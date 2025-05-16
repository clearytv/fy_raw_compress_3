#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Results Panel Module

This module handles the third step of the compression workflow:
- Displaying compression results
- Showing file size comparisons
- Options to start a new compression job
"""

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QColor

from core.macos_utils import set_finder_label # Import for Finder labels

logger = logging.getLogger(__name__)


class ResultsPanel(QWidget):
    """
    Panel for displaying compression results and statistics.
    Shows file size savings and provides options for next steps.
    """
    # Signal to notify when user wants to start a new job
    new_job_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the results panel with output display components."""
        super().__init__(parent)
        logger.info("Initializing results panel")
        
        self.compression_results = {}
        self.parent_folder_path = "" # To store the path from Step 1
        
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
        title_label = QLabel("Step 3: Results")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Summary statistics section
        stats_group = QGroupBox("Compression Summary")
        stats_layout = QVBoxLayout(stats_group)
        
        # Create a grid of statistics
        stats_grid = QHBoxLayout()
        
        # Files processed
        files_layout = QVBoxLayout()
        self.files_label = QLabel("Files Processed")
        self.files_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.files_count = QLabel("0")
        self.files_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.files_count.setStyleSheet("font-size: 24px; font-weight: bold;")
        files_layout.addWidget(self.files_label)
        files_layout.addWidget(self.files_count)
        stats_grid.addLayout(files_layout)
        
        # Time taken
        time_layout = QVBoxLayout()
        self.time_label = QLabel("Total Time")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_value = QLabel("00:00:00")
        self.time_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_value.setStyleSheet("font-size: 24px; font-weight: bold;")
        time_layout.addWidget(self.time_label)
        time_layout.addWidget(self.time_value)
        stats_grid.addLayout(time_layout)
        
        # Space saved
        space_layout = QVBoxLayout()
        self.space_label = QLabel("Space Saved")
        self.space_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.space_value = QLabel("0 MB")
        self.space_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.space_value.setStyleSheet("font-size: 24px; font-weight: bold;")
        space_layout.addWidget(self.space_label)
        space_layout.addWidget(self.space_value)
        stats_grid.addLayout(space_layout)
        
        # Reduction percentage
        reduction_layout = QVBoxLayout()
        self.reduction_label = QLabel("Size Reduction")
        self.reduction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reduction_value = QLabel("0%")
        self.reduction_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reduction_value.setStyleSheet("font-size: 24px; font-weight: bold;")
        reduction_layout.addWidget(self.reduction_label)
        reduction_layout.addWidget(self.reduction_value)
        stats_grid.addLayout(reduction_layout)
        
        stats_layout.addLayout(stats_grid)
        layout.addWidget(stats_group)
        
        # Results table section
        results_group = QGroupBox("File Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "File", "Status", "Original Size", "Compressed Size", "Space Saved", "Reduction"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        results_layout.addWidget(self.results_table)
        
        # Files count summary
        files_summary_layout = QHBoxLayout()
        self.success_label = QLabel("Successful: 0")
        self.failed_label = QLabel("Failed: 0")
        self.cancelled_label = QLabel("Cancelled: 0")
        files_summary_layout.addWidget(self.success_label)
        files_summary_layout.addWidget(self.failed_label)
        files_summary_layout.addWidget(self.cancelled_label)
        files_summary_layout.addStretch()
        results_layout.addLayout(files_summary_layout)
        
        layout.addWidget(results_group, 1)  # Give this section more vertical space
        
        # Action buttons
        actions_layout = QHBoxLayout()
        
        self.new_job_button = QPushButton("Start New Job")
        self.new_job_button.clicked.connect(self.start_new_job)
        
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.quit_application)
        
        actions_layout.addStretch()
        actions_layout.addWidget(self.new_job_button)
        actions_layout.addWidget(self.quit_button)
        
        layout.addLayout(actions_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to their respective slots."""
        # Connections are handled in _init_ui
        pass

    def set_parent_folder_path(self, path: str):
        """Sets the path of the parent folder being processed."""
        self.parent_folder_path = path
        logger.info(f"Parent folder path set in ResultsPanel: {path}")
    
    def set_compression_results(self, results):
        """
        Set the compression results data and update the display.
        
        Args:
            results (dict): Dictionary containing compression results and statistics
        """
        # Set Finder label to Green for the parent folder when results are set
        if self.parent_folder_path:
            logger.info(f"Attempting to set 'Green' Finder label for {self.parent_folder_path}")
            if not set_finder_label(self.parent_folder_path, "Green"):
                logger.warning(f"Could not set 'Green' Finder label for {self.parent_folder_path}")
        else:
            logger.warning("Parent folder path not set in ResultsPanel, cannot set 'Green' label.")

        self.compression_results = results
        self._update_results_display()
        logger.info("Compression results updated in UI")
    
    def _update_results_display(self):
        """
        Update the UI elements with the current compression results.
        
        Calculates statistics and populates the results table.
        """
        if not self.compression_results:
            logger.warning("No compression results to display")
            return
        
        # Calculate overall statistics
        total_files = len(self.compression_results)
        successful_files = 0
        failed_files = 0
        cancelled_files = 0
        total_input_size = 0
        total_output_size = 0
        total_duration = 0  # Will be overridden if special duration entry is found
        
        # Update table
        self.results_table.setRowCount(total_files)
        row = 0
        
        # Check for special duration info entry
        if "total_duration_info" in self.compression_results:
            duration_info = self.compression_results.pop("total_duration_info")
            if duration_info.get('is_duration_info', False):
                total_duration = duration_info.get('duration', 0)
                logger.info(f"Found special duration info entry with total_duration={total_duration:.2f}s")
        
        # Process regular file entries
        for file_path, result in self.compression_results.items():
            file_name = os.path.basename(file_path)
            
            # Create table items
            file_item = QTableWidgetItem(file_name)
            self.results_table.setItem(row, 0, file_item)
            
            # Check if there was an error
            if 'error' in result:
                if result['error'] == "Cancelled By User":
                    # Handle cancelled files
                    status_item = QTableWidgetItem("Cancelled")
                    status_item.setForeground(QColor(255, 0, 0))  # Red text
                    self.results_table.setItem(row, 1, status_item)
                    
                    # Fill rest of row with cancellation message
                    error_item = QTableWidgetItem("Cancelled By User")
                    error_item.setForeground(QColor(255, 0, 0))
                    self.results_table.setItem(row, 2, error_item)
                    self.results_table.setSpan(row, 2, 1, 4)  # Span across remaining columns
                    
                    cancelled_files += 1  # Count as cancelled for statistics
                else:
                    # Handle regular failures
                    status_item = QTableWidgetItem("Failed")
                    status_item.setForeground(QColor(255, 0, 0))  # Red text
                    self.results_table.setItem(row, 1, status_item)
                    
                    # Fill rest of row with error message
                    error_item = QTableWidgetItem(str(result['error']))
                    error_item.setForeground(QColor(255, 0, 0))
                    self.results_table.setItem(row, 2, error_item)
                    self.results_table.setSpan(row, 2, 1, 4)  # Span across remaining columns
                    
                    failed_files += 1
            else:
                # Process successful compression
                successful_files += 1
                
                status_item = QTableWidgetItem("Completed")
                status_item.setForeground(QColor(0, 128, 0))  # Green text
                self.results_table.setItem(row, 1, status_item)
                
                # Add size information
                input_size = result['input_size']
                output_size = result['output_size']
                size_diff = result['size_diff']
                percentage = result['reduction_percent']
                
                # Track totals (but not duration - we get that from the special entry)
                total_input_size += input_size
                total_output_size += output_size
                # Don't accumulate duration here anymore - we use the total value from ConvertPanel
                
                # Add items to table
                input_item = QTableWidgetItem(result['input_size_human'])
                output_item = QTableWidgetItem(result['output_size_human'])
                diff_item = QTableWidgetItem(result['size_diff_human'])
                percent_item = QTableWidgetItem(f"{percentage:.1f}%")
                
                self.results_table.setItem(row, 2, input_item)
                self.results_table.setItem(row, 3, output_item)
                self.results_table.setItem(row, 4, diff_item)
                self.results_table.setItem(row, 5, percent_item)
                
            row += 1
        
        # Update summary statistics
        self.files_count.setText(str(total_files))
        self.success_label.setText(f"Successful: {successful_files}")
        self.failed_label.setText(f"Failed: {failed_files}")
        self.cancelled_label.setText(f"Cancelled: {cancelled_files}")
        
        # Format total time
        hours, remainder = divmod(int(total_duration), 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        self.time_value.setText(time_str)
        
        # Calculate total savings
        total_saved = total_input_size - total_output_size
        
        # Format space saved
        if total_saved >= 1024*1024*1024:
            space_str = f"{total_saved/(1024*1024*1024):.2f} GB"
        else:
            space_str = f"{total_saved/(1024*1024):.2f} MB"
        self.space_value.setText(space_str)
        
        # Calculate reduction percentage
        if total_input_size > 0:
            reduction = (total_saved / total_input_size) * 100
            self.reduction_value.setText(f"{reduction:.1f}%")
        else:
            self.reduction_value.setText("0%")
            
        logger.info("Results display updated")
    
    
    def start_new_job(self):
        """
        Request to start a new compression job.
        
        Emits new_job_requested signal.
        """
        logger.info("New compression job requested")
        self.new_job_requested.emit()
    
    
    
    def closeEvent(self, event):
        """Handle the close event."""
        super().closeEvent(event)
    
    def reset_panel(self):
        """Reset the panel to initial state when starting a new job."""
        logger.info("Resetting results panel state")
        
        # Reset stored data
        self.compression_results = {}
        self.parent_folder_path = "" # Reset parent folder path
        
        # Reset UI elements
        self.files_count.setText("0")
        self.time_value.setText("00:00:00")
        self.space_value.setText("0 MB")
        self.reduction_value.setText("0%")
        self.success_label.setText("Successful: 0")
        self.failed_label.setText("Failed: 0")
        self.cancelled_label.setText("Cancelled: 0")
        
        # Clear the results table
        self.results_table.setRowCount(0)
    
    def quit_application(self):
        """Exit the application."""
        logger.info("User requested application exit")
        self.window().close()