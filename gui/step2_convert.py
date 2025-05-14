#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert Panel Module

This module handles the second step of the compression workflow:
- Displaying files queued for compression
- Setting output options
- Managing the compression process
- Showing compression progress
"""

import os
import logging
import time
import threading
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QComboBox, QFileDialog, QListWidget,
    QGroupBox, QSplitter, QTextEdit, QCheckBox, QFrame,
    QListWidgetItem, QRadioButton, QButtonGroup,
    QProgressDialog
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QThread, QObject, pyqtSlot
from PyQt6.QtGui import QFont

# Import core functionality
from core.video_compression import get_compression_settings, estimate_file_size, calculate_time_remaining
from core.queue_manager import QueueStatus

logger = logging.getLogger(__name__)


class EstimationWorker(QObject):
    """
    Worker class for running file size estimation in a background thread.
    """
    # Signal for estimation result
    estimation_complete = pyqtSignal(float, float, float)  # savings_mb, savings_percent, success
    # Signal for progress updates
    progress_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.queued_files = []
        
    def set_files(self, files):
        """Set the queued files to estimate."""
        self.queued_files = files
    
    @pyqtSlot()
    def calculate_size_estimate(self):
        """Calculate size estimates in a background thread."""
        try:
            if not self.queued_files:
                self.estimation_complete.emit(0, 0, 0)
                return
                
            self.progress_update.emit("Calculating total input size...")
            
            # Calculate total input size
            total_input_size = 0
            for i, file_path in enumerate(self.queued_files):
                try:
                    total_input_size += os.path.getsize(file_path)
                except OSError:
                    pass
                
                if i % 5 == 0:  # Update progress every 5 files
                    self.progress_update.emit(f"Checking input file {i+1}/{len(self.queued_files)}...")
            
            # Estimate output size using default settings
            settings = get_compression_settings()
            estimated_output_size = 0
            
            self.progress_update.emit("Estimating output sizes...")
            
            for i, file_path in enumerate(self.queued_files):
                try:
                    estimated_output_size += estimate_file_size(file_path, settings)
                except:
                    # If estimation fails, use a rough calculation (about 25% of original)
                    try:
                        estimated_output_size += os.path.getsize(file_path) * 0.25
                    except OSError:
                        pass
                        
                if i % 5 == 0:  # Update progress every 5 files
                    self.progress_update.emit(f"Estimating file {i+1}/{len(self.queued_files)}...")
            
            # Calculate savings
            if total_input_size > 0:
                savings = total_input_size - estimated_output_size
                savings_mb = savings / (1024 * 1024)
                savings_percent = (savings / total_input_size) * 100
                
                self.estimation_complete.emit(savings_mb, savings_percent, 1.0)
            else:
                self.estimation_complete.emit(0, 0, 0)
                
        except Exception as e:
            logger.error(f"Error in calculate_size_estimate: {str(e)}", exc_info=True)
            self.estimation_complete.emit(0, 0, 0)


class ConvertPanel(QWidget):
    """
    Panel for configuring and running the video compression process.
    Handles compression options and progress tracking.
    """
    # Signal to notify when compression is complete
    compression_complete = pyqtSignal(dict)
    # Signals for navigation
    back_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the conversion panel with compression options."""
        super().__init__(parent)
        logger.info("Initializing conversion panel")
        
        self.queued_files = []
        self.output_dir = ""
        self.processing = False
        self.start_time = 0
        self.current_file = ""
        self.timer = None
        self.queue_manager = None
        
        # Create worker thread and estimation worker
        self.estimation_thread = QThread()
        self.estimation_worker = EstimationWorker()
        self.estimation_worker.moveToThread(self.estimation_thread)
        
        # Connect worker signals
        self.estimation_worker.estimation_complete.connect(self.on_estimation_complete)
        self.estimation_worker.progress_update.connect(self.on_estimation_progress)
        
        # Connect thread start to worker slots
        self.estimation_thread.started.connect(self.estimation_worker.calculate_size_estimate)
        
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
        title_label = QLabel("Step 2: Convert Files")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Queue information
        queue_group = QGroupBox("Files Queued for Compression")
        queue_layout = QVBoxLayout(queue_group)
        
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(150)
        queue_layout.addWidget(self.queue_list)
        
        queue_stats_layout = QHBoxLayout()
        self.queue_stats_label = QLabel("0 files queued")
        queue_stats_layout.addWidget(self.queue_stats_label)
        queue_stats_layout.addStretch()
        
        # Estimated size savings
        self.size_estimate_label = QLabel("Estimated savings: 0 MB")
        queue_stats_layout.addWidget(self.size_estimate_label)
        
        queue_layout.addLayout(queue_stats_layout)
        layout.addWidget(queue_group)
        
        # Output settings
        settings_group = QGroupBox("Output Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Output directory selection
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Output Directory:")
        dir_layout.addWidget(dir_label)
        
        self.output_dir_label = QLabel("Same as source")
        self.output_dir_label.setStyleSheet("padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        
        self.output_dir_button = QPushButton("Browse...")
        self.output_dir_button.setFixedWidth(100)
        self.output_dir_button.clicked.connect(self.select_output_directory)
        
        dir_layout.addWidget(self.output_dir_label, 1)
        dir_layout.addWidget(self.output_dir_button, 0)
        
        settings_layout.addLayout(dir_layout)
        
        # Use default settings
        self.use_defaults_checkbox = QCheckBox("Use recommended compression settings (24 Mbps HEVC)")
        self.use_defaults_checkbox.setChecked(True)
        settings_layout.addWidget(self.use_defaults_checkbox)
        
        layout.addWidget(settings_group)
        
        # Progress section
        progress_group = QGroupBox("Compression Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Current file
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current file:"))
        self.current_file_label = QLabel("None")
        current_layout.addWidget(self.current_file_label, 1)
        progress_layout.addLayout(current_layout)
        
        # File progress bar
        file_progress_layout = QHBoxLayout()
        file_progress_layout.addWidget(QLabel("File:"))
        self.file_progress_bar = QProgressBar()
        file_progress_bar_style = """
        QProgressBar {
            border: 1px solid #bbb;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4a86e8;
        }
        """
        self.file_progress_bar.setStyleSheet(file_progress_bar_style)
        file_progress_layout.addWidget(self.file_progress_bar, 1)
        progress_layout.addLayout(file_progress_layout)
        
        # Overall progress bar
        overall_progress_layout = QHBoxLayout()
        overall_progress_layout.addWidget(QLabel("Overall:"))
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setStyleSheet(file_progress_bar_style)
        overall_progress_layout.addWidget(self.overall_progress_bar, 1)
        progress_layout.addLayout(overall_progress_layout)
        
        # Time information
        time_layout = QHBoxLayout()
        
        # Elapsed time
        elapsed_layout = QHBoxLayout()
        elapsed_layout.addWidget(QLabel("Time elapsed:"))
        self.elapsed_time_label = QLabel("00:00:00")
        elapsed_layout.addWidget(self.elapsed_time_label)
        time_layout.addLayout(elapsed_layout)
        
        time_layout.addStretch()
        
        # Remaining time
        remaining_layout = QHBoxLayout()
        remaining_layout.addWidget(QLabel("Estimated remaining:"))
        self.remaining_time_label = QLabel("--:--:--")
        remaining_layout.addWidget(self.remaining_time_label)
        time_layout.addLayout(remaining_layout)
        
        progress_layout.addLayout(time_layout)
        
        # Log output toggle and window
        log_layout = QVBoxLayout()
        log_header = QHBoxLayout()
        
        self.show_log_checkbox = QCheckBox("Show log output")
        self.show_log_checkbox.setChecked(False)
        self.show_log_checkbox.stateChanged.connect(self._toggle_log_visibility)
        log_header.addWidget(self.show_log_checkbox)
        log_header.addStretch()
        
        log_layout.addLayout(log_header)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setVisible(False)
        log_layout.addWidget(self.log_output)
        
        progress_layout.addLayout(log_layout)
        
        layout.addWidget(progress_group)
        
        # Navigation and action buttons
        nav_layout = QHBoxLayout()
        
        self.back_button = QPushButton("← Back")
        self.back_button.setFixedWidth(100)
        self.back_button.clicked.connect(self.back_clicked)
        
        self.start_button = QPushButton("Start Compression")
        self.start_button.clicked.connect(self.toggle_compression)
        
        self.next_button = QPushButton("Next →")
        self.next_button.setFixedWidth(100)
        self.next_button.setEnabled(False)
        self.next_button.clicked.connect(self.next_clicked)
        
        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.start_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    def _connect_signals(self):
        """Connect UI signals to their respective slots."""
        # Most connections are handled in _init_ui
        pass
    
    def _toggle_log_visibility(self, state):
        """Toggle the visibility of the log output window."""
        self.log_output.setVisible(bool(state))
    
    def set_queue_manager(self, queue_manager):
        """
        Set the queue manager reference.
        
        Args:
            queue_manager: The queue manager instance to use
        """
        self.queue_manager = queue_manager
        logger.info("Queue manager set in ConvertPanel")
        
    def set_queued_files(self, files):
        """
        Set the list of files queued for compression.
        
        Args:
            files (list): List of file paths to be compressed
        """
        self.queued_files = files
        self.queue_list.clear()
        
        # Add files to the list widget
        for file_path in files:
            item = QListWidgetItem(os.path.basename(file_path))
            self.queue_list.addItem(item)
        
        # Update queue stats
        self.queue_stats_label.setText(f"{len(files)} files queued")
        
        # Update size estimate
        self._update_size_estimate()
        
        logger.info(f"Queue updated with {len(files)} files")
    
    def _update_size_estimate(self):
        """
        Start calculating estimated size savings in a background thread.
        Shows a progress dialog while calculating.
        """
        if not self.queued_files:
            self.size_estimate_label.setText("Estimated savings: 0 MB")
            return
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog("Calculating file sizes...", "Cancel", 0, 0, self)
        self.progress_dialog.setWindowTitle("Size Estimation")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(500)  # Only show for operations > 500ms
        self.progress_dialog.canceled.connect(self.cancel_estimation)
        
        # Configure worker
        self.estimation_worker.set_files(self.queued_files)
        
        # Start the thread if not already running
        if not self.estimation_thread.isRunning():
            self.estimation_thread.start()
            
    def cancel_estimation(self):
        """Cancel the ongoing estimation."""
        if self.estimation_thread.isRunning():
            self.estimation_thread.quit()
            if not self.estimation_thread.wait(1000):
                self.estimation_thread.terminate()
    
    def on_estimation_progress(self, message):
        """Handle progress updates during estimation."""
        if self.progress_dialog is not None:
            self.progress_dialog.setLabelText(message)
    
    def on_estimation_complete(self, savings_mb, savings_percent, success):
        """Handle completion of size estimation."""
        # Close the progress dialog
        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        # Update the UI with results
        if success > 0:
            self.size_estimate_label.setText(f"Est. savings: {savings_mb:.2f} MB ({savings_percent:.1f}%)")
        else:
            self.size_estimate_label.setText("Estimated savings: Unknown")
    
    def select_output_directory(self):
        """
        Open dialog for selecting output directory.
        
        Updates the output directory field.
        """
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            os.path.expanduser("~")
        )
        
        if directory:
            self.output_dir = directory
            self.output_dir_label.setText(directory)
            logger.info(f"Output directory set to: {directory}")
    
    def toggle_compression(self):
        """Start or cancel the compression process."""
        if not self.processing:
            self.start_compression()
        else:
            self.cancel_compression()
    
    def start_compression(self):
        """
        Begin the compression process for all queued files.
        
        Delegates to core.queue_manager for actual compression.
        Updates progress as compression proceeds.
        """
        if not self.queued_files:
            logger.warning("Cannot start compression: No files in queue")
            return
        
        # Verify that queue manager actually has files
        if not self.queue_manager or not self.queue_manager.queue:
            error_msg = "No files in compression queue. This may happen if files were not found after directory rename."
            logger.error(error_msg)
            self.log_output.append(f"ERROR: {error_msg}")
            
            # Make log visible automatically when error occurs
            self.show_log_checkbox.setChecked(True)
            self._toggle_log_visibility(True)
            
            # Show error to the user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Queue Error",
                error_msg + "\n\nPlease go back to Step 1 and re-select the folder with the renamed structure."
            )
            return
        
        # Update UI to processing state
        self.processing = True
        self.start_button.setText("Cancel Compression")
        self.back_button.setEnabled(False)
        self.output_dir_button.setEnabled(False)
        self.use_defaults_checkbox.setEnabled(False)
        
        # Reset progress
        self.file_progress_bar.setValue(0)
        self.overall_progress_bar.setValue(0)
        self.start_time = time.time()
        
        # Start timer for updating elapsed time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_elapsed_time)
        self.timer.start(1000)  # Update every second
        
        # Use the queue manager that was set
        if not self.queue_manager:
            logger.error("Queue manager not set in ConvertPanel")
            self.log_output.append("ERROR: Queue manager not set")
            self.processing = False
            return
            
        queue_manager = self.queue_manager
        
        # Log queue status
        stats = queue_manager.get_queue_status()
        self.log_output.append(f"Queue status: {stats['total']} files in queue")
        
        # Get output directory (or None for default)
        output_dir = self.output_dir if self.output_dir else None
        
        # Get settings
        settings = get_compression_settings() if self.use_defaults_checkbox.isChecked() else None
        
        # Start compression in a separate thread
        logger.info("Starting compression process")
        self.log_output.append("Starting compression process...")
        
        self.compression_thread = threading.Thread(
            target=self._run_compression,
            args=(queue_manager, output_dir, settings)
        )
        self.compression_thread.daemon = True
        self.compression_thread.start()
    
    def _run_compression(self, queue_manager, output_dir, settings):
        """Run the compression process in a background thread."""
        try:
            # Run compression with progress updates
            result = queue_manager.process_queue(
                output_dir=output_dir,
                settings=settings,
                progress_callback=self.update_progress
            )
            
            # Get results after completion
            results = queue_manager.get_results()
            
            # Signal completion
            self.compression_complete.emit(results)
            
        except Exception as e:
            logger.error(f"Error during compression: {str(e)}", exc_info=True)
            # Update log in UI thread
            from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
            QMetaObject.invokeMethod(
                self.log_output,
                "append",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, f"ERROR: {str(e)}")
            )
        finally:
            # Update UI back to idle state using thread-safe method
            from PyQt6.QtCore import QMetaObject, Qt
            
            # Signal UI update via a queued connection
            QMetaObject.invokeMethod(
                self,
                "finish_compression",
                Qt.ConnectionType.QueuedConnection
            )
                
    def closeEvent(self, event):
        """Handle the close event - clean up threads."""
        # Cancel any ongoing operations
        if hasattr(self, 'estimation_worker'):
            self.cancel_estimation()
        
        # Quit the estimation thread properly
        if hasattr(self, 'estimation_thread') and self.estimation_thread:
            if self.estimation_thread.isRunning():
                self.estimation_thread.quit()
                if not self.estimation_thread.wait(3000):  # Wait up to 3 seconds
                    self.estimation_thread.terminate()
        
        super().closeEvent(event)
    
    def update_progress(self, current_file, file_progress_percentage, overall_progress_percentage=None):
        """
        Update the progress indicators for the current file.
        
        Args:
            current_file (str): Path to the current file being processed
            file_progress_percentage (float): File percentage completion (0-1)
            overall_progress_percentage (float, optional): Overall progress percentage (0-1).
                                                          If None, uses file_progress_percentage.
        """
        # For backward compatibility
        if overall_progress_percentage is None:
            overall_progress_percentage = file_progress_percentage
        # Update in UI thread
        from PyQt6.QtCore import QMetaObject, Q_ARG, Qt
        
        # Update current file
        self.current_file = current_file
        QMetaObject.invokeMethod(
            self.current_file_label, 
            "setText", 
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, os.path.basename(current_file))
        )
        
        # Update progress bars (scale to percentage)
        file_progress = int(file_progress_percentage * 100)
        overall_progress = int(overall_progress_percentage * 100)
        
        QMetaObject.invokeMethod(
            self.file_progress_bar,
            "setValue",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, file_progress)
        )
        
        QMetaObject.invokeMethod(
            self.overall_progress_bar,
            "setValue",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, overall_progress)
        )
        
        # Update log
        log_msg = f"Processing: {os.path.basename(current_file)} ({file_progress}%)"
        QMetaObject.invokeMethod(
            self.log_output, 
            "append", 
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, log_msg)
        )
        
        # Calculate time remaining
        if overall_progress_percentage > 0:
            current_time = time.time()
            remaining = calculate_time_remaining(
                overall_progress_percentage,
                self.start_time,
                current_time
            )
            
            QMetaObject.invokeMethod(
                self.remaining_time_label, 
                "setText", 
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, remaining)
            )
    
    @pyqtSlot()
    def finish_compression(self):
        """Thread-safe method to update UI after compression completes."""
        # Update UI back to idle state
        self.processing = False
        self.back_button.setEnabled(True)
        self.output_dir_button.setEnabled(True)
        self.use_defaults_checkbox.setEnabled(True)
        self.start_button.setText("Start Compression")
        self.start_button.setEnabled(True)
        self.next_button.setEnabled(True)
        
        # If compression was cancelled, log it
        if self.queue_manager and hasattr(self.queue_manager, '_cancelled') and self.queue_manager._cancelled:
            self.log_output.append("Compression was cancelled by user")
            
        # Stop timer
        if self.timer:
            self.timer.stop()
            self.timer = None
    
    def _update_elapsed_time(self):
        """Update the elapsed time display."""
        if self.processing and self.start_time > 0:
            elapsed_seconds = int(time.time() - self.start_time)
            hours, remainder = divmod(elapsed_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            elapsed_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.elapsed_time_label.setText(elapsed_str)
    
    def cancel_compression(self):
        """Cancel the ongoing compression process."""
        if not self.processing:
            return
            
        logger.info("Cancelling compression")
        self.log_output.append("Cancelling compression...")
        
        # Update UI to show cancellation is in progress
        self.start_button.setText("Cancelling...")
        self.start_button.setEnabled(False)
        
        # Cancel via queue manager
        if self.queue_manager:
            cancelled = self.queue_manager.cancel_processing()
            if cancelled:
                self.log_output.append("Compression cancelled. Cleaning up and stopping process...")
                # Show log automatically when cancellation occurs
                self.show_log_checkbox.setChecked(True)
                self._toggle_log_visibility(True)
            else:
                self.log_output.append("Failed to cancel compression")
                logger.error("Failed to cancel compression process")
        else:
            logger.error("Queue manager not available for cancellation")
            self.log_output.append("ERROR: Queue manager not available for cancellation")