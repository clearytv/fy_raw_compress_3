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
    QProgressDialog, QApplication, QProgressBar
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QObject, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QIcon

# Import core functionality
from core.file_preparation import scan_directory, validate_video_file, find_cam_folders, rename_video_folder, copy_non_cam_folders

logger = logging.getLogger(__name__)


# No need for ScanWorker class as we're handling folder scanning synchronously now


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
        
        # Progress section - initially hidden
        progress_group = QGroupBox("Copy Progress")
        progress_group.setVisible(False)  # Hide initially
        self.progress_group = progress_group
        progress_layout = QVBoxLayout(progress_group)
        
        # Progress bar
        self.copy_progress_bar = QProgressBar()
        progress_bar_style = """
        QProgressBar {
            border: 1px solid #bbb;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4a86e8;
        }
        """
        self.copy_progress_bar.setStyleSheet(progress_bar_style)
        progress_layout.addWidget(self.copy_progress_bar)
        
        # Status label
        self.copy_status_label = QLabel("Ready")
        progress_layout.addWidget(self.copy_status_label)
        
        layout.addWidget(progress_group)
        
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
                
                # Clear previous data
                self.cam_list.clear()
                self.file_list.clear()
                self.cam_folders = []
                self.valid_files = []
                self.file_count_label.setText("0 files found")
                
                # Direct path to the expected video location (standard wedding folder structure)
                media_path = os.path.join(folder, "03 MEDIA")
                video_path = os.path.join(media_path, "01 VIDEO")
                
                # Validate the standard structure
                if not os.path.exists(media_path):
                    self.status_label.setText("'03 MEDIA' folder not found")
                    self.status_label.setStyleSheet("color: red;")
                    return
                    
                if not os.path.exists(video_path):
                    self.status_label.setText("'01 VIDEO' folder not found in '03 MEDIA'")
                    self.status_label.setStyleSheet("color: red;")
                    return
                
                # Find CAM folders directly without scanning
                cam_folders = []
                try:
                    for item in os.listdir(video_path):
                        item_path = os.path.join(video_path, item)
                        if os.path.isdir(item_path) and "CAM" in item.upper():
                            cam_folders.append(item_path)
                except Exception as e:
                    self.status_label.setText(f"Error accessing folders: {str(e)}")
                    self.status_label.setStyleSheet("color: red;")
                    logger.error(f"Error listing CAM folders: {str(e)}")
                    return
                
                self.cam_folders = cam_folders
                
                # Update CAM folders list
                self.cam_list.clear()
                for cam_folder in cam_folders:
                    item = QListWidgetItem(os.path.basename(cam_folder))
                    self.cam_list.addItem(item)
                
                # Get valid video files directly from CAM folders
                valid_files = []
                for cam_folder in cam_folders:
                    try:
                        for file_name in os.listdir(cam_folder):
                            file_path = os.path.join(cam_folder, file_name)
                            if os.path.isfile(file_path):
                                _, ext = os.path.splitext(file_path)
                                if ext.lower() in ['.mov', '.mp4']:
                                    valid_files.append(file_path)
                    except Exception as e:
                        logger.error(f"Error scanning CAM folder {cam_folder}: {str(e)}")
                
                self.valid_files = valid_files
                
                # Update file list
                self.file_list.clear()
                for file_path in valid_files:
                    item = QListWidgetItem(os.path.basename(file_path))
                    self.file_list.addItem(item)
                
                file_count = len(valid_files)
                self.file_count_label.setText(f"{file_count} files found")
                
                # Update status
                if file_count > 0:
                    self.status_label.setText(f"Found {len(cam_folders)} CAM folders with {file_count} video files")
                    self.status_label.setStyleSheet("color: green;")
                    self.next_button.setEnabled(True)
                else:
                    self.status_label.setText("No valid video files found")
                    self.status_label.setStyleSheet("color: orange;")
                    self.next_button.setEnabled(False)
                
                logger.info(f"Found {len(cam_folders)} CAM folders with {file_count} video files")
                
        except Exception as e:
            logger.error(f"Error in select_folder: {str(e)}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            raise  # Re-raise the exception to be caught by safe_select_folder
    
    # All worker-related methods have been removed as we now handle folder scanning synchronously
    
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
        
        # If rename option is selected, rename the folder without confirmation
        renamed = False
        if self.rename_folders:
            # Rename video folders
            video_path = os.path.join(self.parent_folder, "03 MEDIA", "01 VIDEO")
            renamed_path = rename_video_folder(video_path)
            logger.info(f"Renamed video folder: {video_path} to {renamed_path}")
            
            if renamed_path != video_path:  # If the folder was renamed successfully
                renamed = True
                
                # Create the new '01 VIDEO' directory
                os.makedirs(video_path, exist_ok=True)
                
                # Show progress section
                self.progress_group.setVisible(True)
                self.copy_progress_bar.setValue(0)
                self.copy_status_label.setText("Preparing to copy folders...")
                self.next_button.setEnabled(False)  # Disable next button during copy
                QApplication.processEvents()  # Ensure UI updates
                
                # Progress callback for folder copying
                def update_copy_progress(percent, message):
                    self.copy_progress_bar.setValue(int(percent))
                    self.copy_status_label.setText(message)
                    QApplication.processEvents()  # Ensure UI updates
                
                # Copy contents of non-CAM subfolders from '01 VIDEO.old' to '01 VIDEO'
                copied = copy_non_cam_folders(renamed_path, video_path, update_copy_progress)
                logger.info(f"Copied {copied} non-CAM folders from {renamed_path} to {video_path}")
                
                # Update progress to show completion
                self.copy_progress_bar.setValue(100)
                self.copy_status_label.setText(f"Completed copying {copied} folders")
                QApplication.processEvents()  # Ensure UI updates
                
                # Re-enable next button
                self.next_button.setEnabled(True)
        
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
        
        # Hide the progress bar after completion (if it was shown)
        if self.progress_group.isVisible():
            # Keep it visible for a moment so the user can see it completed
            QTimer.singleShot(1500, lambda: self.progress_group.setVisible(False))
        
        # Emit signal to navigate to next panel
        self.next_clicked.emit()
    
    def closeEvent(self, event):
        """Handle the close event."""
        # No worker threads to clean up
        super().closeEvent(event)
        
    def reset_panel(self):
        """Reset the panel to initial state when starting a new job."""
        logger.info("Resetting import panel state")
        
        # Clear stored data
        self.parent_folder = ""
        self.cam_folders = []
        self.valid_files = []
        
        # Reset UI elements
        self.folder_path_label.setText("No folder selected")
        self.status_label.setText("Please select a folder to begin")
        self.status_label.setStyleSheet("color: #666;")
        self.cam_list.clear()
        self.file_list.clear()
        self.file_count_label.setText("0 files found")
        self.next_button.setEnabled(False)
        
        # Hide progress section if visible
        self.progress_group.setVisible(False)

# Add a check to prevent direct execution
if __name__ == "__main__":
    print("\nError: This file is part of the Forever Yours Compression Tool and should not be run directly.")
    print("Please run the application using the main.py file in the root directory:")
    print("  python main.py\n")