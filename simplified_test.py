#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified test application for Forever Yours Raw Compress.
This application focuses only on the browse button functionality to isolate the issue.
"""

import os
import sys
import logging
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/simplified_test.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimplifiedApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg Availability Test")
        self.resize(600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add status label
        self.status_label = QLabel("Click the Browse button to select a folder")
        layout.addWidget(self.status_label)
        
        # Add folder path label
        self.folder_path_label = QLabel("No folder selected")
        self.folder_path_label.setStyleSheet("padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        layout.addWidget(self.folder_path_label)
        
        # Add browse button
        button_layout = QHBoxLayout()
        browse_button = QPushButton("Browse...")
        browse_button.setFixedWidth(100)
        browse_button.clicked.connect(self.safe_select_folder)
        button_layout.addWidget(browse_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Add FFmpeg simulation button
        ffmpeg_button = QPushButton("Simulate FFmpeg Not Available")
        ffmpeg_button.clicked.connect(self.simulate_ffmpeg_not_available)
        layout.addWidget(ffmpeg_button)
        
        # FFmpeg availability status
        self.ffmpeg_status = True
        self.ffmpeg_status_label = QLabel("FFmpeg Status: Available")
        layout.addWidget(self.ffmpeg_status_label)
        
        layout.addStretch()
    
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
    
    def select_folder(self):
        """
        Open folder dialog for selecting a directory.
        """
        try:
            logger.info("Opening folder selection dialog")
            
            folder = QFileDialog.getExistingDirectory(
                self, 
                "Select Folder",
                os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly
            )
            
            logger.info(f"Folder selection dialog returned: {folder}")
            
            if folder:
                self.folder_path_label.setText(folder)
                logger.info(f"Selected folder: {folder}")
                
                # Update status
                self.status_label.setText("Validating folder...")
                
                # Validate the folder
                self.validate_folder(folder)
        except Exception as e:
            logger.error(f"Error in select_folder: {str(e)}", exc_info=True)
            raise
    
    def validate_folder(self, folder_path):
        """
        Validate the selected folder by checking for video files.
        """
        try:
            logger.info(f"Validating folder: {folder_path}")
            
            # Check if folder exists
            if not os.path.exists(folder_path):
                logger.error(f"Folder does not exist: {folder_path}")
                self.status_label.setText("Error: Folder does not exist")
                return
            
            # Check for video files
            video_files = []
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.mp4', '.mov')):
                        file_path = os.path.join(root, file)
                        try:
                            # Check if FFmpeg is available
                            self.validate_video_file(file_path)
                            video_files.append(file_path)
                        except Exception as e:
                            logger.error(f"Error validating file {file_path}: {str(e)}", exc_info=True)
            
            # Update status
            if video_files:
                self.status_label.setText(f"Found {len(video_files)} valid video files")
            else:
                self.status_label.setText("No valid video files found")
                
            logger.info(f"Found {len(video_files)} valid video files")
        except Exception as e:
            logger.error(f"Error validating folder: {str(e)}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            raise
    
    def validate_video_file(self, file_path):
        """
        Validate a video file using FFmpeg.
        """
        try:
            logger.info(f"Validating video file: {file_path}")
            
            # Check if FFmpeg is available
            if not self.ffmpeg_status:
                logger.error("FFmpeg not available (simulated)")
                return True
            
            # Use FFmpeg to validate the file
            try:
                subprocess.run(["ffmpeg", "-v", "error", "-i", file_path, "-f", "null", "-"], 
                              check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError as e:
                logger.warning(f"FFmpeg validation failed: {str(e)}")
                return False
            except FileNotFoundError:
                logger.error("FFmpeg not found")
                return True
        except Exception as e:
            logger.error(f"Error in validate_video_file: {str(e)}", exc_info=True)
            return False
    
    def simulate_ffmpeg_not_available(self):
        """
        Simulate FFmpeg not being available.
        """
        self.ffmpeg_status = not self.ffmpeg_status
        status_text = "Available" if self.ffmpeg_status else "Not Available"
        self.ffmpeg_status_label.setText(f"FFmpeg Status: {status_text}")
        logger.info(f"FFmpeg availability set to: {self.ffmpeg_status}")
        
        if not self.ffmpeg_status:
            QMessageBox.information(
                self,
                "FFmpeg Simulation",
                "FFmpeg is now simulated as not available. Try using the Browse button."
            )

def main():
    """
    Initialize and run the application.
    """
    try:
        logger.info("Starting simplified test application")
        
        # Initialize application
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = SimplifiedApp()
        window.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()