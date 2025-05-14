#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verification Panel Module

This module handles the verification step after media conversion:
- Displaying verification results for each file.
- Conditionally deleting the original media folder if all files match.
- Updating the main project folder icon based on verification and deletion success.
"""

import os
import shutil
import logging
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QGroupBox, QTextEdit, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

# Import core functionality
from core.verification_utils import verify_media_conversions
from core.macos_utils import set_finder_label # Assuming remove_folder_label is handled by set_finder_label(path, "None")

logger = logging.getLogger(__name__)

class VerifyPanel(QWidget):
    """
    Panel for displaying verification results and handling post-verification actions.
    """
    back_clicked = pyqtSignal()
    next_clicked = pyqtSignal() # Or finish_clicked if this is the last relevant step for this flow

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("Initializing verification panel")

        self.main_project_folder_path = ""
        self.original_media_folder_path = "" # e.g., ".../01 VIDEO.old"
        self.converted_media_folder_path = "" # e.g., ".../02 VIDEO"
        self.verification_results = []
        self.all_files_matched = False

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Set up the user interface components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Step 2.5: Verify Conversions")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Verification Results Group
        results_group = QGroupBox("Verification Details")
        results_layout = QVBoxLayout(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Original File", "Converted File", "Status", "Details"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setMinimumHeight(200)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Read-only
        results_layout.addWidget(self.results_table)
        layout.addWidget(results_group)

        # Overall Status and Actions Group
        status_actions_group = QGroupBox("Summary & Actions")
        status_actions_layout = QVBoxLayout(status_actions_group)

        self.overall_status_label = QLabel("Verification pending...")
        status_actions_layout.addWidget(self.overall_status_label)

        self.deletion_status_label = QLabel("") # For "01 VIDEO.old deletion status"
        status_actions_layout.addWidget(self.deletion_status_label)

        self.icon_update_status_label = QLabel("") # For "Icon update status"
        status_actions_layout.addWidget(self.icon_update_status_label)

        layout.addWidget(status_actions_group)

        # Log output (optional, for detailed messages)
        self.log_output_checkbox = QPushButton("Show Detailed Log") # Placeholder, could be QCheckBox
        self.log_output_checkbox.setCheckable(True)
        self.log_output_checkbox.setChecked(False)
        self.log_output_checkbox.clicked.connect(self._toggle_log_visibility)
        # layout.addWidget(self.log_output_checkbox) # Add if implementing log view

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setVisible(False) # Initially hidden
        # layout.addWidget(self.log_output) # Add if implementing log view


        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back to Convert")
        self.back_button.setFixedWidth(150)

        self.run_verification_button = QPushButton("Run Verification") # Initially visible
        self.run_verification_button.setFixedWidth(150)


        self.next_button = QPushButton("Next →") # Or "Finish"
        self.next_button.setFixedWidth(150)
        self.next_button.setEnabled(False) # Enabled after verification

        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.run_verification_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)
        layout.addLayout(nav_layout)

        self.setLayout(layout)

    def _connect_signals(self):
        """Connect UI signals to their respective slots."""
        self.back_button.clicked.connect(self.back_clicked.emit)
        self.next_button.clicked.connect(self.next_clicked.emit)
        self.run_verification_button.clicked.connect(self.process_verification)


    def _toggle_log_visibility(self):
        self.log_output.setVisible(self.log_output_checkbox.isChecked())

    def set_paths(self, main_project_path, original_media_path, converted_media_path):
        """Set the necessary paths for verification."""
        self.main_project_folder_path = main_project_path
        self.original_media_folder_path = original_media_path
        self.converted_media_folder_path = converted_media_path
        logger.info(f"Verification paths set: Main='{main_project_path}', Orig='{original_media_path}', Conv='{converted_media_path}'")
        # Reset UI for new paths
        self.reset_panel_state()

    def reset_panel_state(self):
        """Resets the panel to its initial state for new data."""
        self.results_table.setRowCount(0)
        self.overall_status_label.setText("Verification pending...")
        self.deletion_status_label.setText("")
        self.icon_update_status_label.setText("")
        self.log_output.clear()
        self.next_button.setEnabled(False)
        self.run_verification_button.setEnabled(True)
        self.all_files_matched = False


    def process_verification(self):
        """Initiates the verification process and updates the UI."""
        if not self.original_media_folder_path or not self.converted_media_folder_path:
            QMessageBox.warning(self, "Path Error", "Required folder paths are not set.")
            logger.warning("Verification cannot run: paths not set.")
            self.overall_status_label.setText("Error: Folder paths not configured.")
            return

        self.run_verification_button.setEnabled(False)
        self.overall_status_label.setText("Verification in progress...")
        logger.info("Starting media verification process.")

        try:
            self.verification_results = verify_media_conversions(
                self.original_media_folder_path,
                self.converted_media_folder_path
            )
        except Exception as e:
            logger.error(f"Critical error during verify_media_conversions call: {e}", exc_info=True)
            QMessageBox.critical(self, "Verification Error", f"An unexpected error occurred: {e}")
            self.overall_status_label.setText("Verification failed with an error.")
            self.run_verification_button.setEnabled(True) # Allow retry
            return

        self._populate_results_table()
        self._check_overall_status_and_proceed()
        self.next_button.setEnabled(True) # Enable next step regardless of outcome for now, user can review

    def _populate_results_table(self):
        """Fills the table with verification results."""
        self.results_table.setRowCount(0) # Clear previous results
        if not self.verification_results:
            self.overall_status_label.setText("No verification results returned.")
            logger.info("Verification returned no results.")
            return

        for i, item in enumerate(self.verification_results):
            self.results_table.insertRow(i)
            self.results_table.setItem(i, 0, QTableWidgetItem(os.path.basename(item.get('original_file', 'N/A'))))
            self.results_table.setItem(i, 1, QTableWidgetItem(os.path.basename(item.get('converted_file', 'N/A'))))
            
            status_item = QTableWidgetItem(item.get('status', 'UNKNOWN'))
            # TODO: Add color coding for status items if desired
            self.results_table.setItem(i, 2, status_item)
            
            mismatches_str = "; ".join(item.get('mismatches', []))
            self.results_table.setItem(i, 3, QTableWidgetItem(mismatches_str if mismatches_str else "No issues"))

        self.results_table.resizeColumnsToContents()


    def _check_overall_status_and_proceed(self):
        """Checks if all files matched and proceeds with deletion and icon update if so."""
        if not self.verification_results:
            self.overall_status_label.setText("Verification did not produce any results.")
            return

        # Check for FFPROBE_NOT_FOUND error first
        if any(item.get('status') == "FFPROBE_NOT_FOUND" for item in self.verification_results):
            msg = "Critical: ffprobe (part of FFmpeg) was not found. Verification cannot be performed."
            self.overall_status_label.setText(msg)
            self.deletion_status_label.setText("Folder deletion skipped.")
            self.icon_update_status_label.setText("Icon update skipped.")
            QMessageBox.critical(self, "FFprobe Error", msg + "\nPlease install FFmpeg and ensure ffprobe is in your system's PATH.")
            logger.error(msg)
            return

        self.all_files_matched = all(item.get('status') == "MATCH" for item in self.verification_results)

        if self.all_files_matched and self.verification_results: # Ensure there were results to check
            self.overall_status_label.setText("All files verified successfully. Proceeding with cleanup.")
            logger.info("All files matched. Proceeding with deletion and icon update.")
            self._perform_conditional_deletion()
        elif not self.verification_results:
             self.overall_status_label.setText("No files were processed by verification.")
             self.deletion_status_label.setText("Folder deletion skipped (no files verified).")
             self.icon_update_status_label.setText("Icon update skipped.")
        else:
            mismatch_count = sum(1 for item in self.verification_results if item.get('status') != "MATCH")
            self.overall_status_label.setText(f"Verification complete. {mismatch_count} issue(s) found.")
            self.deletion_status_label.setText("Originals folder not deleted due to verification issues.")
            self.icon_update_status_label.setText("Icon update skipped.")
            logger.warning("Verification issues found. Originals folder will not be deleted.")


    def _perform_conditional_deletion(self):
        """Deletes the original media folder if all checks passed."""
        if not self.all_files_matched:
            logger.info("Skipping deletion of original folder: Not all files matched verification.")
            self.deletion_status_label.setText("Skipped: Verification issues found.")
            return

        if not self.original_media_folder_path or not os.path.isdir(self.original_media_folder_path):
            logger.error(f"Cannot delete: Original media folder path is invalid or not set: {self.original_media_folder_path}")
            self.deletion_status_label.setText("Error: Original folder path invalid.")
            return

        try:
            shutil.rmtree(self.original_media_folder_path)
            logger.info(f"Successfully deleted folder: {self.original_media_folder_path}")
            self.deletion_status_label.setText(f"Successfully deleted: {os.path.basename(self.original_media_folder_path)}")
            self._update_folder_icon() # Proceed to icon update only if deletion was successful
        except Exception as e:
            logger.error(f"Failed to delete folder {self.original_media_folder_path}: {e}", exc_info=True)
            self.deletion_status_label.setText(f"Failed to delete: {os.path.basename(self.original_media_folder_path)}. Error: {e}")
            self.icon_update_status_label.setText("Icon update skipped due to deletion failure.")
            QMessageBox.critical(self, "Deletion Error", f"Could not delete folder '{self.original_media_folder_path}'.\nError: {e}")


    def _update_folder_icon(self):
        """Updates the main project folder icon."""
        if not self.main_project_folder_path or not os.path.isdir(self.main_project_folder_path):
            logger.error(f"Cannot update icon: Main project folder path is invalid or not set: {self.main_project_folder_path}")
            self.icon_update_status_label.setText("Error: Project folder path invalid.")
            return

        logger.info(f"Attempting to update icon for: {self.main_project_folder_path}")
        # Step 1: Remove "Orange" label
        removed_orange = set_finder_label(self.main_project_folder_path, "None") # Assuming "None" removes all, or find a specific remove
        # For more granular control, one might need a get_labels and then selectively remove.
        # For now, we assume setting "None" clears, then we set "Green".
        # If set_finder_label only *adds*, a separate remove_finder_label(path, "Orange") would be needed.
        # The current macos_utils.set_finder_label replaces the label.

        if not removed_orange: # If setting to "None" failed (which acts as remove here)
             logger.warning(f"Could not remove 'Orange' (or set to 'None') label for {self.main_project_folder_path}. Proceeding to set Green.")
             # Depending on set_finder_label behavior, this might not be an issue if it overwrites.

        # Step 2: Add "Green" label
        added_green = set_finder_label(self.main_project_folder_path, "Green")

        if added_green:
            logger.info(f"Successfully set 'Green' label for folder: {self.main_project_folder_path}")
            self.icon_update_status_label.setText("Project folder icon updated to Green.")
        else:
            logger.error(f"Failed to set 'Green' label for folder: {self.main_project_folder_path}")
            self.icon_update_status_label.setText("Failed to update project folder icon to Green.")
            QMessageBox.warning(self, "Icon Update Failed", f"Could not set 'Green' label for '{self.main_project_folder_path}'.")

if __name__ == '__main__':
    # This part is for testing the panel independently.
    # In a real application, this panel would be part of a larger QStackedWidget or similar.
    from PyQt6.QtWidgets import QApplication
    import sys

    # --- Setup for standalone testing ---
    # Create dummy folders and files for testing
    test_main_dir = os.path.abspath("test_project_folder_main")
    test_orig_dir = os.path.join(test_main_dir, "01 VIDEO.old")
    test_conv_dir = os.path.join(test_main_dir, "02 VIDEO")

    os.makedirs(test_orig_dir, exist_ok=True)
    os.makedirs(test_conv_dir, exist_ok=True)

    # Create dummy files to simulate structure (ffprobe will likely error on these if not media)
    # For a real test, replace with small, valid media files.
    # Or ensure ffprobe is in PATH and can handle empty files gracefully (it usually reports error)
    with open(os.path.join(test_orig_dir, "video1.mov"), 'w') as f: f.write("dummy original")
    with open(os.path.join(test_conv_dir, "video1.mp4"), 'w') as f: f.write("dummy converted") # Match name
    with open(os.path.join(test_orig_dir, "video2.avi"), 'w') as f: f.write("dummy original")
    # video2 converted is missing for testing CONVERTED_MISSING
    with open(os.path.join(test_conv_dir, "video3.mkv"), 'w') as f: f.write("dummy converted") # Original missing

    logger.info(f"Test main dir: {test_main_dir}")
    logger.info(f"Test original dir: {test_orig_dir}")
    logger.info(f"Test converted dir: {test_conv_dir}")
    # --- End setup for standalone testing ---

    app = QApplication(sys.argv)
    verify_panel = VerifyPanel()
    verify_panel.set_paths(
        main_project_path=test_main_dir,
        original_media_path=test_orig_dir,
        converted_media_path=test_conv_dir
    )
    verify_panel.setWindowTitle("Verification Panel Test")
    verify_panel.setGeometry(100, 100, 700, 500)
    verify_panel.show()

    # Example of how to trigger verification after panel is shown
    # In a real app, this might be triggered by a signal or when the panel becomes active.
    # verify_panel.process_verification() # Or click the "Run Verification" button

    exit_code = app.exec()

    # --- Cleanup for standalone testing ---
    # shutil.rmtree(test_main_dir, ignore_errors=True)
    # logger.info(f"Cleaned up test directory: {test_main_dir}")
    # --- End cleanup ---
    sys.exit(exit_code)