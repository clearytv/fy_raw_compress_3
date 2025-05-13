#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal test of PyQt6 file dialog functionality.
This application only tests the file dialog without any FFmpeg validation.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QLabel, QFileDialog

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/minimal_dialog.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MinimalDialog(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Dialog Test")
        self.resize(400, 200)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add status label
        self.status_label = QLabel("Click the button to test file dialog")
        layout.addWidget(self.status_label)
        
        # Add browse button
        self.browse_button = QPushButton("Test Directory Dialog")
        self.browse_button.clicked.connect(self.test_directory_dialog)
        layout.addWidget(self.browse_button)
        
        # Add file button
        self.file_button = QPushButton("Test File Dialog")
        self.file_button.clicked.connect(self.test_file_dialog)
        layout.addWidget(self.file_button)
        
        layout.addStretch()
    
    def test_directory_dialog(self):
        """
        Test the directory selection dialog.
        """
        try:
            logger.info("Testing directory selection dialog")
            self.status_label.setText("Opening directory dialog...")
            
            # Use a different directory dialog method
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select Directory",
                os.path.expanduser("~")
            )
            
            logger.info(f"Directory dialog returned: {folder}")
            self.status_label.setText(f"Selected directory: {folder or 'None'}")
            
        except Exception as e:
            logger.error(f"Error in directory dialog: {str(e)}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
    
    def test_file_dialog(self):
        """
        Test the file selection dialog.
        """
        try:
            logger.info("Testing file selection dialog")
            self.status_label.setText("Opening file dialog...")
            
            # Try a different file dialog method
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select File",
                os.path.expanduser("~"),
                "All Files (*)"
            )
            
            logger.info(f"File dialog returned: {file_path}")
            self.status_label.setText(f"Selected file: {file_path or 'None'}")
            
        except Exception as e:
            logger.error(f"Error in file dialog: {str(e)}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")

def main():
    """
    Initialize and run the application.
    """
    try:
        logger.info("Starting minimal dialog test application")
        
        # Initialize application
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = MinimalDialog()
        window.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()