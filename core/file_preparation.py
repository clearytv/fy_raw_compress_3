#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Preparation Module

This module handles validation and preparation of video files:
- Scanning directories for video files
- Validating file formats
- Extracting video metadata
- Preparing files for compression
"""

import os
import logging
import subprocess
from typing import List, Dict, Tuple, Optional, Union

logger = logging.getLogger(__name__)

# Valid file extensions for input
VALID_EXTENSIONS = ['.mov', '.mp4']


def scan_directory(directory_path: str, recursive: bool = True) -> List[str]:
    """
    Scan a directory for valid video files.
    
    Args:
        directory_path: Path to directory to scan
        recursive: Whether to scan subdirectories recursively
        
    Returns:
        List of valid video file paths
    """
    logger.info(f"Scanning directory: {directory_path} (recursive={recursive})")
    
    valid_files = []
    
    try:
        if recursive:
            for root, _, files in os.walk(directory_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    if validate_video_file(file_path):
                        valid_files.append(file_path)
        else:
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                if os.path.isfile(file_path) and validate_video_file(file_path):
                    valid_files.append(file_path)
    except OSError as e:
        logger.error(f"Error scanning directory {directory_path}: {str(e)}")
    
    logger.info(f"Found {len(valid_files)} valid video files")
    return valid_files


def validate_video_file(file_path: str) -> bool:
    """
    Validate that a file is a compatible video file.
    
    Args:
        file_path: Path to video file to validate
        
    Returns:
        True if file is valid for compression, False otherwise
    """
    logger.info(f"Validating video file: {file_path}")
    
    # Check if file exists
    if not os.path.isfile(file_path):
        logger.warning(f"File does not exist: {file_path}")
        return False
    
    # Check file extension
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in VALID_EXTENSIONS:
        logger.warning(f"Invalid file extension: {ext}")
        return False
    
    # Use FFmpeg to verify file integrity
    try:
        # Just run a quick analysis with FFmpeg to check if the file is valid
        cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # If there are errors in the output, the file may be corrupt
        if result.stderr:
            logger.warning(f"FFmpeg detected issues with file: {file_path}")
            logger.debug(f"FFmpeg output: {result.stderr}")
            return False
    except subprocess.SubprocessError as e:
        logger.warning(f"Failed to validate video file with FFmpeg: {str(e)}")
        return False
    
    return True


def get_video_metadata(file_path: str) -> Optional[Dict]:
    """
    Extract metadata from a video file using FFmpeg.
    
    Args:
        file_path: Path to video file
        
    Returns:
        Dictionary of video metadata or None if extraction fails
    """
    logger.info(f"Extracting metadata from: {file_path}")
    
    metadata = {}
    
    try:
        # Use ffprobe to extract detailed metadata
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"ffprobe returned error code {result.returncode}")
            return None
        
        import json
        data = json.loads(result.stdout)
        
        # Extract basic video information
        if 'format' in data:
            metadata['format'] = data['format']['format_name']
            metadata['duration'] = float(data['format']['duration']) if 'duration' in data['format'] else 0
            metadata['size'] = int(data['format']['size']) if 'size' in data['format'] else 0
        
        # Get video stream information
        video_stream = None
        audio_stream = None
        
        for stream in data.get('streams', []):
            if stream['codec_type'] == 'video' and not video_stream:
                video_stream = stream
            elif stream['codec_type'] == 'audio' and not audio_stream:
                audio_stream = stream
        
        # Parse video stream data
        if video_stream:
            metadata['video_codec'] = video_stream.get('codec_name')
            metadata['width'] = video_stream.get('width')
            metadata['height'] = video_stream.get('height')
            metadata['fps'] = eval(video_stream.get('r_frame_rate', '0/1')) if 'r_frame_rate' in video_stream else 0
            metadata['pix_fmt'] = video_stream.get('pix_fmt')
        
        # Parse audio stream data
        if audio_stream:
            metadata['audio_codec'] = audio_stream.get('codec_name')
            metadata['channels'] = audio_stream.get('channels')
            metadata['sample_rate'] = audio_stream.get('sample_rate')
        
        logger.info(f"Extracted metadata from {file_path}")
        return metadata
        
    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to extract metadata from {file_path}: {str(e)}")
        return None


def generate_output_filename(input_path: str, output_dir: Optional[str] = None) -> str:
    """
    Generate output filename for compressed video.
    
    Args:
        input_path: Path to input video file
        output_dir: Optional output directory (if None, use same directory as input)
        
    Returns:
        Path for output compressed file
    """
    # Extract original filename and extension
    filename = os.path.basename(input_path)
    name, ext = os.path.splitext(filename)
    
    # Add suffix to indicate compression
    new_name = f"{name}_24mbps.mp4"
    
    # Determine output directory
    if output_dir:
        # Create the directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, new_name)
    else:
        output_path = os.path.join(os.path.dirname(input_path), new_name)
    
    logger.info(f"Generated output filename: {output_path}")
    return output_path


def prepare_output_directory(input_dir: str, output_base_dir: str) -> str:
    """
    Create output directory structure mirroring the input directory.
    
    Args:
        input_dir: Path to input directory
        output_base_dir: Path to base output directory
        
    Returns:
        Path to prepared output directory
    """
    logger.info(f"Preparing output directory for {input_dir}")
    
    # Extract the relative path from input directory to create same structure in output
    input_dir = os.path.abspath(input_dir)
    
    # Extract just the final directory name
    dir_name = os.path.basename(input_dir)
    
    # Create the output directory
    output_dir = os.path.join(output_base_dir, dir_name)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Prepared output directory: {output_dir}")
    return output_dir


def rename_video_folder(folder_path: str) -> str:
    """
    Rename the video folder to .old (e.g., '01 VIDEO' to '01 VIDEO.old').
    
    Args:
        folder_path: Path to the folder to rename
        
    Returns:
        Path to the renamed folder or original path if not renamed
    """
    logger.info(f"Attempting to rename folder: {folder_path}")
    
    if not os.path.isdir(folder_path):
        logger.warning(f"Cannot rename non-existent directory: {folder_path}")
        return folder_path
    
    folder_name = os.path.basename(folder_path)
    if folder_name.upper() == "01 VIDEO":
        parent_dir = os.path.dirname(folder_path)
        new_name = folder_name + ".old"
        new_path = os.path.join(parent_dir, new_name)
        
        try:
            # Check if .old folder already exists
            if os.path.exists(new_path):
                logger.warning(f"Cannot rename: {new_path} already exists")
                return folder_path
                
            os.rename(folder_path, new_path)
            logger.info(f"Renamed folder to: {new_path}")
            return new_path
        except OSError as e:
            logger.error(f"Failed to rename folder {folder_path}: {str(e)}")
            return folder_path
    
    return folder_path


def find_cam_folders(root_dir: str) -> List[str]:
    """
    Find all CAM folders within the given directory structure.
    
    Args:
        root_dir: Root directory to search from
        
    Returns:
        List of paths to CAM folders
    """
    logger.info(f"Searching for CAM folders in: {root_dir}")
    
    cam_folders = []
    
    for root, dirs, _ in os.walk(root_dir):
        for dir_name in dirs:
            if "CAM" in dir_name.upper():
                cam_folder = os.path.join(root, dir_name)
                cam_folders.append(cam_folder)
                logger.info(f"Found CAM folder: {cam_folder}")
    
    logger.info(f"Found {len(cam_folders)} CAM folders")
    return cam_folders