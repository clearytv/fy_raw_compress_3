#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify recent changes in the video compression project:
1. Testing the file sorting logic
2. Confirming that output filenames no longer include "_24mbps"
"""

import os
import re
from core.file_preparation import generate_output_filename

def test_file_sorting_logic():
    """
    Test the file sorting logic with sample filenames to ensure they're ordered correctly.
    This replicates the logic from queue_manager.py's add_files method.
    """
    print("=== Testing File Sorting Logic ===")
    
    # Sample file paths
    test_files = [
        "/path/to/CAM 2_005.mov",
        "/path/to/CAM 1_002.mov",
        "/path/to/CAM 1_001.mov",
        "/path/to/CAM 2_002.mov"
    ]
    
    print("Original file order:")
    for i, file in enumerate(test_files):
        print(f"{i+1}. {os.path.basename(file)}")
    
    # Extract camera number and file number from filenames (replicating the logic in queue_manager.py)
    def extract_file_info(path):
        """
        Extract camera number and file number from file path.
        Returns a tuple of (camera_number, file_number, path)
        """
        filename = os.path.basename(path)
        
        # Extract CAM number (e.g., CAM 1, CAM 2, etc.)
        cam_match = re.search(r'CAM\s*(\d+)', filename, re.IGNORECASE)
        cam_number = int(cam_match.group(1)) if cam_match else 999  # Default to high number if no match
        
        # Extract file number (e.g., 001, 002, etc.)
        file_match = re.search(r'(\d{3,})', filename)  # Match 3 or more digits
        file_number = int(file_match.group(1)) if file_match else 999999  # Default to high number if no match
        
        return (cam_number, file_number, path)
    
    # Sort files based on extracted information
    sorted_files = sorted([extract_file_info(path) for path in test_files])
    sorted_paths = [path for _, _, path in sorted_files]
    
    print("\nSorted file order:")
    for i, file in enumerate(sorted_paths):
        print(f"{i+1}. {os.path.basename(file)}")
    
    # Expected order: CAM 1_001, CAM 1_002, CAM 2_002, CAM 2_005
    expected_order = [
        "/path/to/CAM 1_001.mov",
        "/path/to/CAM 1_002.mov",
        "/path/to/CAM 2_002.mov",
        "/path/to/CAM 2_005.mov"
    ]
    
    if sorted_paths == expected_order:
        print("\n✅ File sorting logic is working correctly!")
    else:
        print("\n❌ File sorting logic is not working as expected!")
        print("Expected order:")
        for i, file in enumerate(expected_order):
            print(f"{i+1}. {os.path.basename(file)}")

def test_output_filename_generation():
    """
    Test that the output filename generation no longer adds "_24mbps" to filenames.
    """
    print("\n=== Testing Output Filename Generation ===")
    
    # Test cases
    test_cases = [
        "/path/to/CAM 1_001.mov",
        "/path/to/video_file.mp4",
        "/path/to/sample recording.mov"
    ]
    
    for input_path in test_cases:
        output_path = generate_output_filename(input_path)
        input_basename = os.path.basename(input_path)
        output_basename = os.path.basename(output_path)
        name, _ = os.path.splitext(input_basename)
        
        print(f"Input:  {input_basename}")
        print(f"Output: {output_basename}")
        
        # Check if "_24mbps" was added to the filename
        if "_24mbps" in output_basename and "_24mbps" not in input_basename:
            print(f"❌ Output filename still contains '_24mbps'!")
        else:
            print(f"✅ Output filename does not add '_24mbps'")
        print()

if __name__ == "__main__":
    test_file_sorting_logic()
    test_output_filename_generation()