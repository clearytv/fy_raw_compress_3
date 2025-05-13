#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for the browse button functionality in Forever Yours Raw Compress application.
This script simulates the workflow when the browse button is clicked.
"""

import os
import sys
import logging
import subprocess
from PyQt6.QtWidgets import QApplication, QFileDialog
from gui.step1_import import ImportPanel

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/test_browse_button.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockFileDialog:
    @staticmethod
    def getExistingDirectory(*args, **kwargs):
        """Mock implementation that returns a test directory path."""
        logger.info("Mock file dialog returning test directory")
        return os.path.abspath("test_directory")

def test_browse_button():
    """Test the browse button functionality with FFmpeg unavailable."""
    print("Testing browse button functionality with FFmpeg unavailable...")
    
    # Create a test directory structure
    os.makedirs("test_directory/03 MEDIA/01 VIDEO/CAM 1", exist_ok=True)
    
    # Create a test video file
    test_file = "test_directory/03 MEDIA/01 VIDEO/CAM 1/test_video.mp4"
    with open(test_file, "w") as f:
        f.write("Test file")
    
    # Create a mock subprocess.run function that raises FileNotFoundError for FFmpeg
    original_run = subprocess.run
    original_file_dialog = QFileDialog.getExistingDirectory
    
    def mock_run(*args, **kwargs):
        if args[0][0] == "ffmpeg":
            logger.info("Simulating FFmpeg not found")
            raise FileNotFoundError("Simulated FFmpeg not found")
        return original_run(*args, **kwargs)
    
    # Replace subprocess.run with our mock function
    subprocess.run = mock_run
    QFileDialog.getExistingDirectory = MockFileDialog.getExistingDirectory
    
    try:
        # Initialize Qt application
        app = QApplication(sys.argv)
        
        # Create import panel
        import_panel = ImportPanel()
        
        # Call select_folder method directly (simulating browse button click)
        logger.info("Calling select_folder method")
        import_panel.select_folder()
        
        # Check if the application crashed
        print("✅ Test PASSED: Application did not crash when browse button was clicked")
        logger.info("Test PASSED: Application did not crash when browse button was clicked")
        
    except Exception as e:
        print(f"❌ Test FAILED: Application crashed with error: {str(e)}")
        logger.error(f"Test FAILED: Application crashed with error: {str(e)}", exc_info=True)
    
    finally:
        # Restore original functions
        subprocess.run = original_run
        QFileDialog.getExistingDirectory = original_file_dialog
        
        # Clean up test directory
        import shutil
        if os.path.exists("test_directory"):
            shutil.rmtree("test_directory")

if __name__ == "__main__":
    test_browse_button()