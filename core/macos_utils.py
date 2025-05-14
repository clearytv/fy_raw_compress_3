#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS Utilities Module

This module provides utility functions for interacting with macOS specific features,
such as setting Finder tags (labels).
"""

import subprocess
import logging
import platform

logger = logging.getLogger(__name__)

# Finder label color mapping (indexes used by AppleScript)
FINDER_LABEL_COLORS = {
    "None": 0,
    "Orange": 1,
    "Red": 2,
    "Yellow": 3,
    "Blue": 4,
    "Purple": 5,
    "Green": 6,
    "Gray": 7
}

def set_finder_label(folder_path: str, color_name: str) -> bool:
    """
    Sets the Finder label for a given folder path.

    Args:
        folder_path (str): The absolute path to the folder.
        color_name (str): The name of the color to set (e.g., "Orange", "Green").
                          Must be a key in FINDER_LABEL_COLORS.

    Returns:
        bool: True if the command was executed successfully, False otherwise.
    """
    if platform.system() != "Darwin":
        logger.warning("Finder labels can only be set on macOS. Skipping.")
        return False

    if color_name not in FINDER_LABEL_COLORS:
        logger.error(f"Invalid color name: {color_name}. Available colors: {list(FINDER_LABEL_COLORS.keys())}")
        return False

    color_index = FINDER_LABEL_COLORS[color_name]
    
    try:
        script = f'tell application "Finder"\nset p_file to (POSIX file "{folder_path}" as alias)\nset label index of p_file to {color_index}\nupdate p_file\nend tell'
        process = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, check=True)
        logger.info(f"Successfully set Finder label '{color_name}' for folder: {folder_path} (with update command)")
        if process.stderr:
            logger.warning(f"AppleScript stderr for setting label on {folder_path}: {process.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error setting Finder label for {folder_path} to {color_name}: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("osascript command not found. Ensure AppleScript execution is possible.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred while setting Finder label for {folder_path}: {str(e)}")
        return False

if __name__ == "__main__":
    # Example usage (for testing purposes)
    # Create a dummy folder for testing if it doesn't exist
    import os
    test_folder = os.path.join(os.path.expanduser("~"), "Desktop", "TestLabelFolder")
    if not os.path.exists(test_folder):
        os.makedirs(test_folder)
        print(f"Created test folder: {test_folder}")

    print(f"Attempting to set label 'Orange' for: {test_folder}")
    if set_finder_label(test_folder, "Orange"):
        print("Set to Orange. Check Finder.")
    else:
        print("Failed to set Orange label.")

    # input("Press Enter to change to Green...") # For manual check
    # print(f"Attempting to set label 'Green' for: {test_folder}")
    # if set_finder_label(test_folder, "Green"):
    #     print("Set to Green. Check Finder.")
    # else:
    #     print("Failed to set Green label.")

    # input("Press Enter to remove label...") # For manual check
    # print(f"Attempting to set label 'None' for: {test_folder}")
    # if set_finder_label(test_folder, "None"):
    #     print("Label removed. Check Finder.")
    # else:
    #     print("Failed to remove label.")
    
    # print(f"\nNote: You might need to manually clean up the test folder: {test_folder}")