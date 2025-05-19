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
    try:
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
        
        # Check if FFmpeg is available
        ffmpeg_available = True
        try:
            # First check if FFmpeg is available
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=False)
        except FileNotFoundError:
            logger.error("FFmpeg not found. Please install FFmpeg and add it to your PATH.")
            ffmpeg_available = False
            # Return True to allow the file to be added to the queue even without FFmpeg validation
            return True
        
        # Only validate with FFmpeg if it's available
        if ffmpeg_available:
            try:
                # Just run a quick analysis with FFmpeg to check if the file is valid
                cmd = ["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"]
                
                # Use timeout to prevent hanging
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    # If there are errors in the output, the file may be corrupt
                    if result.stderr:
                        logger.warning(f"FFmpeg detected issues with file: {file_path}")
                        logger.debug(f"FFmpeg output: {result.stderr}")
                        return False
                except subprocess.TimeoutExpired:
                    logger.warning(f"FFmpeg validation timed out for file: {file_path}")
                    # Return True to allow the file to be added to the queue even when timeout occurs
                    return True
                    
            except subprocess.SubprocessError as e:
                logger.warning(f"Failed to validate video file with FFmpeg: {str(e)}")
                # Still return True to allow the file to be added to the queue even with FFmpeg validation issues
                return True
        
        return True
    except Exception as e:
        logger.error(f"Unexpected error validating file {file_path}: {str(e)}", exc_info=True)
        # Return True to allow the file to be added to the queue even with validation errors
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
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.warning(f"ffprobe returned error code {result.returncode}")
                return None
        except subprocess.TimeoutExpired:
            logger.warning(f"ffprobe timed out for file: {file_path}")
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
    
    # Use original filename with .mp4 extension for consistency
    new_name = f"{name}.mp4"
    
    # Determine output directory
    if output_dir:
        # Preserve the original folder structure when using a specified output directory
        # Extract the relative path of the input file from its source directory
        input_dir_path = os.path.dirname(input_path)
        
        # Check if the input path contains a CAM folder
        cam_folder = None
        path_parts = input_dir_path.split(os.path.sep)
        for part in path_parts:
            if "CAM" in part.upper():
                cam_folder = part
                break
        
        if cam_folder:
            # If we found a CAM folder, preserve that structure
            cam_output_dir = os.path.join(output_dir, cam_folder)
            os.makedirs(cam_output_dir, exist_ok=True)
            output_path = os.path.join(cam_output_dir, new_name)
            logger.info(f"Preserving CAM folder structure: {cam_folder}")
        else:
            # If no CAM folder, just use the output directory
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, new_name)
    else:
        # Handle the case where input is in "/01 VIDEO.old/" but output should be in "/01 VIDEO/"
        dir_path = os.path.dirname(input_path)
        
        # Check for different OS path separators and the "01 VIDEO.old" pattern
        # This will work with both Unix-style and Windows-style paths
        video_old_pattern = os.path.sep + "01 VIDEO.old" + os.path.sep
        video_old_end_pattern = os.path.sep + "01 VIDEO.old"
        video_pattern = os.path.sep + "01 VIDEO" + os.path.sep
        
        # Handle paths that contain the pattern
        if video_old_pattern in dir_path or dir_path.endswith(video_old_end_pattern):
            # Create the corresponding "/01 VIDEO/" directory
            new_dir_path = dir_path.replace("01 VIDEO.old", "01 VIDEO")
            logger.info(f"Converting path from '{dir_path}' to '{new_dir_path}'")
            os.makedirs(new_dir_path, exist_ok=True)
            output_path = os.path.join(new_dir_path, new_name)
        else:
            output_path = os.path.join(dir_path, new_name)
    
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
    
    try:
        for root, dirs, _ in os.walk(root_dir):
            for dir_name in dirs:
                if "CAM" in dir_name.upper():
                    cam_folder = os.path.join(root, dir_name)
                    cam_folders.append(cam_folder)
                    logger.info(f"Found CAM folder: {cam_folder}")
    except Exception as e:
        logger.error(f"Error searching for CAM folders: {str(e)}")
    
    logger.info(f"Found {len(cam_folders)} CAM folders")
    return cam_folders


def copy_non_cam_folders(old_dir: str, new_dir: str, progress_callback=None) -> int:
    """
    Copy contents of non-CAM subfolders from old directory to new directory.
    
    Args:
        old_dir: Path to the '01 VIDEO.old' directory
        new_dir: Path to the new '01 VIDEO' directory
        progress_callback: Optional callback function for progress updates
        
    Returns:
        Number of folders processed
    """
    logger.info(f"Copying non-CAM folders from {old_dir} to {new_dir}")
    
    # Create the new directory if it doesn't exist
    os.makedirs(new_dir, exist_ok=True)
    
    folders_copied = 0
    
    try:
        # List all subdirectories in old_dir
        subdirs = [d for d in os.listdir(old_dir) if os.path.isdir(os.path.join(old_dir, d))]
        
        # Filter out folders containing 'CAM' in their name
        non_cam_folders = [d for d in subdirs if "CAM" not in d.upper()]
        
        # If there are no folders to process, return early
        if not non_cam_folders:
            logger.info("No non-CAM folders found to copy")
            return 0
            
        # Total steps for progress tracking
        total_folders = len(non_cam_folders)
        
        # Process each non-CAM folder
        for folder_index, folder_name in enumerate(non_cam_folders):
            src_folder = os.path.join(old_dir, folder_name)
            dst_folder = os.path.join(new_dir, folder_name)
            
            # Update progress
            if progress_callback:
                progress_percent = (folder_index / total_folders) * 100
                progress_callback(progress_percent, f"Copying folder: {folder_name}")
            
            logger.info(f"Processing non-CAM folder: {folder_name}")
            
            # Create the destination folder
            os.makedirs(dst_folder, exist_ok=True)
            
            # Copy contents
            import shutil
            
            # Count items for detailed progress
            items = list(os.listdir(src_folder))
            total_items = len(items)
            
            for item_index, item in enumerate(items):
                src_item = os.path.join(src_folder, item)
                dst_item = os.path.join(dst_folder, item)
                
                # Update detailed progress
                if progress_callback and total_items > 0:
                    sub_progress = (item_index / total_items) * 100
                    sub_message = f"Copying {folder_name}/{item}"
                    # Fold this into the overall progress
                    overall_progress = ((folder_index + (item_index / total_items)) / total_folders) * 100
                    progress_callback(overall_progress, sub_message)
                
                if os.path.isdir(src_item):
                    # Recursively copy directory
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                    logger.info(f"Copied directory: {item}")
                else:
                    # Copy file
                    shutil.copy2(src_item, dst_item)
                    logger.info(f"Copied file: {item}")
            
            folders_copied += 1
            logger.info(f"Completed copying folder: {folder_name}")
            
            # Update progress after completing a folder
            if progress_callback:
                progress_percent = ((folder_index + 1) / total_folders) * 100
                progress_callback(progress_percent, f"Completed folder: {folder_name}")
        
        logger.info(f"Copied {folders_copied} non-CAM folders")
        return folders_copied
        
    except Exception as e:
        logger.error(f"Error copying non-CAM folders: {str(e)}", exc_info=True)
        return folders_copied