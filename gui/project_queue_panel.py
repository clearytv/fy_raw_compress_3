#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Project Queue Panel Module

This module implements a UI panel for managing the project queue:
- Displaying projects queued for processing
- Controls to add/remove/reorder projects
- Showing queue status and projects progress
- Managing queue execution (start/pause/cancel)
"""

import os
import logging
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar, QTableWidget, QTableWidgetItem,
    QGroupBox, QSplitter, QHeaderView, QMenu, QMessageBox,
    QFileDialog, QDialog, QFormLayout, QLineEdit
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QObject
from PyQt6.QtGui import QFont, QAction, QColor, QBrush

# Import core functionality
from core.project_queue_manager import ProjectQueueManager, ProjectStatus
from core.project_manager import ProjectManager

logger = logging.getLogger(__name__)


class ProjectQueuePanel(QWidget):
    """
    Panel for managing and monitoring the project queue.
    
    This panel allows users to add, remove, and reorder projects in the queue,
    as well as start, pause, and cancel queue processing. It displays real-time
    status updates for projects in the queue.
    """
    # Signal to notify main window when back button is clicked
    back_clicked = pyqtSignal()
    
    # Signal to notify main window when a project is selected for editing
    project_selected = pyqtSignal(str)  # project_id
    
    # Signal to notify when the queue status changes
    queue_status_changed = pyqtSignal(dict)
    
    # Signal to notify main window when user wants to add a new project
    add_project_requested = pyqtSignal()
    
    # Signal for thread-safe progress updates (emitted from background thread)
    # Parameters: project_id, project_name, project_progress, overall_progress
    progress_update = pyqtSignal(str, str, float, float)
    
    # Signal for thread-safe project completion notification
    # Parameters: project_id, project_name, success
    project_complete = pyqtSignal(str, str, bool)
    
    def __init__(self, parent=None, project_manager=None):
        """
        Initialize the project queue panel.
        
        Args:
            parent: Parent widget
            project_manager: ProjectManager instance (will be created if None)
        """
        super().__init__(parent)
        logger.info("Initializing project queue panel")
        
        # Store or create project manager
        self.project_manager = project_manager or ProjectManager()
        
        # Convenience reference to project queue manager
        self.project_queue_manager = self.project_manager.project_queue_manager
        
        # Flag to track if queue is processing
        self.is_processing = False
        
        # Timer for updating elapsed time
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)
        self.start_time = 0
        
        # Register callbacks with project manager
        self.project_manager.register_progress_callback(self._handle_progress_update)
        self.project_manager.register_on_project_complete_callback(self._handle_project_complete)
        
        # Connect signals to UI update slots (ensures UI updates happen on main thread)
        self.progress_update.connect(self._update_ui_progress)
        self.project_complete.connect(self._update_ui_project_complete)
        
        # Create UI components
        self._init_ui()
        
        # Refresh the project table
        self.refresh_projects()
    
    def _init_ui(self):
        """Set up the user interface components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Project Queue")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Queue table section
        queue_group = QGroupBox("Queued Projects")
        queue_layout = QVBoxLayout(queue_group)
        
        # Project table
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(6)  # ID, Name, Status, Files, Progress, Actions
        self.project_table.setHorizontalHeaderLabels(["ID", "Project Name", "Status", "Files", "Progress", "Actions"])
        self.project_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column stretches
        self.project_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.project_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.project_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_table.customContextMenuRequested.connect(self._show_context_menu)
        queue_layout.addWidget(self.project_table)
        
        # Queue control buttons
        queue_buttons_layout = QHBoxLayout()
        
        self.add_project_button = QPushButton("Add Project")
        self.add_project_button.clicked.connect(self._add_project_dialog)
        queue_buttons_layout.addWidget(self.add_project_button)
        
        self.remove_project_button = QPushButton("Remove Selected")
        self.remove_project_button.clicked.connect(self._remove_selected_project)
        queue_buttons_layout.addWidget(self.remove_project_button)
        
        self.move_up_button = QPushButton("Move Up")
        self.move_up_button.clicked.connect(lambda: self._reorder_project(-1))
        queue_buttons_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("Move Down")
        self.move_down_button.clicked.connect(lambda: self._reorder_project(1))
        queue_buttons_layout.addWidget(self.move_down_button)
        
        self.clear_queue_button = QPushButton("Clear Queue")
        self.clear_queue_button.clicked.connect(self._clear_queue)
        queue_buttons_layout.addWidget(self.clear_queue_button)
        
        queue_layout.addLayout(queue_buttons_layout)
        
        # Queue statistics
        queue_stats_layout = QHBoxLayout()
        self.queue_stats_label = QLabel("0 projects queued (0 pending, 0 completed, 0 failed)")
        queue_stats_layout.addWidget(self.queue_stats_label)
        queue_stats_layout.addStretch()
        queue_layout.addLayout(queue_stats_layout)
        
        layout.addWidget(queue_group)
        
        # Current project progress section
        progress_group = QGroupBox("Current Project Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        # Current project
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current project:"))
        self.current_project_label = QLabel("None")
        current_layout.addWidget(self.current_project_label, 1)
        progress_layout.addLayout(current_layout)
        
        # Project progress bar
        project_progress_layout = QHBoxLayout()
        project_progress_layout.addWidget(QLabel("Project:"))
        self.project_progress_bar = QProgressBar()
        progress_bar_style = """
        QProgressBar {
            border: 1px solid #bbb;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4a86e8;
        }
        """
        self.project_progress_bar.setStyleSheet(progress_bar_style)
        project_progress_layout.addWidget(self.project_progress_bar, 1)
        progress_layout.addLayout(project_progress_layout)
        
        # Queue progress bar
        queue_progress_layout = QHBoxLayout()
        queue_progress_layout.addWidget(QLabel("Queue:"))
        self.queue_progress_bar = QProgressBar()
        self.queue_progress_bar.setStyleSheet(progress_bar_style)
        queue_progress_layout.addWidget(self.queue_progress_bar, 1)
        progress_layout.addLayout(queue_progress_layout)
        
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
        
        layout.addWidget(progress_group)
        
        # Queue control section
        control_group = QGroupBox("Queue Control")
        control_layout = QVBoxLayout(control_group)
        
        # Control buttons
        control_buttons_layout = QHBoxLayout()
        
        self.start_queue_button = QPushButton("Start Queue")
        self.start_queue_button.clicked.connect(self._toggle_queue_processing)
        control_buttons_layout.addWidget(self.start_queue_button)
        
        self.cancel_queue_button = QPushButton("Cancel Queue")
        self.cancel_queue_button.clicked.connect(self._cancel_queue)
        self.cancel_queue_button.setEnabled(False)
        control_buttons_layout.addWidget(self.cancel_queue_button)
        
        control_layout.addLayout(control_buttons_layout)
        
        layout.addWidget(control_group)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()
        
        self.back_button = QPushButton("← Back")
        self.back_button.setFixedWidth(100)
        self.back_button.clicked.connect(self.back_clicked)
        
        nav_layout.addWidget(self.back_button)
        nav_layout.addStretch()
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    def refresh_projects(self):
        """Refresh the project table with current queue data."""
        projects = self.project_queue_manager.get_all_projects()
        
        # Update table
        self.project_table.setRowCount(len(projects))
        
        for row, project in enumerate(projects):
            # ID column (hidden, used for reference)
            id_item = QTableWidgetItem(project.get("id", ""))
            self.project_table.setItem(row, 0, id_item)
            
            # Name column
            name_item = QTableWidgetItem(project.get("name", "Unnamed Project"))
            self.project_table.setItem(row, 1, name_item)
            
            # Status column
            status_str = project.get("status", "pending")
            status_item = QTableWidgetItem(status_str.upper())
            
            # Set status color
            if status_str == "completed":
                status_item.setForeground(QBrush(QColor("green")))
            elif status_str == "failed":
                status_item.setForeground(QBrush(QColor("red")))
            elif status_str == "processing":
                status_item.setForeground(QBrush(QColor("blue")))
                
            self.project_table.setItem(row, 2, status_item)
            
            # Files column
            files_count = len(project.get("input_files", []))
            files_item = QTableWidgetItem(str(files_count))
            self.project_table.setItem(row, 3, files_item)
            
            # Progress column - create a progress bar
            progress_widget = QProgressBar()
            progress_widget.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #bbb;
                    border-radius: 3px;
                    text-align: center;
                    height: 16px;
                }
                QProgressBar::chunk {
                    background-color: #4a86e8;
                }
            """)
            
            # Set progress based on status
            if status_str == "completed":
                progress_widget.setValue(100)
            elif status_str == "processing":
                # Set a default value for processing if we don't have actual progress
                progress_widget.setValue(50)
            elif status_str == "failed" or status_str == "canceled":
                progress_widget.setValue(0)
                progress_widget.setFormat("Failed")
            else:
                progress_widget.setValue(0)
                
            self.project_table.setCellWidget(row, 4, progress_widget)
            
            # Actions column - placeholder for now
            actions_item = QTableWidgetItem("...")
            self.project_table.setItem(row, 5, actions_item)
        
        # Update queue statistics
        self._update_queue_stats()
        
        # Resize columns to fit content
        self.project_table.resizeColumnsToContents()
        self.project_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    
    def _update_queue_stats(self):
        """Update the queue statistics label."""
        if not hasattr(self, 'project_queue_manager') or not self.project_queue_manager:
            return
            
        stats = self.project_queue_manager.get_queue_status()
        
        total = stats.get("total", 0)
        pending = stats.get("pending", 0)
        completed = stats.get("completed", 0)
        failed = stats.get("failed", 0)
        
        stats_text = f"{total} projects queued ({pending} pending, {completed} completed, {failed} failed)"
        self.queue_stats_label.setText(stats_text)
        
        # Emit signal with stats
        self.queue_status_changed.emit(stats)
    
    def _show_context_menu(self, position):
        """Show context menu for project table rows."""
        menu = QMenu(self)
        
        # Get selected row
        selected_rows = self.project_table.selectionModel().selectedRows()
        if not selected_rows:
            return
            
        row = selected_rows[0].row()
        project_id = self.project_table.item(row, 0).text()
        project = self.project_queue_manager.get_project(project_id)
        if not project:
            return
            
        # Get project status
        status_str = self.project_table.item(row, 2).text().lower()
        
        # Add menu actions based on status
        view_action = menu.addAction("View Details")
        
        # Add edit action only for pending projects
        edit_action = None
        if status_str == "pending":
            edit_action = menu.addAction("Edit Project")
            
        # Add remove action
        remove_action = menu.addAction("Remove Project")
        
        # Add separator
        menu.addSeparator()
        
        # Add move actions
        move_up_action = None
        move_down_action = None
        if row > 0:
            move_up_action = menu.addAction("Move Up")
        if row < self.project_table.rowCount() - 1:
            move_down_action = menu.addAction("Move Down")
        
        # Show menu and get selected action
        action = menu.exec(self.project_table.viewport().mapToGlobal(position))
        
        # Handle selected action
        if action == view_action:
            self._view_project_details(project_id)
        elif edit_action and action == edit_action:
            self._edit_project(project_id)
        elif action == remove_action:
            self._remove_project(project_id)
        elif move_up_action and action == move_up_action:
            self._reorder_project(-1, row)
        elif move_down_action and action == move_down_action:
            self._reorder_project(1, row)
    
    def _view_project_details(self, project_id):
        """View project details."""
        project = self.project_queue_manager.get_project(project_id)
        if not project:
            return
            
        # Create detail dialog
        detail_dialog = QDialog(self)
        detail_dialog.setWindowTitle(f"Project Details: {project.get('name', 'Unnamed')}")
        detail_dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(detail_dialog)
        
        # Project info
        form_layout = QFormLayout()
        
        form_layout.addRow("Project ID:", QLabel(project_id))
        form_layout.addRow("Name:", QLabel(project.get("name", "Unnamed Project")))
        form_layout.addRow("Status:", QLabel(project.get("status", "pending").upper()))
        form_layout.addRow("Files:", QLabel(str(len(project.get("input_files", [])))))
        
        # Add creation time and last updated if available
        if "created_at" in project:
            form_layout.addRow("Created:", QLabel(project["created_at"]))

        # Add output directory
        if "output_dir" in project:
            output_dir_label = QLabel(project["output_dir"])
            output_dir_label.setWordWrap(True)
            form_layout.addRow("Output Directory:", output_dir_label)
        
        layout.addLayout(form_layout)
        
        # Add list of files in project
        if "input_files" in project and project["input_files"]:
            file_list_label = QLabel("Files in project:")
            layout.addWidget(file_list_label)
            
            file_list = QTableWidget()
            file_list.setColumnCount(2)
            file_list.setHorizontalHeaderLabels(["File Name", "Path"])
            file_list.setRowCount(min(len(project["input_files"]), 10))  # Limit to 10 files for display
            
            for i, file_path in enumerate(project["input_files"][:10]):
                file_list.setItem(i, 0, QTableWidgetItem(os.path.basename(file_path)))
                file_list.setItem(i, 1, QTableWidgetItem(file_path))
                
            if len(project["input_files"]) > 10:
                file_list.setRowCount(11)
                file_list.setItem(10, 0, QTableWidgetItem(f"... {len(project['input_files']) - 10} more files"))
                file_list.setItem(10, 1, QTableWidgetItem(""))
                
            file_list.resizeColumnsToContents()
            file_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            file_list.setMaximumHeight(250)
            layout.addWidget(file_list)
        
        # Add results section if available
        if project_id in self.project_queue_manager.results:
            results = self.project_queue_manager.results[project_id]
            
            results_group = QGroupBox("Results")
            results_layout = QFormLayout(results_group)
            
            # Only show results if no errors
            if "error" not in results:
                files_processed = results.get("files_processed", 0)
                results_layout.addRow("Files Processed:", QLabel(str(files_processed)))
                
                if "total_size_reduction_human" in results:
                    results_layout.addRow("Total Size Reduction:", QLabel(results["total_size_reduction_human"]))
                    
                if "average_reduction_percent" in results:
                    percent = results["average_reduction_percent"]
                    results_layout.addRow("Average Reduction:", QLabel(f"{percent:.1f}%"))
                    
                if "processing_time" in results:
                    time_sec = results["processing_time"]
                    results_layout.addRow("Processing Time:", QLabel(f"{time_sec:.2f} seconds"))
            else:
                results_layout.addRow("Error:", QLabel(results["error"]))
                
            layout.addWidget(results_group)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(detail_dialog.accept)
        layout.addWidget(close_button)
        
        detail_dialog.setLayout(layout)
        detail_dialog.exec()
    
    def _edit_project(self, project_id):
        """Edit a project."""
        # For now, just emit the signal to allow parent to handle editing
        self.project_selected.emit(project_id)
    
    def _remove_project(self, project_id):
        """Remove a project from the queue."""
        result = self.project_queue_manager.remove_project(project_id)
        if result:
            logger.info(f"Removed project {project_id} from queue")
            self.refresh_projects()
        else:
            logger.warning(f"Failed to remove project {project_id}")
            QMessageBox.warning(self, "Remove Project", "Failed to remove project from queue.")
    
    def _remove_selected_project(self):
        """Remove the currently selected project."""
        selected_rows = self.project_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Remove Project", "Please select a project to remove.")
            return
            
        row = selected_rows[0].row()
        project_id = self.project_table.item(row, 0).text()
        
        # Confirm removal
        confirm = QMessageBox.question(
            self,
            "Remove Project",
            f"Are you sure you want to remove the selected project?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self._remove_project(project_id)
    
    def _reorder_project(self, direction, selected_row=None):
        """
        Reorder a project in the queue.
        
        Args:
            direction: -1 for up, 1 for down
            selected_row: Row index of the project to move (default: currently selected row)
        """
        # Get selected row if not provided
        if selected_row is None:
            selected_rows = self.project_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.information(self, "Reorder Project", "Please select a project to reorder.")
                return
                
            selected_row = selected_rows[0].row()
        
        # Check if move is valid
        new_position = selected_row + direction
        if new_position < 0 or new_position >= self.project_table.rowCount():
            return
            
        # Get project ID
        project_id = self.project_table.item(selected_row, 0).text()
        
        # Reorder in queue manager
        result = self.project_queue_manager.reorder_project(project_id, new_position)
        if result:
            logger.info(f"Moved project {project_id} from position {selected_row} to {new_position}")
            
            # Refresh table and select the moved row
            self.refresh_projects()
            self.project_table.selectRow(new_position)
        else:
            logger.warning(f"Failed to reorder project {project_id}")
            QMessageBox.warning(self, "Reorder Project", "Failed to reorder project in queue.")
    
    def _clear_queue(self):
        """Clear the entire project queue."""
        # Confirm clearing
        confirm = QMessageBox.question(
            self,
            "Clear Queue",
            "Are you sure you want to clear all projects from the queue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            self.project_queue_manager.clear_queue()
            logger.info("Cleared project queue")
            self.refresh_projects()
    
    def _add_project_dialog(self):
        """Signal that the user wants to add a new project to the queue."""
        # Emit the signal to notify the parent window to start the project creation workflow
        logger.info("Add project requested - emitting signal for project creation workflow")
        self.add_project_requested.emit()
    
    def _toggle_queue_processing(self):
        """Start or pause queue processing."""
        if not self.is_processing:
            self._start_queue()
        else:
            self._pause_queue()
    
    def _start_queue(self):
        """Start processing the queue."""
        # Check if there are pending projects
        stats = self.project_queue_manager.get_queue_status()
        if stats.get("pending", 0) == 0:
            QMessageBox.information(
                self,
                "Start Queue",
                "No pending projects in queue to process."
            )
            return
        
        # Start processing
        success = self.project_manager.start_processing(progress_callback=self._handle_progress_update)
        if success:
            self.is_processing = True
            self.start_queue_button.setText("Pause Queue")
            self.cancel_queue_button.setEnabled(True)
            
            # Disable buttons that would modify the queue
            self.add_project_button.setEnabled(False)
            self.remove_project_button.setEnabled(False)
            self.move_up_button.setEnabled(False)
            self.move_down_button.setEnabled(False)
            self.clear_queue_button.setEnabled(False)
            self.back_button.setEnabled(False)
            
            # Start elapsed time timer
            self.start_time = time.time()
            self.elapsed_timer.start(1000)  # Update every second
            
            logger.info("Started processing project queue")
        else:
            QMessageBox.warning(
                self,
                "Start Queue",
                "Failed to start queue processing. Please check the logs for details."
            )
    
    def _pause_queue(self):
        """Pause queue processing (not implemented yet)."""
        QMessageBox.information(
            self,
            "Pause Queue",
            "Queue pausing is not supported in this version.\n\n"
            "You can cancel the current queue processing."
        )
    
    def _cancel_queue(self):
        """Cancel queue processing."""
        confirm = QMessageBox.question(
            self,
            "Cancel Queue",
            "Are you sure you want to cancel the queue processing?\n\n"
            "The current project will be canceled and you will need to restart the queue.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm == QMessageBox.StandardButton.Yes:
            success = self.project_manager.cancel_processing()
            if success:
                self._on_processing_stopped()
                logger.info("Canceled queue processing")
            else:
                logger.warning("Failed to cancel queue processing")
    
    def _on_processing_stopped(self):
        """Update UI when processing is stopped for any reason."""
        self.is_processing = False
        self.start_queue_button.setText("Start Queue")
        self.cancel_queue_button.setEnabled(False)
        
        # Re-enable buttons
        self.add_project_button.setEnabled(True)
        self.remove_project_button.setEnabled(True)
        self.move_up_button.setEnabled(True)
        self.move_down_button.setEnabled(True)
        self.clear_queue_button.setEnabled(True)
        self.back_button.setEnabled(True)
        
        # Stop elapsed time timer
        self.elapsed_timer.stop()
        
        # Reset progress bars
        self.project_progress_bar.setValue(0)
        self.queue_progress_bar.setValue(0)
        
        # Update current project label
        self.current_project_label.setText("None")
        
        # Refresh projects to show updated statuses
        self.refresh_projects()
    
    def _handle_progress_update(
        self,
        project_id: str,
        project: dict,
        project_progress: float,
        overall_progress: float
    ):
        """
        Handle progress updates from ProjectManager.
        
        This method is called from a background thread, so we emit a signal
        to ensure UI updates happen on the main thread.
        
        Args:
            project_id: ID of the current project
            project: Project dictionary
            project_progress: Progress of the current project (0.0-1.0)
            overall_progress: Overall progress of the queue (0.0-1.0)
        """
        # Get project name
        project_name = project.get("name", "Unnamed Project")
        
        # Emit signal to update UI on main thread
        self.progress_update.emit(project_id, project_name, project_progress, overall_progress)
    
    def _update_ui_progress(
        self,
        project_id: str,
        project_name: str,
        project_progress: float,
        overall_progress: float
    ):
        """
        Update UI components with progress information.
        
        This method is connected to the progress_update signal and runs on the main thread.
        
        Args:
            project_id: ID of the current project
            project_name: Name of the current project
            project_progress: Progress of the current project (0.0-1.0)
            overall_progress: Overall progress of the queue (0.0-1.0)
        """
        # Update current project label
        self.current_project_label.setText(f"{project_name} (ID: {project_id})")
        
        # Update progress bars
        project_progress_int = int(project_progress * 100)
        overall_progress_int = int(overall_progress * 100)
        
        self.project_progress_bar.setValue(project_progress_int)
        self.queue_progress_bar.setValue(overall_progress_int)
        
        # Update project table progress
        for row in range(self.project_table.rowCount()):
            if self.project_table.item(row, 0).text() == project_id:
                progress_widget = self.project_table.cellWidget(row, 4)
                if progress_widget:
                    progress_widget.setValue(project_progress_int)
                break
        
        # Update remaining time estimate
        if self.start_time > 0 and overall_progress > 0.01:
            elapsed_seconds = time.time() - self.start_time
            
            # Only estimate if we have enough data (at least 5% progress)
            if overall_progress >= 0.05:
                total_seconds_estimate = elapsed_seconds / overall_progress
                remaining_seconds = total_seconds_estimate - elapsed_seconds
                
                # Format remaining time
                hours, remainder = divmod(remaining_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                remaining_time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
                
                self.remaining_time_label.setText(remaining_time_str)
                
    def _handle_project_complete(self, project_id: str, project: dict, success: bool):
        """
        Handle project completion notification from ProjectManager.
        
        This method is called from a background thread, so we emit a signal
        to ensure UI updates happen on the main thread.
        
        Args:
            project_id: ID of the completed project
            project: Project dictionary
            success: Whether the project completed successfully
        """
        # Get project name
        project_name = project.get('name', 'Unnamed')
        
        # Log completion
        if success:
            logger.info(f"Project {project_id} ({project_name}) completed successfully")
        else:
            logger.warning(f"Project {project_id} ({project_name}) failed")
        
        # Emit signal to update UI on main thread
        self.project_complete.emit(project_id, project_name, success)
    
    def _update_ui_project_complete(self, project_id: str, project_name: str, success: bool):
        """
        Update UI after project completion.
        
        This method is connected to the project_complete signal and runs on the main thread.
        
        Args:
            project_id: ID of the completed project
            project_name: Name of the completed project
            success: Whether the project completed successfully
        """
        # Refresh the project table to show updated statuses
        self.refresh_projects()
        
    def _update_elapsed_time(self):
        """Update the elapsed time label."""
        if self.start_time > 0:
            elapsed_seconds = time.time() - self.start_time
            hours, remainder = divmod(elapsed_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            elapsed_time_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            self.elapsed_time_label.setText(elapsed_time_str)
            
    def reset_panel(self):
        """Reset the panel to its initial state."""
        # Reset processing flags
        self.is_processing = False
        
        # Reset UI elements
        self.start_queue_button.setText("Start Queue")
        self.cancel_queue_button.setEnabled(False)
        
        # Enable all buttons
        self.add_project_button.setEnabled(True)
        self.remove_project_button.setEnabled(True)
        self.move_up_button.setEnabled(True)
        self.move_down_button.setEnabled(True)
        self.clear_queue_button.setEnabled(True)
        self.back_button.setEnabled(True)
        
        # Reset progress bars
        self.project_progress_bar.setValue(0)
        self.queue_progress_bar.setValue(0)
        
        # Reset labels
        self.current_project_label.setText("None")
        self.elapsed_time_label.setText("00:00:00")
        self.remaining_time_label.setText("--:--:--")
        
        # Stop timer
        self.elapsed_timer.stop()
        
        # Refresh projects
        self.refresh_projects()
        
        logger.info("Project queue panel reset")