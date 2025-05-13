#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the threading fix in Forever Yours Raw Compress application.
This script verifies that file operations are properly moved to a background thread.
"""

import os
import sys
import logging
import subprocess
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QWidget
from gui.step1_import import ImportPanel

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/test_threading_fix.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestWindow(QMainWindow):
    """Test window to host the import panel and monitor UI responsiveness."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Threading Fix Test")
        self.setGeometry(100, 100, 800, 800)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add status label
        self.status_label = QLabel("Testing threading fix...")
        layout.addWidget(self.status_label)
        
        # Add UI responsiveness test button
        self.test_button = QPushButton("Test UI Responsiveness")
        self.test_button.clicked.connect(self.update_ui)
        layout.addWidget(self.test_button)
        
        # Create test counter label to verify UI is responsive
        self.counter_label = QLabel("UI Counter: 0")
        layout.addWidget(self.counter_label)
        self.counter = 0
        
        # Add the import panel
        self.import_panel = ImportPanel(self)  # Pass self as parent
        layout.addWidget(self.import_panel)
        
        # Log status
        logger.info("Test window initialized")
        self.status_label.setText("Click 'Browse...' to select a folder and test threading")
    
    def update_ui(self):
        """Update the counter to demonstrate UI responsiveness."""
        self.counter += 1
        self.counter_label.setText(f"UI Counter: {self.counter}")
        logger.info(f"UI updated. Counter: {self.counter}")
        self.status_label.setText("UI thread is responsive!")

def create_test_directory():
    """Create a test directory structure with video files."""
    logger.info("Creating test directory structure")
    
    # Create directory structure
    os.makedirs("test_directory/03 MEDIA/01 VIDEO/CAM 1", exist_ok=True)
    os.makedirs("test_directory/03 MEDIA/01 VIDEO/CAM 2", exist_ok=True)
    os.makedirs("test_directory/03 MEDIA/01 VIDEO/CAM 3", exist_ok=True)
    
    # Create test video files (empty files with video extensions)
    for i in range(10):
        with open(f"test_directory/03 MEDIA/01 VIDEO/CAM 1/video_{i}.mp4", "w") as f:
            f.write("Test MP4 file")
        with open(f"test_directory/03 MEDIA/01 VIDEO/CAM 2/video_{i}.mov", "w") as f:
            f.write("Test MOV file")
        with open(f"test_directory/03 MEDIA/01 VIDEO/CAM 3/video_{i}.mp4", "w") as f:
            f.write("Test MP4 file")
    
    logger.info("Test directory structure created")
    return os.path.abspath("test_directory")

def cleanup_test_directory():
    """Clean up the test directory."""
    import shutil
    if os.path.exists("test_directory"):
        shutil.rmtree("test_directory")
        logger.info("Test directory removed")

def main():
    """Run the threading fix test."""
    try:
        logger.info("Starting threading fix test")
        
        # Create test data
        test_dir = create_test_directory()
        logger.info(f"Test directory created at: {test_dir}")
        
        # Initialize Qt application
        app = QApplication(sys.argv)
        
        # Create test window
        window = TestWindow()
        window.show()
        
        # Run the application
        exit_code = app.exec()
        
        # Clean up
        cleanup_test_directory()
        
        # Exit with the appropriate code
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Test error: {str(e)}", exc_info=True)
        cleanup_test_directory()
        raise

if __name__ == "__main__":
    main()