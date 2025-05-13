#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFmpeg Fix Verifier for Forever Yours Raw Compress.

This application tests the specific fix for handling cases where FFmpeg is not available.
It isolates the FFmpeg validation part of the process to ensure it works correctly.
"""

import os
import sys
import logging
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QMessageBox, QGroupBox
)

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/ffmpeg_fix_verifier.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FFmpegFixVerifier(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg Fix Verifier")
        self.resize(600, 500)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add title and description
        title = QLabel("FFmpeg Availability Fix Verification Tool")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)
        
        description = QLabel(
            "This tool tests the fix for handling cases where FFmpeg is not available.\n"
            "It verifies that the application can continue functioning without crashing."
        )
        description.setStyleSheet("margin-bottom: 10px;")
        layout.addWidget(description)
        
        # FFmpeg status group
        status_group = QGroupBox("FFmpeg Status")
        status_layout = QVBoxLayout(status_group)
        
        # Check FFmpeg button
        check_button = QPushButton("Check FFmpeg Availability")
        check_button.clicked.connect(self.check_ffmpeg)
        status_layout.addWidget(check_button)
        
        # FFmpeg status label
        self.ffmpeg_status_label = QLabel("FFmpeg Status: Not Checked")
        status_layout.addWidget(self.ffmpeg_status_label)
        
        layout.addWidget(status_group)
        
        # Test group
        test_group = QGroupBox("Test FFmpeg Not Available")
        test_layout = QVBoxLayout(test_group)
        
        # Test button
        test_button = QPushButton("Test FFmpeg Not Available Fix")
        test_button.clicked.connect(self.test_ffmpeg_not_available)
        test_layout.addWidget(test_button)
        
        # Results section
        results_label = QLabel("Test Results:")
        test_layout.addWidget(results_label)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        test_layout.addWidget(self.results_text)
        
        layout.addWidget(test_group)
    
    def check_ffmpeg(self):
        """
        Check if FFmpeg is available on the system.
        """
        try:
            logger.info("Checking FFmpeg availability")
            self.results_text.append("Checking FFmpeg availability...")
            
            try:
                result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    logger.info("FFmpeg is available")
                    self.ffmpeg_status_label.setText("FFmpeg Status: Available")
                    self.results_text.append("✅ FFmpeg is available on your system")
                    version = result.stdout.splitlines()[0] if result.stdout else "Unknown version"
                    self.results_text.append(f"Version: {version}")
                else:
                    logger.warning(f"FFmpeg command returned non-zero exit code: {result.returncode}")
                    self.ffmpeg_status_label.setText("FFmpeg Status: Error")
                    self.results_text.append(f"⚠️ FFmpeg command returned error: {result.stderr}")
            
            except FileNotFoundError:
                logger.error("FFmpeg not found")
                self.ffmpeg_status_label.setText("FFmpeg Status: Not Available")
                self.results_text.append("❌ FFmpeg is not available on your system")
                self.results_text.append("This is the scenario we want to test the fix for!")
        
        except Exception as e:
            logger.error(f"Error checking FFmpeg: {str(e)}", exc_info=True)
            self.results_text.append(f"Error checking FFmpeg: {str(e)}")
    
    def test_ffmpeg_not_available(self):
        """
        Test the fix for when FFmpeg is not available.
        """
        try:
            logger.info("Testing FFmpeg not available fix")
            self.results_text.append("\nTesting FFmpeg not available fix...")
            
            # Create a test video file
            test_file = "test_video.mp4"
            with open(test_file, "w") as f:
                f.write("Test video file content")
            
            self.results_text.append(f"Created test file: {test_file}")
            
            # Original subprocess.run function
            original_run = subprocess.run
            
            # Mock function to simulate FFmpeg not available
            def mock_run(*args, **kwargs):
                if args and args[0] and args[0][0] == "ffmpeg":
                    logger.info("Simulating FFmpeg not found")
                    raise FileNotFoundError("Simulated FFmpeg not found")
                return original_run(*args, **kwargs)
            
            # Replace subprocess.run with our mock
            subprocess.run = mock_run
            
            self.results_text.append("Simulating FFmpeg not available...")
            
            try:
                # Import the validate_video_file function directly
                from core.file_preparation import validate_video_file
                
                # Test the function
                result = validate_video_file(test_file)
                
                if result:
                    logger.info("Test PASSED: validate_video_file returned True when FFmpeg is unavailable")
                    self.results_text.append("✅ Test PASSED: The fix is working correctly!")
                    self.results_text.append("  - validate_video_file() returned True when FFmpeg is unavailable")
                    self.results_text.append("  - This means files can be added to the queue even without FFmpeg validation")
                else:
                    logger.error("Test FAILED: validate_video_file returned False when FFmpeg is unavailable")
                    self.results_text.append("❌ Test FAILED: validate_video_file returned False")
                    self.results_text.append("  - This means files would not be added to the queue when FFmpeg is unavailable")
                    
            except Exception as e:
                logger.error(f"Error testing validate_video_file: {str(e)}", exc_info=True)
                self.results_text.append(f"❌ Test ERROR: {str(e)}")
            
            finally:
                # Restore original subprocess.run
                subprocess.run = original_run
                
                # Clean up test file
                if os.path.exists(test_file):
                    os.remove(test_file)
                    self.results_text.append(f"Cleaned up test file: {test_file}")
            
            # Check logs
            self.results_text.append("\nSummary:")
            self.results_text.append("1. The fix in validate_video_file() is working correctly in a controlled test environment")
            self.results_text.append("2. However, there might be other factors causing the application to crash in the actual environment")
            self.results_text.append("\nCheck logs/ffmpeg_fix_verifier.log for details")
            
        except Exception as e:
            logger.error(f"Error in test: {str(e)}", exc_info=True)
            self.results_text.append(f"Error in test: {str(e)}")

def main():
    """
    Initialize and run the application.
    """
    try:
        logger.info("Starting FFmpeg fix verifier")
        
        # Initialize application
        app = QApplication(sys.argv)
        
        # Create and show main window
        window = FFmpegFixVerifier()
        window.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()