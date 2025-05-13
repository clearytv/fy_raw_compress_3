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
    QFrame, QCheckBox, QMessageBox, QSplitter, QGroupBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QIcon

# Import core functionality
from core.file_preparation import scan_directory, validate_video_file, find_cam_folders, rename_video_folder

logger = logging.getLogger(__name__)


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
        browse_button.clicked.connect(self.select_folder)
        
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
    
    def select_folder(self):
        """
        Open folder dialog for selecting a directory of video files.
        
        Scans directory recursively for valid video files.
        """
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Select Wedding Footage Folder",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.parent_folder = folder
            self.folder_path_label.setText(folder)
            logger.info(f"Selected folder: {folder}")
            
            # Update status
            self.status_label.setText("Scanning for CAM folders...")
            self.status_label.setStyleSheet("color: #666;")
            
            # Find parent folder containing "03 MEDIA/01 VIDEO" structure
            self._find_cam_folders()
    
    def _find_cam_folders(self):
        """Find CAM folders within the selected parent folder."""
        # Check for "03 MEDIA/01 VIDEO" structure
        media_path = os.path.join(self.parent_folder, "03 MEDIA")
        video_path = os.path.join(media_path, "01 VIDEO")
        
        if not os.path.exists(media_path):
            self.status_label.setText("Error: '03 MEDIA' folder not found")
            self.status_label.setStyleSheet("color: red;")
            return
            
        if not os.path.exists(video_path):
            self.status_label.setText("Error: '01 VIDEO' folder not found in '03 MEDIA'")
            self.status_label.setStyleSheet("color: red;")
            return
            
        # Find CAM folders
        self.cam_folders = find_cam_folders(video_path)
        
        # Update CAM folders list
        self.cam_list.clear()
        if self.cam_folders:
            for cam_folder in self.cam_folders:
                item = QListWidgetItem(os.path.basename(cam_folder))
                self.cam_list.addItem(item)
                
            self.status_label.setText(f"Found {len(self.cam_folders)} CAM folders")
            self.status_label.setStyleSheet("color: green;")
            
            # Scan for video files
            self._scan_for_video_files()
        else:
            self.status_label.setText("No CAM folders found in '01 VIDEO'")
            self.status_label.setStyleSheet("color: orange;")
    
    def _scan_for_video_files(self):
        """Scan CAM folders for valid video files."""
        self.valid_files = []
        self.file_list.clear()
        
        for cam_folder in self.cam_folders:
            files = scan_directory(cam_folder)
            self.valid_files.extend(files)
        
        # Update file list
        for file_path in self.valid_files:
            item = QListWidgetItem(os.path.basename(file_path))
            self.file_list.addItem(item)
        
        # Update file count and enable Next button if files found
        file_count = len(self.valid_files)
        self.file_count_label.setText(f"{file_count} files found")
        
        if file_count > 0:
            self.next_button.setEnabled(True)
        else:
            self.next_button.setEnabled(False)
    
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
        
        # Emit signal with validated files
        logger.info(f"Adding {len(self.valid_files)} files to queue")
        self.files_selected.emit(self.valid_files)
        
        # Emit signal to navigate to next panel
        self.next_clicked.emit()