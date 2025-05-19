#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forever Yours RAW Compression Tool

Main entry point for the video compression application.
This file initializes the GUI and connects core functionality.
"""

import sys
import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import QSettings, Qt
from core.log_rotation import get_line_limited_logger

# Set up logging
os.makedirs('logs', exist_ok=True)
# Use custom line count rotating logger instead of basic config
# This will limit the log file to 100 lines maximum
# Configure the root logger so all modules use this handler by default
root_logger = logging.getLogger() # Get the root logger
get_line_limited_logger(
    None, # Pass None or "" to configure the root logger via our custom function
    'logs/compress.log',
    max_lines=100, # Or a higher number for debugging like 500
    level=logging.INFO,
    log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Get a logger for the current module, which will now use the root's handlers
logger = logging.getLogger(__name__)


# Import GUI components
from gui.step1_import import ImportPanel
from gui.step2_convert import ConvertPanel
from gui.step2b_verify import VerifyPanel # New verification panel
from gui.step3_results import ResultsPanel
from gui.project_queue_panel import ProjectQueuePanel  # New project queue panel

# Import core functionality
from core.queue_manager import QueueManager
from core.project_queue_manager import ProjectQueueManager, ProjectStatus
from core.project_manager import ProjectManager


class MainWindow(QMainWindow):
    """
    Main application window containing the workflow steps.
    Manages navigation between steps and shares data between them.
    """
    
    def __init__(self):
        """Initialize main window with step panels."""
        super().__init__()
        logger.info("Creating main application window")
        
        self.setWindowTitle("Forever Yours Compression")
        
        # Set window to stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        # Initialize with default size if settings don't exist
        self.resize(800, 600)
        
        # Restore window geometry from previous session
        self.restore_window_geometry()
        
        # Create managers for handling projects and files
        self.queue_manager = QueueManager()  # For managing files within a single project
        self.project_queue_manager = ProjectQueueManager()  # For managing multiple projects
        self.project_manager = ProjectManager(self.project_queue_manager)  # Interface between project queue and file queue
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create stacked widget to hold step panels
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Create workflow step panels
        self.import_panel = ImportPanel(self)
        self.convert_panel = ConvertPanel(self)
        self.verify_panel = VerifyPanel(self) # Instantiate verification panel
        self.results_panel = ResultsPanel(self)
        self.project_queue_panel = ProjectQueuePanel(self, self.project_manager)  # Create project queue panel
        
        # Add panels to stacked widget
        self.stacked_widget.addWidget(self.import_panel)  # Index 0
        self.stacked_widget.addWidget(self.convert_panel) # Index 1
        self.stacked_widget.addWidget(self.verify_panel)  # Index 2
        self.stacked_widget.addWidget(self.results_panel) # Index 3
        self.stacked_widget.addWidget(self.project_queue_panel) # Index 4
        
        # Set queue manager in panels that need it
        self.convert_panel.set_queue_manager(self.queue_manager)
        
        # Connect signals between panels
        self._connect_signals()
        
        # Start with project queue panel
        self.stacked_widget.setCurrentIndex(4)  # Start with project queue panel
        logger.info(f"Starting application with panel index set to {self.stacked_widget.currentIndex()}")
        
    def _connect_signals(self):
        """Connect signals between panels for workflow navigation."""
        # Import panel signals
        self.import_panel.files_selected.connect(self.on_files_selected)
        # self.import_panel.next_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Old direct connection
        self.import_panel.next_clicked.connect(self.go_to_convert_panel) # New method
        
        # Convert panel signals
        # self.convert_panel.compression_complete.connect(self.on_compression_complete) # This might still be useful for logging
        self.convert_panel.verification_needed.connect(self.go_to_verify_panel) # New signal for verification
        self.convert_panel.back_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Corrected: ConvertPanel is index 1
        # self.convert_panel.next_clicked is no longer directly connected here for forward navigation
        
        # Connect the compression_complete signal for logging or data handling if needed
        self.convert_panel.compression_complete.connect(self.on_compression_complete)

        # Verify panel signals
        self.verify_panel.back_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Back to ConvertPanel (index 1)
        self.verify_panel.next_clicked.connect(self.go_to_results_panel)
        
        # Results panel signals
        self.results_panel.new_job_requested.connect(self.reset_workflow)
        
        # Project queue panel signals
        self.project_queue_panel.back_clicked.connect(lambda: self.go_to_import_panel())
        self.project_queue_panel.project_selected.connect(self.edit_project)
        self.project_queue_panel.add_project_requested.connect(self.handle_add_project_request)
        
    def on_files_selected(self, files):
        """Handle files selected from import panel."""
        logger.info(f"Main window received {len(files)} files from import panel")
        
        # Verify that we have valid files before proceeding
        if not files:
            logger.warning("No valid files received, not proceeding to next step")
            return
            
        self.queue_manager.add_files(files)
        self.convert_panel.set_queued_files(files)

    def go_to_convert_panel(self):
        """Transition from Import panel to Convert panel, passing necessary data."""
        parent_folder = self.import_panel.parent_folder
        if parent_folder:
            self.convert_panel.set_parent_folder_path(parent_folder)
            logger.info(f"Passing parent folder path to ConvertPanel: {parent_folder}")
        else:
            logger.warning("No parent folder path available from ImportPanel to pass to ConvertPanel.")
        
        # Pass the rename folders preference from Step 1 to Step 2
        rename_folders_option = self.import_panel.rename_folders
        self.convert_panel.set_rename_option(rename_folders_option)
        logger.info(f"Passing rename folders option to ConvertPanel: {rename_folders_option}")
        
        # Pass the auto mode preference from Step 1 to Step 2
        auto_mode_option = self.import_panel.auto_mode
        self.convert_panel.set_auto_mode(auto_mode_option)
        logger.info(f"Passing auto mode option to ConvertPanel: {auto_mode_option}")
        
        self.stacked_widget.setCurrentIndex(1) # ConvertPanel is index 1

    def go_to_verify_panel(self, main_path, original_path, converted_path):
        """Transition from Convert panel to Verify panel."""
        logger.info(f"Transitioning to Verify Panel. Main: {main_path}, Orig: {original_path}, Conv: {converted_path}")
        if not main_path or not original_path or not converted_path:
            logger.error(f"Cannot go to verify panel, one or more paths are missing. Main='{main_path}', Orig='{original_path}', Conv='{converted_path}'")
            # Optionally show a message to the user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Path Error", "Cannot proceed to verification due to missing folder path information.")
            return
            
        # Pass auto mode setting from ConvertPanel to VerifyPanel
        auto_mode_option = self.convert_panel.auto_mode
        self.verify_panel.set_auto_mode(auto_mode_option)
        logger.info(f"Passing auto mode option to VerifyPanel: {auto_mode_option}")
        
        self.verify_panel.set_paths(main_path, original_path, converted_path)
        self.stacked_widget.setCurrentIndex(2) # Verify Panel is index 2
        
        # If auto mode is enabled, automatically run verification after a delay
        if auto_mode_option:
            from PyQt6.QtCore import QTimer
            logger.info("Auto mode enabled: Will automatically run verification after 2-second delay")
            QTimer.singleShot(2000, self.verify_panel.process_verification)

    def go_to_results_panel(self):
        """Transition to the Results panel, typically from Verify panel."""
        logger.info("Transitioning to Results Panel.")
        
        parent_folder_path_for_results = self.convert_panel.parent_folder_path
        # Or, if VerifyPanel modifies/confirms the main project path, get it from there:
        # parent_folder_path_for_results = self.verify_panel.main_project_folder_path
        
        if parent_folder_path_for_results:
            self.results_panel.set_parent_folder_path(parent_folder_path_for_results)
            logger.info(f"Passing parent folder path to ResultsPanel: {parent_folder_path_for_results}")
        else:
            logger.warning("No parent folder path available to pass to ResultsPanel.")
            
        # Update project status if this is a project from the queue
        if hasattr(self, 'current_project_id') and self.current_project_id:
            # Create project results from verification results
            project_results = self._build_project_results_from_verification()
            
            # Add project results to the queue manager
            self.project_queue_manager.results[self.current_project_id] = project_results
            
            # Update project status to completed
            self.project_queue_manager.status[self.current_project_id] = ProjectStatus.COMPLETED
            
            logger.info(f"Updated project {self.current_project_id} status to COMPLETED with results")
            
            # Save the queue state
            self.project_queue_manager.save_state()
        
        # Handle case when we're creating a new project for the queue
        elif hasattr(self, 'creating_project_for_queue') and self.creating_project_for_queue:
            logger.info("Creating new project for queue from completed workflow")
            
            # Create a new project from the current workflow
            if self.queue_manager.files:
                project_id = self.project_queue_manager.generate_id()
                parent_folder = self.convert_panel.parent_folder_path
                
                project = {
                    "id": project_id,
                    "name": os.path.basename(parent_folder) if parent_folder else "Untitled Project",
                    "status": "pending",
                    "input_files": self.queue_manager.files.copy(),
                    "parent_folder": parent_folder,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Add to queue
                self.project_queue_manager.add_project(project_id, project)
                logger.info(f"Added new project {project_id} to queue")
                
                # Save the queue state
                self.project_queue_manager.save_state()
                
                # Reset flag
                self.creating_project_for_queue = False
                
                # Return to queue panel
                self.stacked_widget.setCurrentIndex(4)  # Project queue panel
                return  # Skip the normal transition to ResultsPanel
        
        # Get total compression duration from ConvertPanel
        total_duration = self.convert_panel.total_compression_duration
        logger.info(f"Total compression duration: {total_duration:.2f} seconds")
        
        # Convert verification results to format expected by ResultsPanel
        compression_results = {}
        
        # Get verification results from VerifyPanel
        verification_results = self.verify_panel.verification_results
        
        # Process each verification result into the format expected by ResultsPanel
        for item in verification_results:
            original_file = item.get('original_file', '')
            converted_file = item.get('converted_file', '')
            status = item.get('status', '')
            mismatches = item.get('mismatches', [])
            
            # Skip entries without both files
            if not original_file or not converted_file:
                continue
                
            # For each file pair, create an entry in compression_results
            if status == "MATCH":
                try:
                    # Function to format sizes in human-readable form
                    def format_size(size_bytes):
                        if size_bytes >= 1024*1024*1024:
                            return f"{size_bytes/(1024*1024*1024):.2f} GB"
                        else:
                            return f"{size_bytes/(1024*1024):.2f} MB"
                    
                    # Check if the converted file exists
                    if os.path.exists(converted_file):
                        conv_size = os.path.getsize(converted_file)
                        
                        # Try to get original file size if it exists
                        if os.path.exists(original_file):
                            orig_size = os.path.getsize(original_file)
                        else:
                            # Original file probably deleted after verification passed
                            # Get size info from properties if available
                            original_props = item.get('original_properties', {})
                            # Convert to bytes (approximate if not available)
                            # Bit rate * duration / 8 (to convert bits to bytes)
                            orig_size = conv_size * 3  # Default to 3x if no better estimate available
                        
                        size_diff = orig_size - conv_size
                        reduction_percent = (size_diff / orig_size * 100) if orig_size > 0 else 0
                        
                        compression_results[converted_file] = {  # Use converted_file as key since original may not exist
                            'input_size': orig_size,
                            'output_size': conv_size,
                            'size_diff': size_diff,
                            'reduction_percent': reduction_percent,
                            'input_size_human': format_size(orig_size),
                            'output_size_human': format_size(conv_size),
                            'size_diff_human': format_size(size_diff),
                            'duration': 0  # Set to zero for all files, we'll use a different approach
                        }
                    else:
                        logger.error(f"Converted file not found: {converted_file}")
                        compression_results[converted_file] = {
                            'error': f"Converted file not found: {os.path.basename(converted_file)}"
                        }
                except Exception as e:
                    logger.error(f"Error processing file sizes for {converted_file}: {e}")
                    compression_results[converted_file] = {
                        'error': f"Error processing data: {str(e)}"
                    }
            else:
                # For non-matches, add as error
                error_message = f"Verification {status}: {'; '.join(mismatches)}"
                # Use converted_file as key if available, otherwise use original_file
                key_file = converted_file if converted_file else original_file
                compression_results[key_file] = {
                    'error': error_message
                }
        
        # Create special entry with just the duration info to avoid double-counting
        duration_key = "total_duration_info"
        compression_results[duration_key] = {
            'input_size': 0,
            'output_size': 0,
            'size_diff': 0,
            'reduction_percent': 0,
            'input_size_human': "0 MB",
            'output_size_human': "0 MB",
            'size_diff_human': "0 MB",
            'duration': total_duration,  # Store the total duration in a single entry
            'is_duration_info': True  # Flag for ResultsPanel to identify this special entry
        }
        # Pass the results to the ResultsPanel
        self.results_panel.set_compression_results(compression_results)
        logger.info(f"Passed {len(compression_results)} results to ResultsPanel with total_duration={total_duration:.2f}s")
        
        self.stacked_widget.setCurrentIndex(3) # Results Panel is index 3
    
    def _build_project_results_from_verification(self):
        """
        Build project results from verification results.
        
        Returns:
            Dictionary with project statistics
        """
        # Get verification results
        verification_results = self.verify_panel.verification_results
        
        # Initialize statistics
        stats = {
            "files_processed": 0,
            "files_failed": 0,
            "total_input_size": 0,
            "total_output_size": 0,
            "total_size_reduction": 0,
            "average_reduction_percent": 0,
            "processing_time": self.convert_panel.total_compression_duration
        }
        
        # Process verification results
        for item in verification_results:
            original_file = item.get('original_file', '')
            converted_file = item.get('converted_file', '')
            status = item.get('status', '')
            
            if status == "MATCH" and os.path.exists(converted_file):
                stats["files_processed"] += 1
                
                # Get file sizes
                conv_size = os.path.getsize(converted_file)
                stats["total_output_size"] += conv_size
                
                # Try to get original file size
                if os.path.exists(original_file):
                    orig_size = os.path.getsize(original_file)
                else:
                    # Use approximate size if original doesn't exist
                    orig_size = conv_size * 3  # Default multiplier
                    
                stats["total_input_size"] += orig_size
            else:
                stats["files_failed"] += 1
                
        # Calculate reduction
        stats["total_size_reduction"] = stats["total_input_size"] - stats["total_output_size"]
        
        # Calculate average reduction percentage
        if stats["total_input_size"] > 0:
            stats["average_reduction_percent"] = (stats["total_size_reduction"] / stats["total_input_size"]) * 100
            
        # Format human-readable sizes
        def format_size(size_bytes):
            if size_bytes < 0:
                return "0 B"
            
            suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
            suffix_index = 0
            
            while size_bytes >= 1024 and suffix_index < len(suffixes) - 1:
                size_bytes /= 1024.0
                suffix_index += 1
                
            return f"{size_bytes:.2f} {suffixes[suffix_index]}"
            
        stats.update({
            "total_input_size_human": format_size(stats["total_input_size"]),
            "total_output_size_human": format_size(stats["total_output_size"]),
            "total_size_reduction_human": format_size(stats["total_size_reduction"])
        })
        
        return stats
        
    def on_compression_complete(self, results):
        """
        Handle compression completion from convert panel.
        This signal is emitted by ConvertPanel when its processing queue finishes,
        BEFORE it emits 'verification_needed'.
        Its primary role now is for logging or if any immediate data from 'results'
        (currently an empty dict) needs to be handled.
        Actual navigation to the next step (VerifyPanel) is triggered by 'verification_needed'.
        """
        logger.info(f"Main window received 'compression_complete' signal from ConvertPanel. Results: {results}")
        # No direct navigation from here anymore.
        # ConvertPanel.finish_compression will emit 'verification_needed' if successful,
        # which then calls self.go_to_verify_panel.
    

    def reset_workflow(self):
        """Reset the workflow to start a new job."""
        logger.info("Resetting workflow - clearing queue and going to step 1")
        self.queue_manager.clear_queue()
        
        # Reset all panel states
        self.import_panel.reset_panel()
        self.convert_panel.reset_panel()
        if hasattr(self, 'verify_panel'): # Check if verify_panel exists
            self.verify_panel.reset_panel_state()
        self.results_panel.reset_panel()
        if hasattr(self, 'project_queue_panel'):
            self.project_queue_panel.reset_panel()
        
        # Clear current project reference
        if hasattr(self, 'current_project_id'):
            self.current_project_id = None
            
        # Clear project creation flag
        if hasattr(self, 'creating_project_for_queue'):
            self.creating_project_for_queue = False
        
        # Return to project queue panel instead of import panel
        self.stacked_widget.setCurrentIndex(4)  # Project queue panel
        logger.info(f"Current index set to {self.stacked_widget.currentIndex()}")
    
    def go_to_import_panel(self):
        """Navigate to the import panel to start a single project workflow."""
        logger.info("Transitioning to Import Panel to create a new project.")
        self.stacked_widget.setCurrentIndex(0)  # Import panel index
    
    def go_to_project_queue_panel(self):
        """Navigate back to the project queue panel."""
        logger.info("Returning to Project Queue Panel.")
        self.stacked_widget.setCurrentIndex(4)  # Project queue panel index
        
        # If we just added a project to the queue, refresh the panel
        if hasattr(self, 'project_queue_panel'):
            self.project_queue_panel.refresh_projects()
    
    def edit_project(self, project_id):
        """
        Start editing an existing project.
        
        Args:
            project_id: ID of the project to edit
        """
        logger.info(f"Starting to edit project with ID {project_id}")
        
        # Get project from queue manager
        project = self.project_queue_manager.get_project(project_id)
        if not project:
            logger.warning(f"Project with ID {project_id} not found")
            return
        
        # Store current project ID for reference
        self.current_project_id = project_id
        
        # Extract project data
        input_files = project.get("input_files", [])
        output_dir = project.get("output_dir", "")
        
        # Set up ImportPanel with project data
        # For now, we'll just pass the files to the import panel
        if input_files:
            self.queue_manager.clear_queue()
            self.queue_manager.add_files(input_files)
            self.import_panel.set_selected_files(input_files)
            
            # If project has a parent folder, set it
            if "parent_folder" in project:
                self.import_panel.set_parent_folder(project["parent_folder"])
                
            # Navigate to the import panel
            self.stacked_widget.setCurrentIndex(0)
        else:
            logger.warning(f"Project {project_id} has no input files to edit")
            
    def handle_add_project_request(self):
        """
        Handle request to add a new project to the queue.
        This method is called when the user clicks 'Add Project' in the ProjectQueuePanel.
        
        Modified to directly add projects to the queue without processing:
        - Shows a folder selection dialog
        - Adds the selected folder as a pending project to the queue
        - Returns to the ProjectQueuePanel
        """
        logger.info("Handling add project request - adding project to queue directly")
        
        # Open folder dialog to select project folder(s)
        from PyQt6.QtWidgets import QFileDialog
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Wedding Footage Folder",
            os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder:
            logger.info("No folder selected, canceling project addition")
            return
            
        logger.info(f"Selected folder: {folder}")
        
        # Find video files in the project structure (similar to ImportPanel.select_folder)
        try:
            # Expected standard structure
            media_path = os.path.join(folder, "03 MEDIA")
            video_path = os.path.join(media_path, "01 VIDEO")
            cam_folders = []
            input_files = []
            
            if not os.path.exists(media_path):
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Invalid Folder Structure",
                    f"'03 MEDIA' folder not found in {folder}.\n\nPlease select a folder with the standard wedding structure."
                )
                return
                
            if not os.path.exists(video_path):
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Invalid Folder Structure",
                    f"'01 VIDEO' folder not found in '03 MEDIA'.\n\nPlease select a folder with the standard wedding structure."
                )
                return
            
            # Find CAM folders
            for item in os.listdir(video_path):
                item_path = os.path.join(video_path, item)
                if os.path.isdir(item_path) and "CAM" in item.upper():
                    cam_folders.append(item_path)
            
            if not cam_folders:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "No CAM Folders",
                    "No CAM folders found in the '01 VIDEO' directory.\n\nPlease select a folder with the standard wedding structure."
                )
                return
                
            # Find video files in CAM folders
            for cam_folder in cam_folders:
                for file_name in os.listdir(cam_folder):
                    file_path = os.path.join(cam_folder, file_name)
                    if os.path.isfile(file_path):
                        _, ext = os.path.splitext(file_path)
                        if ext.lower() in ['.mov', '.mp4']:
                            input_files.append(file_path)
            
            if not input_files:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "No Video Files",
                    "No valid video files found in CAM folders.\n\nPlease select a folder with video files."
                )
                return
                
            # Create a new project and add to queue
            project_name = os.path.basename(folder)
            
            # Import the default compression settings
            from core.video_compression import get_compression_settings
            
            project = {
                "name": project_name,
                "input_files": input_files,
                "parent_folder": folder,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "output_dir": os.path.join(folder, "03 MEDIA", "01 VIDEO"),
                "settings": get_compression_settings()  # Add default compression settings
            }
            
            # Add to queue without processing - this returns the project_id
            project_id = self.project_queue_manager.add_project(project)
            logger.info(f"Added new project {project_id} with {len(input_files)} files to queue")
            
            # Refresh the project queue panel
            self.project_queue_panel.refresh_projects()
            
            # Show confirmation
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Project Added",
                f"Project '{project_name}' with {len(input_files)} video files has been added to the queue."
            )
            
        except Exception as e:
            logger.error(f"Error adding project to queue: {str(e)}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while adding the project to the queue:\n\n{str(e)}"
            )
            
    def save_window_geometry(self):
        """Save the window's geometry (size and position)"""
        settings = QSettings("ForeverYours", "CompressionTool")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        logger.info("Saved window geometry and state")
    
    def restore_window_geometry(self):
        """Restore the window's geometry from saved settings"""
        settings = QSettings("ForeverYours", "CompressionTool")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))
            logger.info("Restored window geometry and state from settings")
        else:
            logger.info("No saved window geometry found, using defaults")
    
    def closeEvent(self, event):
        """Override close event to save window geometry before closing"""
        self.save_window_geometry()
        super().closeEvent(event)


def main():
    """
    Initialize and run the application.
    """
    try:
        logger.info("Starting Forever Yours Compression Tool")
        
        # Initialize application
        app = QApplication(sys.argv)
        app.setApplicationName("Forever Yours Compression")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()