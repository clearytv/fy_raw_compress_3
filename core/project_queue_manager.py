#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Queue Manager Module

This module handles the project-level compression queue:
- Managing the list of projects to be processed
- Tracking project status (pending, processing, completed, failed, canceled)
- Sequential processing of projects (one project at a time)
- Saving and loading queue state
- Providing status updates about projects
"""

import os
import logging
import json
import time
from enum import Enum
from typing import List, Dict, Tuple, Optional, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ProjectStatus(Enum):
    """Enum representing the status of a project in the queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ProjectQueueManager:
    """
    Manages a queue of projects to be processed sequentially.
    
    Each project represents a collection of files to be processed with the same settings.
    Projects are processed one at a time, with the next project starting only when
    the current one completes fully.
    """
    
    def __init__(self, state_file_path: str = None):
        """
        Initialize an empty project queue.
        
        Args:
            state_file_path: Optional path to save/load queue state
        """
        # List of project dictionaries containing metadata
        self.projects = []  
        
        # Dictionary mapping project IDs to statuses
        self.status = {}  
        
        # Dictionary storing project results
        self.results = {}  
        
        # Index of the current project being processed
        self.current_index = -1
        
        # Whether a project is currently being processed
        self.is_processing = False
        
        # Track if processing was canceled
        self._canceled = False
        
        # Path to save/load queue state
        self.state_file_path = state_file_path or os.path.join(
            os.path.expanduser("~"), 
            ".forever_yours", 
            "project_queue_state.json"
        )
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
        
        logger.info("Project queue manager initialized")
    
    def add_project(self, project: Dict[str, Any]) -> str:
        """
        Add a project to the queue.
        
        Args:
            project: Dictionary containing project information with keys:
                - name: Project name
                - path: Project folder path
                - files: List of file paths to process
                - settings: Dictionary of compression settings
                - created_at: Timestamp (will be added if not provided)
                
        Returns:
            project_id: Unique identifier for the project
        """
        # Generate a unique ID for the project
        project_id = f"project_{int(time.time())}_{len(self.projects)}"
        
        # Ensure project has required fields
        if "name" not in project:
            project["name"] = f"Project {len(self.projects) + 1}"
            
        if "created_at" not in project:
            project["created_at"] = datetime.now().isoformat()
            
        # Add ID to the project
        project["id"] = project_id
        
        # Add project to the queue
        self.projects.append(project)
        
        # Set status to pending
        self.status[project_id] = ProjectStatus.PENDING
        
        logger.info(f"Added project '{project['name']}' with ID {project_id} to queue")
        
        # Save the updated state
        self.save_state()
        
        return project_id
    
    def add_projects(self, projects: List[Dict[str, Any]]) -> List[str]:
        """
        Add multiple projects to the queue.
        
        Args:
            projects: List of project dictionaries
            
        Returns:
            List of project IDs
        """
        project_ids = []
        
        for project in projects:
            project_id = self.add_project(project)
            project_ids.append(project_id)
            
        return project_ids
    
    def remove_project(self, project_id: str) -> bool:
        """
        Remove a project from the queue.
        
        Args:
            project_id: ID of the project to remove
            
        Returns:
            True if the project was removed, False otherwise
        """
        # Find the project with the given ID
        for i, project in enumerate(self.projects):
            if project.get("id") == project_id:
                # Remove the project
                self.projects.pop(i)
                
                # Remove status and results
                if project_id in self.status:
                    del self.status[project_id]
                if project_id in self.results:
                    del self.results[project_id]
                
                logger.info(f"Removed project with ID {project_id}")
                
                # Save the updated state
                self.save_state()
                
                return True
        
        logger.warning(f"Attempt to remove non-existent project with ID {project_id}")
        return False
    
    def reorder_project(self, project_id: str, new_position: int) -> bool:
        """
        Change the position of a project in the queue.
        
        Args:
            project_id: ID of the project to move
            new_position: New position in the queue (0-based)
            
        Returns:
            True if the project was moved, False otherwise
        """
        # Find the project with the given ID
        project_index = None
        for i, project in enumerate(self.projects):
            if project.get("id") == project_id:
                project_index = i
                break
        
        # If the project was found and the new position is valid
        if project_index is not None and 0 <= new_position < len(self.projects):
            # Cannot move a project that is currently being processed
            if (self.is_processing and 
                self.current_index == project_index and 
                self.status.get(project_id) == ProjectStatus.PROCESSING):
                logger.warning(f"Cannot reorder project {project_id} while it's being processed")
                return False
            
            # Move the project
            project = self.projects.pop(project_index)
            self.projects.insert(new_position, project)
            
            # Update current_index if necessary
            if self.is_processing:
                if project_index == self.current_index:
                    self.current_index = new_position
                elif project_index < self.current_index and new_position >= self.current_index:
                    self.current_index -= 1
                elif project_index > self.current_index and new_position <= self.current_index:
                    self.current_index += 1
            
            logger.info(f"Moved project {project_id} from position {project_index} to {new_position}")
            
            # Save the updated state
            self.save_state()
            
            return True
            
        logger.warning(f"Failed to reorder project {project_id} to position {new_position}")
        return False
    
    def clear_queue(self) -> None:
        """Clear all projects from the queue."""
        # Cannot clear while processing
        if self.is_processing:
            logger.warning("Cannot clear queue while processing projects")
            return
        
        self.projects = []
        self.status = {}
        self.results = {}
        self.current_index = -1
        
        logger.info("Project queue cleared")
        
        # Save the updated state
        self.save_state()
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a project by ID.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Project dictionary or None if not found
        """
        for project in self.projects:
            if project.get("id") == project_id:
                return project
        
        return None
    
    def get_all_projects(self) -> List[Dict[str, Any]]:
        """
        Get all projects with their statuses.
        
        Returns:
            List of project dictionaries with status added
        """
        result = []
        
        for project in self.projects:
            project_id = project.get("id")
            if project_id:
                # Create a copy of the project with status added
                project_copy = project.copy()
                project_copy["status"] = self.status.get(project_id, ProjectStatus.PENDING).value
                
                # Add results if available
                if project_id in self.results:
                    project_copy["results"] = self.results[project_id]
                
                result.append(project_copy)
        
        return result
    
    def save_state(self) -> bool:
        """
        Save the queue state to a file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert projects to serializable format
            serializable_projects = []
            for project in self.projects:
                # Create a deep copy to avoid modifying the original
                project_copy = project.copy()
                serializable_projects.append(project_copy)
            
            # Convert status to serializable format
            serializable_status = {
                project_id: status.value 
                for project_id, status in self.status.items()
            }
            
            # Create the state dictionary
            state = {
                "projects": serializable_projects,
                "status": serializable_status,
                "results": self.results,
                "current_index": self.current_index,
                "is_processing": self.is_processing,
                "saved_at": datetime.now().isoformat()
            }
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.state_file_path), exist_ok=True)
            
            # Save to file
            with open(self.state_file_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Queue state saved to {self.state_file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save queue state: {str(e)}", exc_info=True)
            return False
    
    def load_state(self) -> bool:
        """
        Load the queue state from a file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the file exists
            if not os.path.exists(self.state_file_path):
                logger.info(f"No queue state file found at {self.state_file_path}")
                return False
            
            # Load from file
            with open(self.state_file_path, 'r') as f:
                state = json.load(f)
            
            # Restore projects
            self.projects = state.get("projects", [])
            
            # Restore status (convert string values back to enum)
            string_status = state.get("status", {})
            self.status = {
                project_id: ProjectStatus(status_str)
                for project_id, status_str in string_status.items()
            }
            
            # Restore results
            self.results = state.get("results", {})
            
            # Restore indices and flags
            self.current_index = state.get("current_index", -1)
            self.is_processing = state.get("is_processing", False)
            
            # If we were processing but the application was closed,
            # reset to not processing
            if self.is_processing:
                self.is_processing = False
                logger.warning("Resetting processing flag from previous incomplete run")
                
                # Mark any projects that were in progress as pending
                for project_id, status in self.status.items():
                    if status == ProjectStatus.PROCESSING:
                        self.status[project_id] = ProjectStatus.PENDING
                        logger.info(f"Reset project {project_id} status from PROCESSING to PENDING")
            
            logger.info(f"Queue state loaded from {self.state_file_path} with {len(self.projects)} projects")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load queue state: {str(e)}", exc_info=True)
            return False
    
    def start_processing(
        self, 
        process_project_func: Callable[[Dict[str, Any]], Tuple[bool, Dict[str, Any]]],
        progress_callback: Optional[Callable[[str, Dict[str, Any], float], None]] = None
    ) -> bool:
        """
        Start processing projects in the queue sequentially.
        
        Args:
            process_project_func: Function to process a single project.
                It should take a project dictionary and return a tuple of
                (success: bool, results: Dict)
            progress_callback: Optional callback for progress updates
                It receives (project_id, project_dict, overall_progress)
            
        Returns:
            True if started successfully, False otherwise
        """
        if self.is_processing:
            logger.warning("Project queue is already being processed")
            return False
        
        # Check if queue is empty
        if not self.projects:
            logger.warning("Cannot process queue: Project queue is empty")
            return False
        
        # Find first pending project
        start_index = 0
        for i, project in enumerate(self.projects):
            project_id = project.get("id")
            if project_id and self.status.get(project_id) == ProjectStatus.PENDING:
                start_index = i
                break
        else:
            # No pending projects found
            logger.warning("No pending projects found in queue")
            return False
        
        # Initialize processing
        self.is_processing = True
        self.current_index = start_index
        self._canceled = False
        
        # Start processing in a new thread
        import threading
        thread = threading.Thread(
            target=self._process_queue,
            args=(process_project_func, progress_callback),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Started processing project queue at index {start_index}")
        return True
    
    def _process_queue(
        self, 
        process_project_func: Callable[[Dict[str, Any]], Tuple[bool, Dict[str, Any]]],
        progress_callback: Optional[Callable[[str, Dict[str, Any], float], None]] = None
    ) -> bool:
        """
        Process all projects in the queue sequentially.
        
        This method is typically run in a separate thread.
        
        Args:
            process_project_func: Function to process a single project
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if all projects were processed successfully, False otherwise
        """
        # Track overall success
        all_success = True
        
        try:
            # Calculate total pending projects
            total_pending = 0
            for project in self.projects[self.current_index:]:
                project_id = project.get("id")
                if project_id and self.status.get(project_id) == ProjectStatus.PENDING:
                    total_pending += 1
            
            # Track completed projects for progress calculation
            completed_count = 0
            
            # Process each project sequentially
            while self.current_index < len(self.projects) and not self._canceled:
                current_project = self.projects[self.current_index]
                project_id = current_project.get("id")
                
                # Skip projects that aren't pending
                if project_id and self.status.get(project_id) != ProjectStatus.PENDING:
                    self.current_index += 1
                    continue
                
                # Update status to processing
                self.status[project_id] = ProjectStatus.PROCESSING
                logger.info(f"Processing project {self.current_index + 1}/{len(self.projects)}: {current_project.get('name')} (ID: {project_id})")
                
                # Save state to reflect the change
                self.save_state()
                
                # Process current project
                start_time = time.time()
                try:
                    success, result = process_project_func(current_project)
                except Exception as e:
                    logger.error(f"Error processing project {project_id}: {str(e)}", exc_info=True)
                    success = False
                    result = {"error": str(e)}
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                # Update status and result
                if success:
                    self.status[project_id] = ProjectStatus.COMPLETED
                    
                    # Add processing time to results
                    result["processing_time"] = processing_time
                    self.results[project_id] = result
                    
                    logger.info(f"Successfully processed project {project_id} in {processing_time:.2f} seconds")
                else:
                    # Check if failure was due to cancellation
                    if self._canceled:
                        self.status[project_id] = ProjectStatus.CANCELED
                        self.results[project_id] = {"error": "Canceled by user", "processing_time": processing_time}
                        logger.info(f"Processing of project {project_id} was canceled by user")
                    else:
                        self.status[project_id] = ProjectStatus.FAILED
                        
                        # Add processing time to results
                        if isinstance(result, dict):
                            result["processing_time"] = processing_time
                        else:
                            result = {"error": "Processing failed", "processing_time": processing_time}
                        
                        self.results[project_id] = result
                        logger.error(f"Failed to process project {project_id}")
                        all_success = False
                
                # Save state to persist results
                self.save_state()
                
                # Move to next project
                self.current_index += 1
                completed_count += 1
                
                # Update progress
                if progress_callback and total_pending > 0:
                    overall_progress = completed_count / total_pending
                    progress_callback(project_id, current_project, overall_progress)
                
            # If canceled, mark remaining projects
            if self._canceled:
                logger.info("Queue processing was canceled")
                for i in range(self.current_index, len(self.projects)):
                    project = self.projects[i]
                    project_id = project.get("id")
                    if project_id and self.status.get(project_id) == ProjectStatus.PENDING:
                        self.status[project_id] = ProjectStatus.CANCELED
                
                # Save state to persist cancellation
                self.save_state()
        
        except Exception as e:
            logger.error(f"Error during project queue processing: {str(e)}", exc_info=True)
            all_success = False
        
        finally:
            self.is_processing = False
            logger.info(f"Project queue processing completed {'successfully' if all_success else 'with errors'}")
            
            # Final save state
            self.save_state()
            
            return all_success
    
    def cancel_processing(self) -> bool:
        """
        Cancel ongoing queue processing.
        
        Returns:
            True if cancellation was initiated, False if not processing
        """
        if not self.is_processing:
            logger.warning("Cannot cancel: queue is not being processed")
            return False
        
        logger.info("Canceling project queue processing")
        self._canceled = True
        
        return True
    
    def get_queue_status(self) -> Dict[str, int]:
        """
        Get the current status counts of the queue.
        
        Returns:
            Dictionary with queue statistics
        """
        stats = {
            "total": len(self.projects),
            "pending": sum(1 for s in self.status.values() if s == ProjectStatus.PENDING),
            "processing": sum(1 for s in self.status.values() if s == ProjectStatus.PROCESSING),
            "completed": sum(1 for s in self.status.values() if s == ProjectStatus.COMPLETED),
            "failed": sum(1 for s in self.status.values() if s == ProjectStatus.FAILED),
            "canceled": sum(1 for s in self.status.values() if s == ProjectStatus.CANCELED),
        }
        
        return stats
    
    def get_next_pending_project(self) -> Optional[Dict[str, Any]]:
        """
        Get the next pending project in the queue.
        
        Returns:
            Project dictionary or None if no pending projects
        """
        for project in self.projects:
            project_id = project.get("id")
            if project_id and self.status.get(project_id) == ProjectStatus.PENDING:
                return project
        
        return None

    def get_results_summary(self) -> Dict[str, Any]:
        """
        Get a summary of project processing results.
        
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_projects": len(self.projects),
            "completed_projects": 0,
            "failed_projects": 0,
            "total_processing_time": 0,
            "total_files_processed": 0,
            "total_input_size": 0,
            "total_output_size": 0,
            "total_size_reduction": 0,
            "average_reduction_percent": 0,
        }
        
        # Collect statistics from all projects with results
        for project_id, result in self.results.items():
            if self.status.get(project_id) == ProjectStatus.COMPLETED:
                summary["completed_projects"] += 1
                
                # Add processing time
                if "processing_time" in result:
                    summary["total_processing_time"] += result["processing_time"]
                
                # Add file counts
                if "files_processed" in result:
                    summary["total_files_processed"] += result["files_processed"]
                
                # Add size information
                if "total_input_size" in result:
                    summary["total_input_size"] += result["total_input_size"]
                if "total_output_size" in result:
                    summary["total_output_size"] += result["total_output_size"]
            
            elif self.status.get(project_id) == ProjectStatus.FAILED:
                summary["failed_projects"] += 1
        
        # Calculate derived statistics
        if summary["total_input_size"] > 0:
            summary["total_size_reduction"] = summary["total_input_size"] - summary["total_output_size"]
            summary["average_reduction_percent"] = (
                summary["total_size_reduction"] / summary["total_input_size"] * 100
            )
        
        return summary