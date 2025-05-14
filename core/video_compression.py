#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Compression Module

This module handles the actual video compression:
- Building FFmpeg commands with correct parameters
- Executing compression processes
- Monitoring compression progress
- Error handling and reporting
"""

import os
import subprocess
import logging
import re
import shlex
from typing import Dict, List, Tuple, Optional, Callable

logger = logging.getLogger(__name__)


def get_compression_settings() -> Dict:
    """
    Get the default compression settings based on project requirements.
    
    Returns:
        Dictionary of compression settings
    """
    return {
        "codec": "libx265",
        "profile": "main10",
        "preset": "medium",  # Encoding speed/quality tradeoff
        "crf": 12,           # Constant Rate Factor (quality-based)
        "x265_params": "profile=main10",
        "pixel_format": "yuv420p10le",
        "color_settings": {
            "primaries": "bt709",
            "trc": "bt709",
            "space": "bt709"
        },
        "tag": "hvc1",
        "faststart": True,
        "audio_codec": "aac",  # AAC audio encoding
        "audio_bitrate": "320k"  # 320kbps audio bitrate
    }


def build_ffmpeg_command(input_path: str, output_path: str, settings: Optional[Dict] = None) -> List[str]:
    """
    Build FFmpeg command for video compression.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output compressed file
        settings: Optional custom settings (defaults to get_compression_settings())
        
    Returns:
        List of command arguments for subprocess
    """
    if settings is None:
        settings = get_compression_settings()
    
    logger.info(f"Building FFmpeg command for {input_path}")
    
    # Base command
    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-i", input_path
    ]
    
    # Video settings
    cmd.extend([
        "-c:v", settings["codec"],
        "-profile:v", settings["profile"],
        "-preset", settings["preset"],
        "-crf", str(settings["crf"]),
        "-pix_fmt", settings["pixel_format"]
    ])
    
    # x265-specific parameters
    if "x265_params" in settings:
        cmd.extend(["-x265-params", settings["x265_params"]])
    
    # Color settings
    color = settings["color_settings"]
    cmd.extend([
        "-color_primaries", color["primaries"],
        "-color_trc", color["trc"],
        "-colorspace", color["space"]
    ])
    
    # Tag and faststart
    cmd.extend(["-tag:v", settings["tag"]])
    if settings["faststart"]:
        cmd.extend(["-movflags", "+faststart"])
    
    # Audio settings - use AAC with specified bitrate
    cmd.extend([
        "-c:a", settings["audio_codec"],
        "-b:a", settings["audio_bitrate"]
    ])
    
    # Output path
    cmd.append(output_path)
    
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")
    return cmd


# Global variable to store the current compression process
_current_compression_process = None
_compression_cancelled = False

def compress_video(
    input_path: str,
    output_path: str,
    settings: Optional[Dict] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    temp_dir: str = None,  # Kept for backward compatibility but no longer used
    check_cancelled: Optional[Callable[[], bool]] = None  # Function to check if compression was cancelled
) -> bool:
    """
    Compress a video file using FFmpeg.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output compressed file
        settings: Optional custom settings
        progress_callback: Optional callback function for progress updates
        temp_dir: No longer used - files are written directly to output location
        
    Returns:
        True if compression was successful, False otherwise
    """
    logger.info(f"Starting compression of {input_path}")
    
    # Get video duration for progress calculation
    duration = 0
    try:
        metadata = get_video_duration(input_path)
        if metadata:
            duration = metadata
            logger.info(f"Video duration: {duration} seconds")
    except Exception as e:
        logger.warning(f"Could not get video duration: {str(e)}")
    
    # Ensure output directory exists
    try:
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Ensuring output directory exists: {output_dir}")
    except PermissionError as e:
        logger.error(f"Permission error creating output directory {output_dir}: {str(e)}")
        return False
    except OSError as e:
        logger.error(f"OS error creating output directory {output_dir}: {str(e)}")
        return False
    
    # Build command to write directly to output path
    cmd = build_ffmpeg_command(input_path, output_path, settings)
    
    # Log command for debugging quality issues
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")
    
    try:
        # Reset the cancellation flag
        global _compression_cancelled
        _compression_cancelled = False
        
        # Use Popen to get real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Store reference to the current process
        global _current_compression_process
        _current_compression_process = process
        
        # Process output in real-time
        last_progress = 0
        for line in process.stderr:
            # Check if cancellation was requested
            if check_cancelled and check_cancelled() or _compression_cancelled:
                logger.info("Cancelling compression due to user request")
                process.terminate()
                # Allow some time for process to terminate
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()  # Force kill if it doesn't terminate
                
                # Clean up partial output file
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                        logger.info(f"Removed partial output file due to cancellation: {output_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove partial output file: {str(e)}")
                
                # Reset current process reference
                _current_compression_process = None
                return False
                
            # Parse progress and update callback
            progress = parse_progress(line, duration)
            if progress is not None and progress > last_progress:
                last_progress = progress
                if progress_callback:
                    progress_callback(progress)
                    
                # Log progress at 10% intervals
                if int(progress * 10) > int(last_progress * 10):
                    logger.info(f"Compression progress: {progress:.1%}")
        
        # Wait for process to complete
        return_code = process.wait()
        
        if return_code != 0:
            logger.error(f"FFmpeg process failed with return code {return_code}")
            # Clean up partial output file if it exists
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    logger.info(f"Removed failed output file: {output_path}")
                except Exception as e:
                    logger.error(f"Failed to remove failed output file: {str(e)}")
            return False
        
        # File is already at final destination since we wrote directly to it
        logger.info(f"Successfully compressed to {output_path}")
        
        # Update callback with 100% completion
        if progress_callback:
            progress_callback(1.0)
            
        return True
            
    except subprocess.SubprocessError as e:
        logger.error(f"Subprocess error during compression: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during compression: {str(e)}")
        return False
    finally:
        # Reset current process reference
        _current_compression_process = None


def get_video_duration(input_path: str) -> float:
    """
    Get the duration of a video in seconds.
    
    Args:
        input_path: Path to video file
        
    Returns:
        Duration in seconds
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        duration = float(result.stdout.strip())
        return duration
    except (subprocess.SubprocessError, ValueError) as e:
        logger.error(f"Failed to get video duration: {str(e)}")
        return 0.0


