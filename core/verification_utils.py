import os
import subprocess
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for comparison
DURATION_TOLERANCE_SECONDS = 1.0 # Allow 1 second difference in duration

def get_media_properties(file_path):
    """
    Extracts video and audio properties from a media file using ffprobe.

    Args:
        file_path (str): The path to the media file.

    Returns:
        dict: A dictionary containing media properties, or None if ffprobe fails
              or the file doesn't exist.
              Properties include:
              - 'format_name'
              - 'duration' (float, in seconds)
              - 'video_streams' (list of dicts, each with 'width', 'height', 'r_frame_rate', 'codec_name')
              - 'audio_streams' (list of dicts, each with 'channels', 'codec_name', 'sample_rate')
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None

    command = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        file_path
    ]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(timeout=60) # Timeout after 60 seconds

        if process.returncode != 0:
            logger.error(f"ffprobe error for {file_path}: {stderr.decode('utf-8', 'ignore')}")
            return None

        properties = json.loads(stdout.decode('utf-8', 'ignore'))
        
        extracted_data = {
            'format_name': properties.get('format', {}).get('format_name'),
            'duration': float(properties.get('format', {}).get('duration', 0.0)),
            'video_streams': [],
            'audio_streams': []
        }

        for stream in properties.get('streams', []):
            if stream.get('codec_type') == 'video':
                # Convert frame rate like "30000/1001" to a float
                r_frame_rate_str = stream.get('r_frame_rate', '0/1')
                try:
                    num, den = map(float, r_frame_rate_str.split('/'))
                    frame_rate = num / den if den != 0 else 0.0
                except ValueError:
                    frame_rate = 0.0
                
                extracted_data['video_streams'].append({
                    'width': stream.get('width'),
                    'height': stream.get('height'),
                    'r_frame_rate_val': frame_rate, # Storing as float
                    'r_frame_rate_str': r_frame_rate_str, # Storing original string for reference
                    'codec_name': stream.get('codec_name'),
                    'duration': float(stream.get('duration', 0.0))
                })
            elif stream.get('codec_type') == 'audio':
                extracted_data['audio_streams'].append({
                    'channels': stream.get('channels'),
                    'codec_name': stream.get('codec_name'),
                    'sample_rate': stream.get('sample_rate'),
                    'duration': float(stream.get('duration', 0.0))
                })
        
        # If video stream duration is 0 but format duration is available, use format duration
        # This can happen with some formats/encodings
        if extracted_data['video_streams'] and extracted_data['video_streams'][0]['duration'] == 0.0 and extracted_data['duration'] > 0:
            extracted_data['video_streams'][0]['duration'] = extracted_data['duration']
        if extracted_data['audio_streams'] and extracted_data['audio_streams'][0]['duration'] == 0.0 and extracted_data['duration'] > 0:
             # Prefer audio stream specific duration if available and non-zero, otherwise use format duration
            for i in range(len(extracted_data['audio_streams'])):
                if extracted_data['audio_streams'][i]['duration'] == 0.0:
                     extracted_data['audio_streams'][i]['duration'] = extracted_data['duration']


        return extracted_data

    except subprocess.TimeoutExpired:
        logger.error(f"ffprobe timed out for {file_path}")
        return None
    except FileNotFoundError:
        logger.error("ffprobe command not found. Please ensure FFmpeg (which includes ffprobe) is installed and in your system's PATH.")
        # Re-raise for higher level handling or specific user feedback
        raise 
    except json.JSONDecodeError:
        logger.error(f"Failed to decode ffprobe JSON output for {file_path}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing {file_path} with ffprobe: {e}")
        return None

def compare_media_properties(original_props, converted_props):
    """
    Compares properties of original and converted media.
    Returns a list of mismatch descriptions.
    """
    mismatches = []

    # Video Duration
    # Use the duration from the first video stream if available, otherwise format duration
    orig_video_duration = original_props['video_streams'][0]['duration'] if original_props.get('video_streams') else original_props.get('duration', 0.0)
    conv_video_duration = converted_props['video_streams'][0]['duration'] if converted_props.get('video_streams') else converted_props.get('duration', 0.0)

    if abs(orig_video_duration - conv_video_duration) > DURATION_TOLERANCE_SECONDS:
        mismatches.append(f"Duration mismatch: original {orig_video_duration:.2f}s, converted {conv_video_duration:.2f}s")

    # Video Resolution (comparing first video stream)
    if original_props.get('video_streams') and converted_props.get('video_streams'):
        orig_video = original_props['video_streams'][0]
        conv_video = converted_props['video_streams'][0]
        if orig_video.get('width') != conv_video.get('width') or \
           orig_video.get('height') != conv_video.get('height'):
            mismatches.append(
                f"Resolution mismatch: original {orig_video.get('width')}x{orig_video.get('height')}, "
                f"converted {conv_video.get('width')}x{conv_video.get('height')}"
            )
        # Optional: Frame Rate (comparing first video stream's r_frame_rate_val)
        # Frame rates can be tricky due to representation (e.g., 29.97 vs 30000/1001)
        # Comparing the float value with a small tolerance might be better
        orig_fr = orig_video.get('r_frame_rate_val', 0.0)
        conv_fr = conv_video.get('r_frame_rate_val', 0.0)
        if abs(orig_fr - conv_fr) > 0.1: # Tolerance for frame rate comparison
             mismatches.append(
                f"Frame rate mismatch: original {orig_fr:.2f} (raw: {orig_video.get('r_frame_rate_str')}), "
                f"converted {conv_fr:.2f} (raw: {conv_video.get('r_frame_rate_str')})"
            )
    elif original_props.get('video_streams') and not converted_props.get('video_streams'):
        mismatches.append("Converted file is missing video stream(s).")
    elif not original_props.get('video_streams') and converted_props.get('video_streams'):
        mismatches.append("Original file was missing video stream(s), but converted has them (unexpected).")


    # Audio Properties (comparing first audio stream if multiple exist, or aggregate)
    # For simplicity, comparing number of streams first.
    if len(original_props.get('audio_streams', [])) != len(converted_props.get('audio_streams', [])):
        mismatches.append(
            f"Audio stream count mismatch: original {len(original_props.get('audio_streams', []))}, "
            f"converted {len(converted_props.get('audio_streams', []))}"
        )
    elif original_props.get('audio_streams') and converted_props.get('audio_streams'):
        # Assuming we compare the first audio stream for simplicity
        # A more robust check might iterate or ensure all streams match some criteria
        orig_audio = original_props['audio_streams'][0]
        conv_audio = converted_props['audio_streams'][0]

        if orig_audio.get('channels') != conv_audio.get('channels'):
            mismatches.append(
                f"Audio channels mismatch: original {orig_audio.get('channels')}, "
                f"converted {conv_audio.get('channels')}"
            )
        
        # Optional: Audio Codec
        # if orig_audio.get('codec_name') != conv_audio.get('codec_name'):
        #     mismatches.append(
        #         f"Audio codec mismatch: original {orig_audio.get('codec_name')}, "
        #         f"converted {conv_audio.get('codec_name')}"
        #     )
            
        # Optional: Audio Sample Rate
        # if orig_audio.get('sample_rate') != conv_audio.get('sample_rate'):
        #     mismatches.append(
        #         f"Audio sample rate mismatch: original {orig_audio.get('sample_rate')}, "
        #         f"converted {conv_audio.get('sample_rate')}"
        #     )

        # Audio Duration (from first audio stream)
        # Should align with video duration, already checked broadly, but can be specific
        orig_audio_duration = orig_audio.get('duration', 0.0)
        conv_audio_duration = conv_audio.get('duration', 0.0)
        if abs(orig_audio_duration - conv_audio_duration) > DURATION_TOLERANCE_SECONDS:
             mismatches.append(f"Audio stream duration mismatch: original {orig_audio_duration:.2f}s, converted {conv_audio_duration:.2f}s")
        
        # Check if audio and video durations match within the original file
        if abs(orig_video_duration - orig_audio_duration) > DURATION_TOLERANCE_SECONDS:
            logger.warning(f"Original file has audio/video duration mismatch: video {orig_video_duration:.2f}s, audio {orig_audio_duration:.2f}s")
            # We don't add this to mismatches since it's an issue with the original file, not the conversion
        
        # Check if audio and video durations match within the converted file
        # Only report this as a mismatch if the original file didn't have the same issue
        if abs(conv_video_duration - conv_audio_duration) > DURATION_TOLERANCE_SECONDS:
            # Only flag as an issue if the original didn't have this problem
            if abs(orig_video_duration - orig_audio_duration) <= DURATION_TOLERANCE_SECONDS:
                mismatches.append(f"Converted file has audio/video duration mismatch (original didn't): video {conv_video_duration:.2f}s, audio {conv_audio_duration:.2f}s")
            else:
                # Both files have audio/video mismatch, check if the mismatch is similar
                orig_mismatch = abs(orig_video_duration - orig_audio_duration)
                conv_mismatch = abs(conv_video_duration - conv_audio_duration)
                if abs(orig_mismatch - conv_mismatch) > DURATION_TOLERANCE_SECONDS:
                    mismatches.append(f"Audio/video duration mismatch differs between files: original mismatch {orig_mismatch:.2f}s, converted mismatch {conv_mismatch:.2f}s")

    elif original_props.get('audio_streams') and not converted_props.get('audio_streams'):
        mismatches.append("Converted file is missing audio stream(s).")
    elif not original_props.get('audio_streams') and converted_props.get('audio_streams'):
         mismatches.append("Original file was missing audio stream(s), but converted has them (unexpected).")

    return mismatches


def find_media_files(folder_path, extensions=None):
    """
    Recursively find all media files in a folder and its subfolders.
    
    Args:
        folder_path (str): Path to the folder to search
        extensions (list, optional): List of file extensions to include (e.g., ['.mp4', '.mov'])
                                    If None, include all files
    
    Returns:
        dict: Dictionary with lowercase basename (without extension) as key and full path as value
    """
    if extensions is None:
        # Common video file extensions
        extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv', '.ts', '.m4v']
    
    result = {}
    
    if not os.path.isdir(folder_path):
        return result
        
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            # Skip hidden files and system files
            if file.startswith('.') or file == 'Thumbs.db':
                continue
                
            # Check if file has a media extension
            _, ext = os.path.splitext(file)
            if extensions and ext.lower() not in extensions:
                continue
                
            # Use the filename without extension as the key
            base = os.path.splitext(file)[0].lower()
            full_path = os.path.join(root, file)
            
            # Store in the result dictionary
            result[base] = full_path
            
    return result

def verify_media_conversions(original_folder_path, converted_folder_path):
    """
    Verifies media conversions by comparing properties of files in two folders.

    Args:
        original_folder_path (str): Path to the folder with original media files.
        converted_folder_path (str): Path to the folder with converted media files.

    Returns:
        list: A list of dictionaries, each representing a file pair and its
              verification status.
              Each dictionary contains:
              - 'original_file' (str or None)
              - 'converted_file' (str or None)
              - 'original_properties' (dict or None)
              - 'converted_properties' (dict or None)
              - 'status' (str: "MATCH", "MISMATCH", "ORIGINAL_MISSING",
                          "CONVERTED_MISSING", "ORIGINAL_ERROR", "CONVERTED_ERROR", "FFPROBE_NOT_FOUND")
              - 'mismatches' (list of str)
    """
    report = []
    
    try:
        # Test ffprobe availability once
        get_media_properties(None) # This will fail if ffprobe not found, but we pass None to avoid file error
    except FileNotFoundError:
         # If ffprobe is not found, all files will fail. Return a single error entry.
        logger.error("Critical: ffprobe command not found. Verification cannot proceed.")
        report.append({
            'original_file': original_folder_path, # Indicate folder level issue
            'converted_file': converted_folder_path,
            'original_properties': None,
            'converted_properties': None,
            'status': "FFPROBE_NOT_FOUND",
            'mismatches': ["ffprobe command not found. Please ensure FFmpeg is installed and in your system's PATH."]
        })
        return report
    except TypeError: # Caused by passing None to os.path.exists
        pass # This is expected if ffprobe is found, we just wanted to trigger the FileNotFoundError

    if not os.path.isdir(original_folder_path):
        logger.error(f"Original folder not found: {original_folder_path}")
        # Or handle as appropriate, e.g., return an error status for the whole batch
        report.append({
            'original_file': original_folder_path,
            'converted_file': converted_folder_path,
            'original_properties': None,
            'converted_properties': None,
            'status': "ERROR_ORIGINAL_FOLDER_NOT_FOUND",
            'mismatches': [f"Original folder does not exist: {original_folder_path}"]
        })
        return report # Cannot proceed if original folder is missing

    if not os.path.isdir(converted_folder_path):
        logger.warning(f"Converted folder not found: {converted_folder_path}. All files will be marked as CONVERTED_MISSING.")
        # We can still proceed to list originals and mark them as missing converted counterparts

    # Recursively find all media files in both folders
    try:
        logger.info(f"Recursively searching for media files in: {original_folder_path}")
        original_files = find_media_files(original_folder_path)
        logger.info(f"Found {len(original_files)} media files in original folder")
    except OSError as e:
        logger.error(f"Error listing files in original folder {original_folder_path}: {e}")
        report.append({
            'original_file': original_folder_path,
            'converted_file': converted_folder_path,
            'original_properties': None,
            'converted_properties': None,
            'status': "ERROR_LISTING_ORIGINAL_FILES",
            'mismatches': [f"Could not read original folder contents: {e}"]
        })
        return report

    converted_files = {}
    if os.path.isdir(converted_folder_path):
        try:
            logger.info(f"Recursively searching for media files in: {converted_folder_path}")
            converted_files = find_media_files(converted_folder_path)
            logger.info(f"Found {len(converted_files)} media files in converted folder")
        except OSError as e:
            logger.error(f"Error listing files in converted folder {converted_folder_path}: {e}")
            # Continue, but converted files might be missing from comparison

    processed_converted_stems = set()

    # Iterate through original files to find matches and missing converted files
    for orig_base_lower, orig_path in original_files.items():
        report_item = {
            'original_file': orig_path,
            'converted_file': None,
            'original_properties': None,
            'converted_properties': None,
            'status': "",
            'mismatches': []
        }

        # Skip directories - only process actual files
        if os.path.isdir(orig_path):
            logger.info(f"Skipping directory: {orig_path}")
            continue
            
        # Get media properties
        orig_props = get_media_properties(orig_path)
        if orig_props is None:
            report_item['status'] = "ORIGINAL_ERROR"
            report_item['mismatches'].append(f"Failed to get properties for original: {orig_path}")
            report.append(report_item)
            continue
        report_item['original_properties'] = orig_props

        conv_path = converted_files.get(orig_base_lower)
        if conv_path:
            report_item['converted_file'] = conv_path
            processed_converted_stems.add(orig_base_lower)
            
            # Skip directories - only process actual files
            if os.path.isdir(conv_path):
                logger.info(f"Skipping directory: {conv_path}")
                report_item['status'] = "CONVERTED_ERROR"
                report_item['mismatches'].append(f"Converted path is a directory, not a file: {conv_path}")
                report.append(report_item)
                continue
                
            conv_props = get_media_properties(conv_path)
            if conv_props is None:
                report_item['status'] = "CONVERTED_ERROR"
                report_item['mismatches'].append(f"Failed to get properties for converted: {conv_path}")
            else:
                report_item['converted_properties'] = conv_props
                mismatches = compare_media_properties(orig_props, conv_props)
                if mismatches:
                    report_item['status'] = "MISMATCH"
                    report_item['mismatches'] = mismatches
                else:
                    report_item['status'] = "MATCH"
        else:
            report_item['status'] = "CONVERTED_MISSING"
            report_item['mismatches'].append(f"Converted file for {orig_path} not found based on name '{orig_base_lower}'.")
        
        report.append(report_item)

    # Check for converted files that don't have an original counterpart (orphans)
    for conv_base_lower, conv_path in converted_files.items():
        if conv_base_lower not in processed_converted_stems:
            # Skip directories - only process actual files
            if os.path.isdir(conv_path):
                logger.info(f"Skipping directory: {conv_path}")
                continue
                
            conv_props = get_media_properties(conv_path) # Get props for context, even if no original
            report.append({
                'original_file': None,
                'converted_file': conv_path,
                'original_properties': None,
                'converted_properties': conv_props,
                'status': "ORIGINAL_MISSING", # From perspective of converted file
                'mismatches': [f"Original file for {conv_path} not found based on name '{conv_base_lower}'."]
            })
            
    return report


if __name__ == '__main__':
    # Example Usage (for testing purposes)
    # Create dummy folders and files for testing
    print("Running example verification (requires FFmpeg/ffprobe in PATH)...")
    
    # Create test directories
    test_orig_dir = "test_originals"
    test_conv_dir = "test_converted"
    os.makedirs(test_orig_dir, exist_ok=True)
    os.makedirs(test_conv_dir, exist_ok=True)

    # To run this example, you'd need actual (small) video files.
    # Or, create dummy files and expect errors if ffprobe can't process them.
    # For now, let's assume ffprobe will error out on non-media files,
    # or you can place small, valid media files here for a real test.

    # Create dummy files to simulate structure
    # Note: ffprobe will fail on these empty files, demonstrating error handling.
    # For a real test, replace with small video files.
    dummy_files_info = [
        ("video1.mov", "video1.mp4", True), # Match (if content was real and similar)
        ("video2.avi", "video2.mkv", False), # Mismatch (if content was real and different)
        ("video3.ts", None, False),          # Original only
        (None, "video4.webm", False)         # Converted only
    ]

    print(f"Please place actual (small) video files in '{test_orig_dir}' and '{test_conv_dir}' for a full test.")
    print("Creating dummy files for structure testing (ffprobe will likely error on these):")

    for orig_name, conv_name, _ in dummy_files_info:
        if orig_name:
            with open(os.path.join(test_orig_dir, orig_name), 'w') as f:
                f.write("dummy original content")
            print(f"Created dummy: {os.path.join(test_orig_dir, orig_name)}")
        if conv_name:
            with open(os.path.join(test_conv_dir, conv_name), 'w') as f:
                f.write("dummy converted content")
            print(f"Created dummy: {os.path.join(test_conv_dir, conv_name)}")


    # Example:
    # Create a real small video file (e.g., using ffmpeg CLI) if you want to test MATCH/MISMATCH properly
    # ffmpeg -f lavfi -i testsrc=duration=1:size=128x72:rate=10 -c:v libx264 -t 1 test_originals/sample_good.mp4
    # ffmpeg -f lavfi -i testsrc=duration=1:size=128x72:rate=10 -c:v libx264 -t 1 test_converted/sample_good.mp4
    # ffmpeg -f lavfi -i testsrc=duration=2:size=64x36:rate=15 -c:v libx264 -t 2 test_converted/sample_bad.mp4 
    # (and corresponding original for sample_bad)

    try:
        results = verify_media_conversions(test_orig_dir, test_conv_dir)
        if not results:
            print("Verification returned no results. Check logs or paths.")
        for item in results:
            print(f"\nOriginal: {item.get('original_file')}")
            print(f"Converted: {item.get('converted_file')}")
            print(f"Status: {item.get('status')}")
            if item.get('mismatches'):
                print("Mismatches:")
                for mismatch in item.get('mismatches'):
                    print(f"  - {mismatch}")
            # print(f"Original Props: {item.get('original_properties')}") # Verbose
            # print(f"Converted Props: {item.get('converted_properties')}") # Verbose

    except FileNotFoundError:
        print("\nFFPROBE NOT FOUND. Please install FFmpeg and ensure ffprobe is in your system PATH.")
    except Exception as e:
        print(f"\nAn error occurred during example execution: {e}")
    
    # Clean up dummy files and directories (optional)
    # print("\nCleaning up test directories...")
    # import shutil
    # shutil.rmtree(test_orig_dir, ignore_errors=True)
    # shutil.rmtree(test_conv_dir, ignore_errors=True)
    # print("Cleanup complete.")