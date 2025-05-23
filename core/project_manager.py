#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Manager Module

This module manages the lifecycle of individual projects:
- Interfaces between the ProjectQueueManager and the existing workflow
- Handles all stages of project processing
- Signals when a project is complete to trigger the next one
"""

import os
import logging
import time
import shutil
from typing import List, Dict, Tuple, Optional, Callable, Any
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Import other core modules
from core.queue_manager import QueueManager, QueueStatus
from core.project_queue_manager import ProjectQueueManager, ProjectStatus
from core.file_preparation import generate_output_filename


class ProjectManager:
    """
    Manages the lifecycle of individual projects in the sequential workflow.
    
    This class serves as an interface between the ProjectQueueManager (which handles
    the sequence of projects) and the existing QueueManager (which handles the files
    within a single project).
    """
    
    def __init__(self, project_queue_manager: Optional[ProjectQueueManager] = None):
        """
        Initialize the project manager.
        
        Args:
            project_queue_manager: Optional ProjectQueueManager instance
                If not provided, a new one will be created
        """
        # Create or store the project queue manager
        self.project_queue_manager = project_queue_manager or ProjectQueueManager()
        
        # Initialize the file queue manager for the current project
        self.file_queue_manager = QueueManager()
        
        # Currently processing project
        self.current_project = None
        
        # Whether a project is currently being processed
        self.is_processing = False
        
        # Completion callbacks
        self._on_project_complete_callback = None
        self._on_queue_complete_callback = None
        
        # Progress callback
        self._progress_callback = None
        
        logger.info("Project manager initialized")
    
    def register_on_project_complete_callback(
        self, callback: Callable[[str, Dict[str, Any], bool], None]
    ) -> None:
        """
        Register a callback function to be called when a project is completed.
        
        Args:
            callback: Function to call when a project is completed.
                It receives (project_id, project_dict, success)
        """
        self._on_project_complete_callback = callback
        logger.info("Project completion callback registered")
    
    def register_on_queue_complete_callback(
        self, callback: Callable[[bool], None]
    ) -> None:
        """
        Register a callback function to be called when the entire queue is completed.
        
        Args:
            callback: Function to call when queue processing is completed.
                It receives a single boolean parameter indicating if all projects were successful.
        """
        self._on_queue_complete_callback = callback
        logger.info("Queue completion callback registered")
    
    def register_progress_callback(
        self, callback: Callable[[str, Dict[str, Any], float, float], None]
    ) -> None:
        """
        Register a callback function to be called with progress updates.
        
        Args:
            callback: Function to call with progress updates.
                It receives (project_id, project_dict, project_progress, overall_queue_progress)
        """
        self._progress_callback = callback
        logger.info("Progress callback registered")
    
    def create_project(
        self,
        name: str,
        input_files: List[str],
        output_dir: str,
        settings: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new project and add it to the queue.
        
        Args:
            name: Name of the project
            input_files: List of input file paths
            output_dir: Directory to store output files
            settings: Compression settings
            metadata: Additional project metadata
            
        Returns:
            Project ID
        """
        # Create default settings if none provided
        if settings is None:
            settings = {}
        
        # Create default metadata if none provided
        if metadata is None:
            metadata = {}
        
        # Create project dictionary
        project = {
            "name": name,
            "input_files": input_files,
            "output_dir": output_dir,
            "settings": settings,
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to queue
        project_id = self.project_queue_manager.add_project(project)
        
        logger.info(f"Created project '{name}' with ID {project_id} ({len(input_files)} files)")
        
        return project_id
    
    def start_processing(
        self,
        progress_callback: Optional[Callable[[str, Dict[str, Any], float, float], None]] = None
    ) -> bool:
        """
        Start processing projects in the queue sequentially.
        
        Args:
            progress_callback: Optional function to receive progress updates
                It receives (project_id, project_dict, project_progress, overall_progress)
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_processing:
            logger.warning("Already processing projects")
            return False
        
        # Store the progress callback
        if progress_callback:
            self._progress_callback = progress_callback
        
        # Start processing the queue
        success = self.project_queue_manager.start_processing(
            process_project_func=self._process_project,
            progress_callback=self._handle_queue_progress,
            completion_callback=self._handle_queue_complete
        )
        
        if success:
            self.is_processing = True
            logger.info("Started processing project queue")
        else:
            logger.warning("Failed to start processing project queue")
        
        return success
    
    def cancel_processing(self) -> bool:
        """
        Cancel all ongoing processing.
        
        Returns:
            True if cancellation was initiated, False otherwise
        """
        if not self.is_processing:
            logger.warning("Cannot cancel: not processing")
            return False
        
        # First cancel the current file queue if it's processing
        if self.file_queue_manager.is_processing:
            self.file_queue_manager.cancel_processing()
        
        # Then cancel the project queue
        self.project_queue_manager.cancel_processing()
        
        self.is_processing = False
        logger.info("Canceled all processing")
        
        return True
    
    def _handle_queue_complete(self, all_successful: bool) -> None:
        """
        Handle completion of the entire project queue.
        
        Args:
            all_successful: Whether all projects completed successfully
        """
        logger.info(f"Project queue processing completed {'successfully' if all_successful else 'with some failures'}")
        
        # Update processing state
        self.is_processing = False
        
        # Call the callback if registered
        if self._on_queue_complete_callback:
            self._on_queue_complete_callback(all_successful)
    
    def _process_project(self, project: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Process a single project.
        
        This is the worker function passed to the project queue manager.
        
        Args:
            project: Project dictionary
            
        Returns:
            Tuple of (success, results)
        """
        try:
            project_id = project.get("id")
            name = project.get("name", "Unnamed Project")
            input_files = project.get("input_files", [])
            output_dir = project.get("output_dir", "")
            settings = project.get("settings", {})
            
            logger.info(f"Processing project '{name}' (ID: {project_id}) with {len(input_files)} files")
            logger.info(f"Queue processing: Starting workflow for project '{name}' with folder renaming")
            
            # Store current project
            self.current_project = project
            
            # Get the parent folder path from the first input file's directory
            # This is needed for the folder renaming process
            parent_folder_path = None
            if input_files:
                # Try to determine the project root directory from the input files
                # We're looking for the parent folder that contains '03 MEDIA/01 VIDEO'
                logger.info(f"Queue processing: Analyzing {len(input_files)} input files to find parent folder path")
                
                for file_path in input_files:
                    logger.info(f"Queue processing: Examining file path: {file_path}")
                    path_parts = os.path.normpath(file_path).split(os.path.sep)
                    
                    # Look for '03 MEDIA' in the path
                    for i, part in enumerate(path_parts):
                        if part == "03 MEDIA" and i > 0:
                            # The parent folder is one level above '03 MEDIA'
                            parent_folder_path = os.path.sep.join(path_parts[:i])
                            logger.info(f"Queue processing: Found parent folder path: {parent_folder_path}")
                            break
                    
                    if parent_folder_path:
                        break
                
                if not parent_folder_path:
                    logger.warning(f"Queue processing: Could not find parent folder path with '03 MEDIA' in any input file")
            
            # Perform folder renaming if we found a valid parent folder
            renamed = False
            renamed_path = ""
            updated_files = input_files.copy()
            
            if parent_folder_path:
                # Import the folder renaming functions
                from core.file_preparation import rename_video_folder, copy_non_cam_folders
                
                logger.info(f"Queue processing: Starting folder rename workflow for project '{name}' (ID: {project_id})")
                
                # Construct the video path
                media_dir = os.path.join(parent_folder_path, "03 MEDIA")
                video_path = os.path.join(media_dir, "01 VIDEO")
                
                logger.info(f"Queue processing: Checking for video folder to rename: {video_path}")
                
                # Check if the video path exists and rename it to .old
                if not os.path.exists(video_path):
                    logger.warning(f"Queue processing: Video folder does not exist: {video_path}")
                else:
                    # Rename video folder
                    logger.info(f"Queue processing: Calling rename_video_folder on: {video_path}")
                    renamed_path = rename_video_folder(video_path)
                    logger.info(f"Queue processing: Rename operation completed - from: {video_path} to: {renamed_path}")
                    
                    # Check if the renaming was successful
                    if renamed_path == video_path:
                        logger.warning(f"Queue processing: Folder renaming failed or unnecessary for: {video_path}")
                    else:  # If the folder was renamed successfully
                        logger.info(f"Queue processing: Successfully renamed folder to: {renamed_path}")
                        renamed = True
                        
                        # Create a new empty "01 VIDEO" folder
                        os.makedirs(video_path, exist_ok=True)
                        logger.info(f"Queue processing: Created new '01 VIDEO' directory at: {video_path}")
                        
                        # Copy non-CAM folders from "01 VIDEO.old" to the new "01 VIDEO"
                        logger.info("Queue processing: Starting to copy non-CAM folders...")
                        copied = copy_non_cam_folders(renamed_path, video_path)
                        logger.info(f"Queue processing: Copied {copied} non-CAM folders from {renamed_path} to {video_path}")
                        
                        # Update file paths to point to renamed folder for CAM files
                        if renamed:
                            logger.info(f"Queue processing: Updating file paths in queue after folder rename for {len(input_files)} files")
                            
                            video_path_normalized = os.path.normpath(video_path)
                            renamed_path_normalized = os.path.normpath(renamed_path)
                            
                            logger.info(f"Queue processing: Looking for paths containing '{video_path_normalized}' to replace with '{renamed_path_normalized}'")
                            
                            cam_files_count = 0
                            updated_count = 0
                            
                            for i, file_path in enumerate(input_files):
                                # Create a normalized path string
                                normalized_path = os.path.normpath(file_path)
                                
                                # Check if this file is in a CAM folder
                                path_parts = normalized_path.split(os.path.sep)
                                is_cam_folder = any("CAM" in part.upper() for part in path_parts)
                                
                                # If it's a CAM file, update the path to point to the renamed folder
                                if is_cam_folder:
                                    cam_files_count += 1
                                    logger.info(f"Queue processing: File {i+1}/{len(input_files)} is in a CAM folder: {file_path}")
                                    
                                    # Replace the original video path with the renamed path
                                    updated_path = normalized_path.replace(video_path_normalized, renamed_path_normalized)
                                    logger.info(f"Queue processing: Path replacement attempt: {normalized_path} -> {updated_path}")
                                    
                                    if os.path.exists(updated_path):
                                        logger.info(f"Queue processing: Updated path exists: {updated_path}")
                                        updated_files[i] = updated_path
                                        updated_count += 1
                                    else:
                                        logger.warning(f"Queue processing: Updated path does not exist: {updated_path}")
                                        # Try to fix the path if it's not found
                                        found = False
                                        for part in path_parts:
                                            if "CAM" in part.upper():
                                                # Try to find the file in the renamed folder structure
                                                cam_path = os.path.join(renamed_path_normalized, part)
                                                logger.info(f"Queue processing: Looking for file in alternate CAM path: {cam_path}")
                                                
                                                # Find all files with the same name in the expected location
                                                file_name = os.path.basename(file_path)
                                                possible_file = os.path.join(cam_path, file_name)
                                                
                                                if os.path.exists(possible_file):
                                                    updated_path = possible_file
                                                    updated_files[i] = updated_path
                                                    found = True
                                                    updated_count += 1
                                                    logger.info(f"Queue processing: Found file at alternative path: {updated_path}")
                                                    break
                                                else:
                                                    logger.info(f"Queue processing: File not found at alternative path: {possible_file}")
                                        
                                        if not found:
                                            logger.warning(f"Queue processing: Updated path not found after all attempts: {updated_path}")
                                else:
                                    logger.info(f"Queue processing: File {i+1}/{len(input_files)} is not in a CAM folder, path unchanged: {file_path}")
                            
                            # Log the path changes summary
                            logger.info(f"Queue processing: Found {cam_files_count} CAM files, successfully updated {updated_count} paths")
            
            # Reset the file queue manager
            self.file_queue_manager.clear_queue()
            
            # Add files to the file queue (using updated paths if renamed)
            files_added = self.file_queue_manager.add_files(updated_files)
            
            if files_added == 0:
                logger.warning(f"No valid files to process in project {project_id}")
                return False, {"error": "No valid files to process"}
            
            logger.info(f"Added {files_added} files to file queue for project {project_id}")
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Define progress callback for file queue
            def file_progress_callback(
                file_path: str, 
                file_progress: float, 
                queue_progress: float
            ) -> None:
                if self._progress_callback:
                    # Convert file queue progress to project progress
                    self._progress_callback(
                        project_id, 
                        project, 
                        queue_progress,  # Use queue progress as project progress
                        0.0  # Overall progress will be handled by project queue manager
                    )
            
            # Process the file queue
            start_time = time.time()
            success = self.file_queue_manager.process_queue(
                output_dir=output_dir,
                settings=settings,
                progress_callback=file_progress_callback
            )
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            # Get file queue results
            file_results = self.file_queue_manager.get_results()
            
            # Calculate project statistics
            stats = self._calculate_project_statistics(file_results)
            stats["processing_time"] = processing_time
            
            # Log results
            logger.info(f"Project '{name}' (ID: {project_id}) processing completed "
                       f"{'successfully' if success else 'with errors'} "
                       f"in {processing_time:.2f} seconds")
            
            if success:
                logger.info(f"Processed {stats['files_processed']} files, "
                           f"reduced size by {stats['total_size_reduction_human']}, "
                           f"average reduction: {stats['average_reduction_percent']:.1f}%")
                
                # Add verification and deletion step here if processing was successful
                # Update project status to VERIFYING in the project queue manager
                from core.project_queue_manager import ProjectStatus
                if project_id in self.project_queue_manager.status:
                    self.project_queue_manager.status[project_id] = ProjectStatus.VERIFYING
                    logger.info(f"Project '{name}' (ID: {project_id}) status updated to VERIFYING")
                
                # Get the folders to verify (original and converted)
                if parent_folder_path and renamed_path:
                    # Only proceed with verification if folders are available
                    media_dir = os.path.join(parent_folder_path, "03 MEDIA")
                    original_media_folder_path = renamed_path  # 01 VIDEO.old
                    converted_media_folder_path = os.path.join(media_dir, "01 VIDEO")  # 01 VIDEO
                    
                    logger.info(f"Starting verification between original folder '{original_media_folder_path}' and converted folder '{converted_media_folder_path}'")
                    
                    # Import verification utility
                    from core.verification_utils import verify_media_conversions
                    
                    try:
                        # Perform verification
                        verification_results = verify_media_conversions(
                            original_media_folder_path,
                            converted_media_folder_path
                        )
                        
                        # Add verification status to results
                        stats["verification_performed"] = True
                        stats["verification_results"] = verification_results
                        
                        # Check if all files matched
                        all_files_matched = verification_results and all(
                            item.get('status') == "MATCH" for item in verification_results
                        )
                        
                        stats["verification_all_matched"] = all_files_matched
                        
                        if all_files_matched:
                            logger.info(f"All files verified successfully for project '{name}' (ID: {project_id}). Proceeding with deletion of original folder.")
                            
                            # Attempt to delete the original folder
                            try:
                                import shutil
                                shutil.rmtree(original_media_folder_path)
                                logger.info(f"Successfully deleted original folder: {original_media_folder_path}")
                                stats["original_folder_deleted"] = True
                                
                                # Update main project folder icon from Orange to Green
                                if parent_folder_path:
                                    from core.macos_utils import set_finder_label
                                    # Remove Orange label and set Green
                                    set_finder_label(parent_folder_path, "None")  # Clear existing labels
                                    success_icon = set_finder_label(parent_folder_path, "Green")
                                    logger.info(f"Project folder icon updated to Green: {success_icon}")
                                    stats["folder_icon_updated"] = success_icon
                            except Exception as e:
                                logger.error(f"Failed to delete original folder {original_media_folder_path}: {e}", exc_info=True)
                                stats["original_folder_deleted"] = False
                                stats["deletion_error"] = str(e)
                        else:
                            logger.warning(f"Verification failed - not all files matched for project '{name}' (ID: {project_id}). Original folder not deleted.")
                            stats["original_folder_deleted"] = False
                            stats["deletion_skipped_reason"] = "verification_mismatch"
                    except Exception as e:
                        logger.error(f"Verification error for project '{name}' (ID: {project_id}): {e}", exc_info=True)
                        stats["verification_error"] = str(e)
                else:
                    logger.warning(f"Cannot perform verification for project '{name}' (ID: {project_id}): Missing folder information")
                    stats["verification_performed"] = False
                    stats["verification_skipped_reason"] = "missing_folder_information"
            
            # Signal completion if callback is registered
            if self._on_project_complete_callback:
                self._on_project_complete_callback(project_id, project, success)
            
            return success, stats
            
        except Exception as e:
            logger.error(f"Error processing project: {str(e)}", exc_info=True)
            return False, {"error": str(e)}
        finally:
            # Clear current project
            self.current_project = None
    
    def _handle_queue_progress(
        self, 
        project_id: str, 
        project: Dict[str, Any], 
        overall_progress: float
    ) -> None:
        """
        Handle progress updates from the project queue manager.
        
        Args:
            project_id: ID of the current project
            project: Project dictionary
            overall_progress: Overall progress of the queue
        """
        if self._progress_callback:
            # Get the current file queue progress if available
            if self.file_queue_manager.is_processing:
                # Get the current index and total files
                current_index = self.file_queue_manager.current_index
                total_files = len(self.file_queue_manager.queue)
                
                # Calculate project progress (percentage of files processed)
                if total_files > 0:
                    project_progress = min(current_index / total_files, 1.0)
                else:
                    project_progress = 0.0
            else:
                # If file queue isn't processing, use appropriate progress values
                if project_id in self.project_queue_manager.status:
                    status = self.project_queue_manager.status[project_id]
                    if status == ProjectStatus.COMPLETED:
                        project_progress = 1.0
                    elif status == ProjectStatus.FAILED or status == ProjectStatus.CANCELED:
                        project_progress = 0.0
                    else:
                        project_progress = 0.0
                else:
                    project_progress = 0.0
            
            self._progress_callback(
                project_id,
                project,
                project_progress,
                overall_progress
            )
    
    def _calculate_project_statistics(self, file_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics for a processed project.
        
        Args:
            file_results: Dictionary mapping file paths to compression results
            
        Returns:
            Dictionary with project statistics
        """
        stats = {
            "files_processed": 0,
            "files_failed": 0,
            "total_input_size": 0,
            "total_output_size": 0,
            "total_size_reduction": 0,
            "average_reduction_percent": 0,
            "total_processing_time": 0,
        }
        
        # Process file results
        for file_path, result in file_results.items():
            # Check if the result has an error
            if "error" in result:
                stats["files_failed"] += 1
                continue
            
            stats["files_processed"] += 1
            
            # Add sizes
            if "input_size" in result:
                stats["total_input_size"] += result["input_size"]
            
            if "output_size" in result:
                stats["total_output_size"] += result["output_size"]
            
            # Add processing time
            if "duration" in result:
                stats["total_processing_time"] += result["duration"]
        
        # Calculate size reduction
        stats["total_size_reduction"] = stats["total_input_size"] - stats["total_output_size"]
        
        # Calculate average reduction percentage
        if stats["total_input_size"] > 0:
            stats["average_reduction_percent"] = (stats["total_size_reduction"] / stats["total_input_size"]) * 100
        
        # Format human-readable sizes
        stats.update({
            "total_input_size_human": self._format_file_size(stats["total_input_size"]),
            "total_output_size_human": self._format_file_size(stats["total_output_size"]),
            "total_size_reduction_human": self._format_file_size(stats["total_size_reduction"])
        })
        
        return stats
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted string (e.g., "12.34 MB")
        """
        if size_bytes < 0:
            return "0 B"
        
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        suffix_index = 0
        
        while size_bytes >= 1024 and suffix_index < len(suffixes) - 1:
            size_bytes /= 1024.0
            suffix_index += 1
            
        return f"{size_bytes:.2f} {suffixes[suffix_index]}"