def estimate_file_size(input_path: str, settings: Optional[Dict] = None) -> int:
    """
    Estimate output file size based on input file and compression settings.
    
    Args:
        input_path: Path to input video file
        settings: Optional custom settings
        
    Returns:
        Estimated file size in bytes
    """
    if settings is None:
        settings = get_compression_settings()
    
    # Get video duration
    duration = get_video_duration(input_path)
    if duration <= 0:
        logger.warning("Could not determine video duration for size estimation")
        return 0
    
    # For quality-based encoding, estimate a bitrate based on quality setting
    # Quality 100 typically produces files similar to the original quality
    # This is an estimate since quality-based encoding produces variable bitrates
    video_bitrate = 0
    
    # For CRF-based encoding, estimate bitrate based on CRF value
    # Lower CRF = higher quality = higher bitrate
    crf = settings.get("crf", 23)  # Default CRF in FFmpeg is 23
    
    # CRF scale is logarithmic:
    # - CRF 18 (high quality) ≈ 20-30 Mbps for 1080p content
    # - CRF 23 (default) ≈ 8-12 Mbps for 1080p content
    # - CRF 28 (lower quality) ≈ 3-5 Mbps for 1080p content
    
    # Base estimation on the CRF value (lower = higher bitrate)
    if crf <= 18:  # Very high quality
        video_bitrate = 25000000  # ~25 Mbps
    elif crf <= 21:  # High quality
        video_bitrate = 15000000  # ~15 Mbps
    elif crf <= 25:  # Medium quality
        video_bitrate = 8000000   # ~8 Mbps
    else:  # Lower quality
        video_bitrate = 4000000   # ~4 Mbps
    
    # Get audio bitrate from settings or use default
    audio_bitrate_str = settings.get("audio_bitrate", "320k")
    
    # Parse audio bitrate value
    if audio_bitrate_str.endswith('K') or audio_bitrate_str.endswith('k'):
        audio_bitrate = int(float(audio_bitrate_str[:-1]) * 1000)
    elif audio_bitrate_str.endswith('M') or audio_bitrate_str.endswith('m'):
        audio_bitrate = int(float(audio_bitrate_str[:-1]) * 1000000)
    else:
        try:
            audio_bitrate = int(audio_bitrate_str)
        except ValueError:
            logger.info(f"Using default audio bitrate: 320000")
            audio_bitrate = 320000  # 320 kbps AAC
    
    # Calculate based on bitrate and duration
    total_bitrate = video_bitrate + audio_bitrate
    estimated_bytes = int((total_bitrate / 8) * duration)
    
    # Add 10% overhead for container and other metadata
    estimated_bytes = int(estimated_bytes * 1.1)
    
    logger.info(f"Estimated output size: {estimated_bytes / (1024*1024):.2f} MB")
    
    return estimated_bytes


def parse_progress(line: str, total_duration: float) -> Optional[float]:
    """
    Parse FFmpeg output line to extract progress information.
    
    Args:
        line: Line of FFmpeg output
        total_duration: Total duration of the video in seconds
        
    Returns:
        Progress percentage (0.0-1.0) or None if no progress info
    """
    if total_duration <= 0:
        return None
        
    # Look for time information in the output
    time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
    if time_match:
        # Extract hours, minutes, and seconds
        hours, minutes, seconds = map(float, time_match.groups())
        current_time = hours * 3600 + minutes * 60 + seconds
        
        # Calculate progress as a percentage
        progress = min(current_time / total_duration, 1.0)
        return progress
    
    return None


def calculate_time_remaining(progress: float, start_time: float, current_time: float) -> str:
    """
    Calculate and format the estimated time remaining.
    
    Args:
        progress: Current progress as a percentage (0.0-1.0)
        start_time: Timestamp when the compression started
        current_time: Current timestamp
        
    Returns:
        Formatted string with estimated time remaining
    """
    if progress <= 0:
        return "Calculating..."
    
    elapsed = current_time - start_time
    estimated_total = elapsed / progress
    remaining_seconds = estimated_total - elapsed
    
    # Format as hours, minutes, seconds
    hours, remainder = divmod(remaining_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"


def terminate_current_compression():
    """
    Terminate the current compression process if one is running.
    
    Returns:
        True if a process was terminated, False otherwise
    """
    global _current_compression_process, _compression_cancelled
    
    if _current_compression_process is not None:
        logger.info("Terminating active compression process")
        _compression_cancelled = True
        
        try:
            _current_compression_process.terminate()
            # Allow some time for the process to terminate gracefully
            try:
                _current_compression_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Process did not terminate in time, force killing")
                _current_compression_process.kill()
                
            return True
        except Exception as e:
            logger.error(f"Error terminating compression process: {str(e)}")
            return False
    
    return False


def check_hardware_acceleration():
    """
    Check if libx265 codec is available for video encoding.
    
    Returns:
        True if libx265 is available, False otherwise
    """
    cmd = ["ffmpeg", "-encoders"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Check for libx265 support
        if "libx265" in result.stdout:
            logger.info("libx265 codec is available")
            return True
        else:
            logger.warning("libx265 codec not found")
            return False
            
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to check codec availability: {str(e)}")
        return False