#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Results Panel Module

This module handles the third step of the compression workflow:
- Displaying compression results
- Showing file size comparisons
- Providing options to view output files
- Options to start a new compression job
"""

import os
import logging
import subprocess
import platform
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QFrame, QSplitter, QFileDialog, QMessageBox,
    QProgressDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class ResultsWorker(QObject):
    """
    Worker class for running potentially blocking operations in a background thread.
    """
    # Signal for task completion
    task_completed = pyqtSignal(bool, str)
    # Signal for progress updates
    progress_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.working = False
        self.folder_path = ""
        self.report_path = ""
        self.report_data = {}
    
    def set_folder_path(self, path):
        """Set the folder path to open."""
        self.folder_path = path
    
    def set_report_params(self, path, data):
        """Set report parameters."""
        self.report_path = path
        self.report_data = data
    
    @pyqtSlot()
    def open_folder(self):
        """Open the folder in a background thread."""
        try:
            self.working = True
            self.progress_update.emit(f"Opening folder: {self.folder_path}")
            
            # Open directory using the appropriate command for the platform
            success = False
            error_msg = ""
            
            try:
                if platform.system() == "Windows":
                    os.startfile(self.folder_path)
                    success = True
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", self.folder_path], timeout=30)
                    success = True
                else:  # Linux
                    subprocess.run(["xdg-open", self.folder_path], timeout=30)
                    success = True
                    
                logger.info(f"Opened output folder: {self.folder_path}")
            except Exception as e:
                logger.error(f"Failed to open output folder: {str(e)}")
                error_msg = str(e)
                success = False
            
            self.working = False
            self.task_completed.emit(success, error_msg)
            
        except Exception as e:
            logger.error(f"Error in open_folder: {str(e)}", exc_info=True)
            self.working = False
            self.task_completed.emit(False, str(e))
    
    @pyqtSlot()
    def export_report(self):
        """Export a report in a background thread."""
        try:
            self.working = True
            self.progress_update.emit(f"Exporting report to: {self.report_path}")
            
            success = False
            error_msg = ""
            
            try:
                with open(self.report_path, 'w') as f:
                    # Write header
                    f.write("File,Status,Original Size,Compressed Size,Space Saved,Reduction,Duration\n")
                    self.progress_update.emit("Writing header...")
                    
                    # Write each file's results
                    count = 0
                    total = len(self.report_data)
                    for file_path, result in self.report_data.items():
                        count += 1
                        self.progress_update.emit(f"Writing data {count}/{total}...")
                        
                        file_name = os.path.basename(file_path)
                        
                        if 'error' in result:
                            if result['error'] == "Cancelled By User":
                                f.write(f'"{file_name}",Cancelled,,,,,\n')
                            else:
                                f.write(f'"{file_name}",Failed,,,,,\n')
                        else:
                            f.write(
                                f'"{file_name}",Completed,{result["input_size_human"]},{result["output_size_human"]},'
                                f'{result["size_diff_human"]},{result["reduction_percent"]:.1f}%,{result["duration"]:.1f}s\n'
                            )
                
                success = True
                error_msg = "export_report"
                logger.info(f"Exported compression report to {self.report_path}")
                
            except Exception as e:
                logger.error(f"Failed to export report: {str(e)}")
                error_msg = str(e)
                success = False
            
            self.working = False
            self.task_completed.emit(success, error_msg)
            
        except Exception as e:
            logger.error(f"Error in export_report: {str(e)}", exc_info=True)
            self.working = False
            self.task_completed.emit(False, str(e))

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
        
        # Create worker thread and worker
        self.worker_thread = QThread()
        self.worker = ResultsWorker()
        self.worker.moveToThread(self.worker_thread)
        
        # Connect worker signals
        self.worker.task_completed.connect(self.on_task_completed)
        self.worker.progress_update.connect(self.on_progress_update)
        
        # Connect thread start to worker slots
        self.worker_thread.started.connect(self.worker.open_folder)  # Default connection
        
        # Progress dialog
        self.progress_dialog = None
        
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
        
        self.open_folder_button = QPushButton("Open Output Folder")
        self.open_folder_button.clicked.connect(self.open_output_folder)
        
        self.export_report_button = QPushButton("Export Report")
        self.export_report_button.clicked.connect(self.export_report)
        
        self.new_job_button = QPushButton("Start New Job")
        self.new_job_button.clicked.connect(self.start_new_job)
        
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.quit_application)
        
        actions_layout.addWidget(self.open_folder_button)
        actions_layout.addWidget(self.export_report_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.new_job_button)
        actions_layout.addWidget(self.quit_button)
        
        layout.addLayout(actions_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to their respective slots."""
        # Connections are handled in _init_ui
        pass
    
    def set_compression_results(self, results):
        """
        Set the compression results data and update the display.
        
        Args:
            results (dict): Dictionary containing compression results and statistics
        """
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
        total_duration = 0
        
        # Update table
        self.results_table.setRowCount(total_files)
        row = 0
        
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
                
                # Track totals
                total_input_size += input_size
                total_output_size += output_size
                total_duration += result.get('duration', 0)
                
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
    
    def open_output_folder(self):
        """
        Open the folder containing the compressed output files.
        
        Uses system file browser to open the output directory.
        Uses a background thread to avoid UI freezing.
        """
        # Find the first output path
        output_path = None
        for result in self.compression_results.values():
            if 'output_path' in result:
                output_path = result['output_path']
                break
        
        if not output_path:
            QMessageBox.warning(
                self,
                "No Output Files",
                "No output files were found to open."
            )
            return
        
        # Get the directory
        output_dir = os.path.dirname(output_path)
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog("Opening folder...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Opening")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(500)  # Only show for operations > 500ms
        
        # Configure worker for folder opening
        self.worker.set_folder_path(output_dir)
        
        # Disconnect any previous connections
        try:
            self.worker_thread.started.disconnect()
        except TypeError:
            pass  # No connections to disconnect
        
        # Connect thread start to open_folder
        self.worker_thread.started.connect(self.worker.open_folder)
        
        # Start thread if not already running
        if not self.worker_thread.isRunning():
            self.worker_thread.start()
    
    def start_new_job(self):
        """
        Request to start a new compression job.
        
        Emits new_job_requested signal.
        """
        logger.info("New compression job requested")
        self.new_job_requested.emit()
    
    def export_report(self):
        """
        Export a compression report as a text or CSV file.
        
        Saves detailed information about the compression results.
        Uses a background thread to avoid UI freezing.
        """
        if not self.compression_results:
            QMessageBox.warning(
                self,
                "No Results",
                "There are no results to export."
            )
            return
        
        # Ask for save location
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Compression Report",
            os.path.expanduser("~/compression_report.csv"),
            "CSV Files (*.csv);;Text Files (*.txt)"
        )
        
        if not file_path:
            return
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog("Exporting report...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Exporting")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(500)  # Only show for operations > 500ms
        
        # Configure worker for report export
        self.worker.set_report_params(file_path, self.compression_results)
        
        # Disconnect any previous connections
        try:
            self.worker_thread.started.disconnect()
        except TypeError:
            pass  # No connections to disconnect
        
        # Connect thread start to export_report
        self.worker_thread.started.connect(self.worker.export_report)
        
        # Start thread if not already running
        if not self.worker_thread.isRunning():
            self.worker_thread.start()
    
    def on_progress_update(self, message):
        """Update progress dialog message."""
        if self.progress_dialog is not None:
            self.progress_dialog.setLabelText(message)
    
    def on_task_completed(self, success, error_msg):
        """Handle task completion."""
        # Close the progress dialog
        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Show success/error message
        if success:
            if "expor" in error_msg.lower() or "report" in error_msg.lower():
                # This is an export completion
                QMessageBox.information(
                    self,
                    "Report Exported",
                    f"The compression report has been saved successfully."
                )
        else:
            if error_msg:
                QMessageBox.warning(
                    self,
                    "Operation Failed",
                    f"Operation failed: {error_msg}"
                )
    
    def closeEvent(self, event):
        """Handle the close event - clean up threads."""
        # Cancel any ongoing operations
        if hasattr(self, 'worker') and self.worker:
            self.worker.working = False
        
        # Quit the worker thread properly
        if hasattr(self, 'worker_thread') and self.worker_thread:
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                if not self.worker_thread.wait(3000):  # Wait up to 3 seconds for thread to finish
                    self.worker_thread.terminate()
        
        super().closeEvent(event)
    
    def quit_application(self):
        """Exit the application."""
        logger.info("User requested application exit")
        self.window().close()