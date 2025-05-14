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
import tempfile
from typing import Dict, List, Tuple, Optional, Callable

logger = logging.getLogger(__name__)


def get_compression_settings() -> Dict:
    """
    Get the default compression settings based on project requirements.
    
    Returns:
        Dictionary of compression settings
    """
    return {
        "codec": "hevc_videotoolbox",
        "profile": "main10",
        "bitrate": "24M",
        "pixel_format": "yuv420p10le",
        "color_settings": {
            "primaries": "bt709",
            "trc": "bt709",
            "space": "bt709"
        },
        "tag": "hvc1",
        "faststart": True,
        "audio_codec": "copy"  # Audio pass-through as per specification
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
        "-b:v", settings["bitrate"],
        "-maxrate", settings["bitrate"],
        "-bufsize", f"{int(settings['bitrate'][:-1])*2}M",
        "-pix_fmt", settings["pixel_format"]
    ])
    
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
    
    # Audio settings - use copy for passthrough
    cmd.extend([
        "-c:a", settings["audio_codec"]
    ])
    
    # Output path
    cmd.append(output_path)
    
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")
    return cmd


def compress_video(
    input_path: str,
    output_path: str,
    settings: Optional[Dict] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    temp_dir: str = None
) -> bool:
    """
    Compress a video file using FFmpeg.
    
    Args:
        input_path: Path to input video file
        output_path: Path for output compressed file
        settings: Optional custom settings
        progress_callback: Optional callback function for progress updates
        temp_dir: Directory to use for temporary files
        
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
    
    # Use the external Media HD drive for temporary storage
    if temp_dir is None:
        # Default to Media HD drive temp directory
        media_hd_temp = "/Volumes/Media HD/temp"
        try:
            # Ensure the Media HD drive is mounted and accessible
            if os.path.exists("/Volumes/Media HD"):
                # Create the temp directory if it doesn't exist
                temp_dir = media_hd_temp
                if not os.path.exists(temp_dir):
                    logger.info(f"Creating Media HD temp directory: {temp_dir}")
                    os.makedirs(temp_dir, exist_ok=True)
                logger.info(f"Using Media HD temp directory: {temp_dir}")
            else:
                # Fallback if drive is not mounted
                logger.warning("Media HD drive not found. Using system temp directory instead.")
                temp_dir = tempfile.gettempdir()
                logger.info(f"Using system temp directory: {temp_dir}")
        except Exception as e:
            # Final fallback: Use a local 'temp' directory within the project
            logger.error(f"Error accessing Media HD temp directory: {str(e)}")
            temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'temp')
            logger.info(f"Using local temp directory: {temp_dir}")
    
    # Ensure temp directory exists
    try:
        os.makedirs(temp_dir, exist_ok=True)
        logger.debug(f"Ensuring temp directory exists: {temp_dir}")
    except PermissionError as e:
        logger.error(f"Permission error creating temp directory {temp_dir}: {str(e)}")
        return False
    except OSError as e:
        logger.error(f"OS error creating temp directory {temp_dir}: {str(e)}")
        return False
    
    # Create temporary output path
    temp_output = os.path.join(temp_dir, os.path.basename(output_path))
    
    # Build command using temporary output
    cmd = build_ffmpeg_command(input_path, temp_output, settings)
    
    # Log command for debugging quality issues
    logger.debug(f"FFmpeg command: {' '.join(cmd)}")
    
    try:
        # Use Popen to get real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        # Process output in real-time
        last_progress = 0
        for line in process.stderr:
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
            # Clean up temp file if exists
            if os.path.exists(temp_output):
                os.remove(temp_output)
            return False
        
        # Move from temp location to final destination
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Move file
            import shutil
            shutil.move(temp_output, output_path)
            logger.info(f"Successfully compressed and moved to {output_path}")
            
            # Update callback with 100% completion
            if progress_callback:
                progress_callback(1.0)
                
            return True
        except Exception as e:
            logger.error(f"Failed to move from temp to final location: {str(e)}")
            return False
            
    except subprocess.SubprocessError as e:
        logger.error(f"Subprocess error during compression: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during compression: {str(e)}")
        return False


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
    
    # Extract bitrate from settings
    video_bitrate_str = settings["bitrate"]
    video_bitrate = 0
    
    # Parse bitrate value (e.g., "24M" to 24000000)
    if video_bitrate_str.endswith('K') or video_bitrate_str.endswith('k'):
        video_bitrate = int(float(video_bitrate_str[:-1]) * 1000)
    elif video_bitrate_str.endswith('M') or video_bitrate_str.endswith('m'):
        video_bitrate = int(float(video_bitrate_str[:-1]) * 1000000)
    else:
        try:
            video_bitrate = int(video_bitrate_str)
        except ValueError:
            logger.error(f"Could not parse bitrate: {video_bitrate_str}")
            return 0
    
    # Assume audio bitrate (typically much smaller than video)
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


def check_hardware_acceleration():
    """
    Check if hardware acceleration is available for video encoding.
    
    Returns:
        True if hardware acceleration is available, False otherwise
    """
    cmd = ["ffmpeg", "-encoders"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Check for videotoolbox support
        if "hevc_videotoolbox" in result.stdout:
            logger.info("Hardware acceleration (VideoToolbox) is available")
            return True
        else:
            logger.warning("Hardware acceleration (VideoToolbox) not found")
            return False
            
    except subprocess.SubprocessError as e:
        logger.error(f"Failed to check hardware acceleration: {str(e)}")
        return False