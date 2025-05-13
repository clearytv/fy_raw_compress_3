#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for FFmpeg availability fix in Forever Yours Raw Compress application.
This script simulates FFmpeg being unavailable and tests the validate_video_file function.
"""

import os
import sys
import logging
import subprocess
from core.file_preparation import validate_video_file

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/test_ffmpeg.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_validate_video_file():
    """Test the validate_video_file function with FFmpeg unavailable."""
    print("Testing validate_video_file function with FFmpeg unavailable...")
    
    # Create a mock subprocess.run function that raises FileNotFoundError
    original_run = subprocess.run
    
    def mock_run(*args, **kwargs):
        if args[0][0] == "ffmpeg":
            logger.info("Simulating FFmpeg not found")
            raise FileNotFoundError("Simulated FFmpeg not found")
        return original_run(*args, **kwargs)
    
    # Replace subprocess.run with our mock function
    subprocess.run = mock_run
    
    try:
        # Create a test file
        test_file = "test_video.mp4"
        with open(test_file, "w") as f:
            f.write("Test file")
        
        # Test the function
        result = validate_video_file(test_file)
        
        # Check the result
        if result:
            print("✅ Test PASSED: validate_video_file returned True when FFmpeg is unavailable")
            logger.info("Test PASSED: validate_video_file returned True when FFmpeg is unavailable")
        else:
            print("❌ Test FAILED: validate_video_file returned False when FFmpeg is unavailable")
            logger.error("Test FAILED: validate_video_file returned False when FFmpeg is unavailable")
    
    except Exception as e:
        print(f"❌ Test ERROR: {str(e)}")
        logger.error(f"Test ERROR: {str(e)}", exc_info=True)
    
    finally:
        # Restore original subprocess.run
        subprocess.run = original_run
        
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    test_validate_video_file()