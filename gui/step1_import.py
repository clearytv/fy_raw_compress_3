#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import Panel Module

This module handles the first step of the compression workflow:
- File/folder selection
- Input validation
- Adding files to the compression queue
"""

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QListWidget, QListWidgetItem,
    QFrame, QCheckBox, QMessageBox, QSplitter, QGroupBox,
    QProgressDialog, QApplication
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QFont, QIcon

# Import core functionality
from core.file_preparation import scan_directory, validate_video_file, find_cam_folders, rename_video_folder

logger = logging.getLogger(__name__)


class ScanWorker(QObject):
    """
    Worker class for running folder scanning and file validation in a background thread.
    """
    # Signal to report found CAM folders
    cam_folders_found = pyqtSignal(list)
    # Signal to report found files
    files_found = pyqtSignal(list)
    # Signal to report status updates
    status_update = pyqtSignal(str, str)
    # Signal to report progress
    progress_update = pyqtSignal(int, int)
    # Signal to report completion
    task_completed = pyqtSignal()
    # Signal to report errors
    error_occurred = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.folder_path = ""
        self.cancel_requested = False
    
    def set_folder(self, folder_path):
        """Set the folder path to scan."""
        self.folder_path = folder_path
        self.cancel_requested = False
    
    @pyqtSlot()
    def scan_folder(self):
        """Scan the folder for CAM folders and video files using the known structure."""
        try:
            # Reset signal
            self.cancel_requested = False
            
            # Check if folder exists
            if not os.path.exists(self.folder_path):
                self.error_occurred.emit(f"Folder does not exist: {self.folder_path}")
                return
                
            # Direct path to the expected video location (standard wedding folder structure)
            media_path = os.path.join(self.folder_path, "03 MEDIA")
            video_path = os.path.join(media_path, "01 VIDEO")
            
            self.status_update.emit("Checking for standard folder structure...", "#666")
            
            # Quick validation of the standard structure
            if not os.path.exists(media_path):
                self.error_occurred.emit("'03 MEDIA' folder not found")
                return
                
            if not os.path.exists(video_path):
                self.error_occurred.emit("'01 VIDEO' folder not found in '03 MEDIA'")
                return
            
            # Find CAM folders - expected to be direct children of the video path
            self.status_update.emit("Finding CAM folders...", "#666")
            
            # Get CAM folders without walking the entire directory tree
            try:
                # Direct list of folders rather than full recursive search
                potential_cam_folders = []
                for item in os.listdir(video_path):
                    item_path = os.path.join(video_path, item)
                    if os.path.isdir(item_path) and "CAM" in item.upper():
                        potential_cam_folders.append(item_path)
                        
                cam_folders = potential_cam_folders
            except Exception as e:
                self.error_occurred.emit(f"Error listing CAM folders: {str(e)}")
                return
            
            if not cam_folders:
                self.status_update.emit("No CAM folders found in '01 VIDEO'", "orange")
                self.task_completed.emit()
                return
            
            self.status_update.emit(f"Found {len(cam_folders)} CAM folders", "green")
            self.cam_folders_found.emit(cam_folders)
            
            # Check if operation was cancelled
            if self.cancel_requested:
                self.status_update.emit("Operation cancelled", "orange")
                self.task_completed.emit()
                return
            
            # Process files - scan only the direct CAM folders without deep recursion
            valid_files = []
            self.status_update.emit("Scanning for video files...", "#666")
            
            # Create a list to track progress
            total_folders = len(cam_folders)
            
            # For each CAM folder, only look at direct files (no deep recursion)
            for i, cam_folder in enumerate(cam_folders):
                if self.cancel_requested:
                    break
                
                folder_name = os.path.basename(cam_folder)
                self.status_update.emit(f"Scanning {folder_name} ({i+1}/{total_folders})", "#666")
                self.progress_update.emit(i, total_folders)
                
                # Skip FFmpeg validation during initial scan - just check extensions
                try:
                    for file_name in os.listdir(cam_folder):
                        if self.cancel_requested:
                            break
                            
                        file_path = os.path.join(cam_folder, file_name)
                        if os.path.isfile(file_path):
                            _, ext = os.path.splitext(file_path)
                            if ext.lower() in ['.mov', '.mp4']:
                                valid_files.append(file_path)
                except Exception as e:
                    logger.error(f"Error scanning CAM folder {cam_folder}: {str(e)}", exc_info=True)
            
            # Report final results
            if self.cancel_requested:
                self.status_update.emit("Operation cancelled", "orange")
            else:
                if valid_files:
                    self.status_update.emit(f"Found {len(valid_files)} valid video files", "green")
                    self.files_found.emit(valid_files)
                else:
                    self.status_update.emit("No valid video files found", "orange")
            
            self.task_completed.emit()
            
        except Exception as e:
            logger.error(f"Error in scan_folder: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"Error: {str(e)}")
            self.task_completed.emit()
    
    def cancel(self):
        """Cancel the current operation."""
        self.cancel_requested = True


class ImportPanel(QWidget):
    """
    Panel for importing and validating video files.
    Responsible for file selection UI and validation before adding to queue.
    """
    # Signal to notify when files are ready for compression
    files_selected = pyqtSignal(list)
    # Signal to navigate to next panel
    next_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the import panel with file selection components."""
        super().__init__(parent)
        logger.info("Initializing import panel")
        
        self.parent_folder = ""
        self.cam_folders = []
        self.valid_files = []
        self.rename_folders = True
        
        # Create worker thread and worker
        self.worker_thread = QThread()
        self.worker = ScanWorker()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect worker signals
        self.worker.cam_folders_found.connect(self.on_cam_folders_found)
        self.worker.files_found.connect(self.on_files_found)
        self.worker.status_update.connect(self.on_status_update)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.task_completed.connect(self.on_task_completed)
        
        # Connect thread start to worker processing slot
        self.worker_thread.started.connect(self.worker.scan_folder)
        
        # Progress dialog
        self.progress_dialog = None
        
        # Create UI components
        self._init_ui()
        # Connect signals and slots
        self._connect_signals()
    
    def _init_ui(self):
        """Set up the user interface components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Step 1: Import Folder")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Select a parent folder containing wedding footage. "
            "The tool will look for CAM folders within the '03 MEDIA/01 VIDEO' structure."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Folder selection section
        folder_group = QGroupBox("Folder Selection")
        folder_layout = QVBoxLayout(folder_group)
        
        folder_row = QHBoxLayout()
        self.folder_path_label = QLabel("No folder selected")
        self.folder_path_label.setStyleSheet("padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        self.folder_path_label.setFixedHeight(30)
        
        browse_button = QPushButton("Browse...")
        browse_button.setFixedWidth(100)
        # Use a try-except wrapper for the browse button click
        browse_button.clicked.connect(self.safe_select_folder)
        
        folder_row.addWidget(self.folder_path_label, 1)
        folder_row.addWidget(browse_button, 0)
        folder_layout.addLayout(folder_row)
        
        # Validation status
        self.status_label = QLabel("Please select a folder to begin")
        self.status_label.setStyleSheet("color: #666;")
        folder_layout.addWidget(self.status_label)
        
        layout.addWidget(folder_group)
        
        # CAM folders section
        cam_group = QGroupBox("Detected CAM Folders")
        cam_layout = QVBoxLayout(cam_group)
        
        self.cam_list = QListWidget()
        self.cam_list.setMinimumHeight(150)
        cam_layout.addWidget(self.cam_list)
        
        # Option to rename folders
        self.rename_checkbox = QCheckBox("Rename '01 VIDEO' folders to '01 VIDEO.old' (recommended)")
        self.rename_checkbox.setChecked(True)
        self.rename_checkbox.stateChanged.connect(self.toggle_rename_option)
        cam_layout.addWidget(self.rename_checkbox)
        
        layout.addWidget(cam_group)
        
        # Files section
        files_group = QGroupBox("Files to Process")
        files_layout = QVBoxLayout(files_group)
        
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(150)
        files_layout.addWidget(self.file_list)
        
        file_count_layout = QHBoxLayout()
        self.file_count_label = QLabel("0 files found")
        file_count_layout.addWidget(self.file_count_label)
        file_count_layout.addStretch()
        files_layout.addLayout(file_count_layout)
        
        layout.addWidget(files_group)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.addStretch()
        
        self.next_button = QPushButton("Next →")
        self.next_button.setFixedWidth(100)
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.add_to_queue)
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to their respective slots."""
        # Connections are handled in _init_ui
        pass
    
    def toggle_rename_option(self, state):
        """Toggle whether to rename 01 VIDEO folders."""
        self.rename_folders = bool(state)
        logger.info(f"Rename folders option set to: {self.rename_folders}")
    
    def safe_select_folder(self):
        """
        Wrapper for select_folder with additional error handling.
        """
        try:
            logger.info("Browse button clicked, calling select_folder")
            self.select_folder()
        except Exception as e:
            logger.error(f"Error in safe_select_folder: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while selecting a folder: {str(e)}"
            )
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
    
    def select_folder(self):
        """
        Open folder dialog for selecting a directory of video files.
        
        Scans directory recursively for valid video files.
        """
        try:
            logger.info("Opening folder selection dialog")
            
            # Use a try-except block specifically for the file dialog
            try:
                folder = QFileDialog.getExistingDirectory(
                    self,
                    "Select Wedding Footage Folder",
                    os.path.expanduser("~"),
                    QFileDialog.Option.ShowDirsOnly
                )
                logger.info(f"Folder selection dialog returned: {folder}")
            except Exception as e:
                logger.error(f"Error in file dialog: {str(e)}", exc_info=True)
                raise Exception(f"File dialog error: {str(e)}")
            
            if folder:
                self.parent_folder = folder
                self.folder_path_label.setText(folder)
                logger.info(f"Selected folder: {folder}")
                
                # Update status
                self.status_label.setText("Scanning for CAM folders...")
                self.status_label.setStyleSheet("color: #666;")
                
                # Clear previous data
                self.cam_list.clear()
                self.file_list.clear()
                self.cam_folders = []
                self.valid_files = []
                self.file_count_label.setText("0 files found")
                self.next_button.setEnabled(False)
                
                # Use worker to scan the folder in a background thread
                self.worker.set_folder(folder)
                
                # Create progress dialog
                self.progress_dialog = QProgressDialog("Scanning for video files...", "Cancel", 0, 100, self)
                self.progress_dialog.setWindowTitle("Scanning")
                self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                self.progress_dialog.setMinimumDuration(500)  # Only show for operations > 500ms
                self.progress_dialog.canceled.connect(self.worker.cancel)
                
                # Connect progress update signal
                self.worker.progress_update.connect(self.update_progress)
                
                # Start the worker (if not already running)
                if not self.worker_thread.isRunning():
                    self.worker_thread.start()
                else:
                    # Thread already running, just trigger scan_folder directly
                    QApplication.processEvents()  # Ensure UI updates
                    self.worker.scan_folder()
                
        except Exception as e:
            logger.error(f"Error in select_folder: {str(e)}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            raise  # Re-raise the exception to be caught by safe_select_folder
    
    def update_progress(self, current, total):
        """Update the progress dialog."""
        if self.progress_dialog is not None:
            progress_percent = int((current / max(1, total)) * 100)
            self.progress_dialog.setValue(progress_percent)
            QApplication.processEvents()  # Ensure UI updates
    
    def on_cam_folders_found(self, cam_folders):
        """Handle found CAM folders."""
        self.cam_folders = cam_folders
        self.cam_list.clear()
        
        for cam_folder in cam_folders:
            item = QListWidgetItem(os.path.basename(cam_folder))
            self.cam_list.addItem(item)
    
    def on_files_found(self, files):
        """Handle found video files."""
        self.valid_files = files
        self.file_list.clear()
        
        file_count = len(files)
        
        if file_count == 0:
            logger.warning("No valid files found during scan")
            self.status_update.emit("No valid video files found in the selected folders", "red")
            self.next_button.setEnabled(False)
            self.file_count_label.setText("0 files found")
            return
            
        # Add files to the list
        for file_path in files:
            item = QListWidgetItem(os.path.basename(file_path))
            self.file_list.addItem(item)
        
        self.file_count_label.setText(f"{file_count} files found")
        self.next_button.setEnabled(True)
        logger.info(f"Found {file_count} valid video files")
    
    def on_status_update(self, message, color):
        """Handle status updates."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def on_error(self, error_message):
        """Handle errors."""
        self.status_label.setText(error_message)
        self.status_label.setStyleSheet("color: red;")
    
    def on_task_completed(self):
        """Handle task completion."""
        # Close the progress dialog
        if self.progress_dialog is not None:
            self.progress_dialog.setValue(100)  # Ensure dialog shows 100% before closing
            self.progress_dialog.close()
            self.progress_dialog = None
    
    def validate_selections(self):
        """
        Validate all selected files to ensure they are compatible.
        
        Returns:
            bool: True if all files are valid, False otherwise
        """
        # Files have already been validated during scan
        return len(self.valid_files) > 0
    
    def add_to_queue(self):
        """
        Add validated files to the compression queue.
        
        Emits files_selected signal with list of files.
        """
        if not self.validate_selections():
            QMessageBox.warning(
                self,
                "Validation Error",
                "No valid video files selected. Please select a valid folder."
            )
            return
        
        # If rename option is selected, prompt user to confirm
        renamed = False
        if self.rename_folders:
            reply = QMessageBox.question(
                self,
                "Confirm Folder Rename",
                "This will rename '01 VIDEO' folders to '01 VIDEO.old'. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Rename video folders
                video_path = os.path.join(self.parent_folder, "03 MEDIA", "01 VIDEO")
                renamed_path = rename_video_folder(video_path)
                logger.info(f"Renamed video folder: {video_path} to {renamed_path}")
                renamed = True
        
        # If we renamed folders, update the file paths
        updated_files = []
        if renamed:
            for file_path in self.valid_files:
                if "/01 VIDEO/" in file_path:
                    updated_path = file_path.replace("/01 VIDEO/", "/01 VIDEO.old/")
                    if os.path.exists(updated_path):
                        logger.info(f"Updated path after rename: {file_path} -> {updated_path}")
                        updated_files.append(updated_path)
                    else:
                        # Still include the original path - the queue manager will handle it
                        logger.warning(f"Could not find updated path for: {file_path}")
                        updated_files.append(file_path)
                else:
                    updated_files.append(file_path)
            logger.info(f"Updated {len(updated_files)} file paths after renaming directory")
        else:
            updated_files = self.valid_files
        
        # Emit signal with validated files
        logger.info(f"Adding {len(updated_files)} files to queue")
        self.files_selected.emit(updated_files)
        
        # Emit signal to navigate to next panel
        self.next_clicked.emit()
    
    def closeEvent(self, event):
        """Handle the close event - clean up threads."""
        # Cancel any ongoing operations
        if hasattr(self, 'worker') and self.worker:
            self.worker.cancel()
        
        # Quit the worker thread properly
        if hasattr(self, 'worker_thread') and self.worker_thread:
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                if not self.worker_thread.wait(3000):  # Wait up to 3 seconds for thread to finish
                    self.worker_thread.terminate()
                    self.worker_thread.wait()
        
        super().closeEvent(event)