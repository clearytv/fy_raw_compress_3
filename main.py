#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forever Yours RAW Compression Tool

Main entry point for the video compression application.
This file initializes the GUI and connects core functionality.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import QSettings, Qt
from core.log_rotation import get_line_limited_logger

# Set up logging
os.makedirs('logs', exist_ok=True)
# Use custom line count rotating logger instead of basic config
# This will limit the log file to 100 lines maximum
# Configure the root logger so all modules use this handler by default
root_logger = logging.getLogger() # Get the root logger
get_line_limited_logger(
    None, # Pass None or "" to configure the root logger via our custom function
    'logs/compress.log',
    max_lines=100, # Or a higher number for debugging like 500
    level=logging.INFO,
    log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Get a logger for the current module, which will now use the root's handlers
logger = logging.getLogger(__name__)


# Import GUI components
from gui.step1_import import ImportPanel
from gui.step2_convert import ConvertPanel
from gui.step2b_verify import VerifyPanel # New verification panel
from gui.step3_results import ResultsPanel

# Import core functionality
from core.queue_manager import QueueManager


class MainWindow(QMainWindow):
    """
    Main application window containing the workflow steps.
    Manages navigation between steps and shares data between them.
    """
    
    def __init__(self):
        """Initialize main window with step panels."""
        super().__init__()
        logger.info("Creating main application window")
        
        self.setWindowTitle("Forever Yours Compression")
        
        # Set window to stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        # Initialize with default size if settings don't exist
        self.resize(800, 600)
        
        # Restore window geometry from previous session
        self.restore_window_geometry()
        
        # Create queue manager to share between panels
        self.queue_manager = QueueManager()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create stacked widget to hold step panels
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Create workflow step panels
        self.import_panel = ImportPanel(self)
        self.convert_panel = ConvertPanel(self)
        self.verify_panel = VerifyPanel(self) # Instantiate new panel
        self.results_panel = ResultsPanel(self)
        
        # Add panels to stacked widget
        self.stacked_widget.addWidget(self.import_panel)  # Index 0
        self.stacked_widget.addWidget(self.convert_panel) # Index 1
        self.stacked_widget.addWidget(self.verify_panel)  # Index 2
        self.stacked_widget.addWidget(self.results_panel) # Index 3
        
        # Set queue manager in panels that need it
        self.convert_panel.set_queue_manager(self.queue_manager)
        
        # Connect signals between panels
        self._connect_signals()
        
        # Start with first panel
        self.stacked_widget.setCurrentIndex(0)
        logger.info(f"Starting application with panel index set to {self.stacked_widget.currentIndex()}")
        
    def _connect_signals(self):
        """Connect signals between panels for workflow navigation."""
        # Import panel signals
        self.import_panel.files_selected.connect(self.on_files_selected)
        # self.import_panel.next_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Old direct connection
        self.import_panel.next_clicked.connect(self.go_to_convert_panel) # New method
        
        # Convert panel signals
        # self.convert_panel.compression_complete.connect(self.on_compression_complete) # This might still be useful for logging
        self.convert_panel.verification_needed.connect(self.go_to_verify_panel) # New signal for verification
        self.convert_panel.back_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Corrected: ConvertPanel is index 1
        # self.convert_panel.next_clicked is no longer directly connected here for forward navigation
        
        # Connect the compression_complete signal for logging or data handling if needed
        self.convert_panel.compression_complete.connect(self.on_compression_complete)

        # Verify panel signals
        self.verify_panel.back_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1)) # Back to ConvertPanel (index 1)
        self.verify_panel.next_clicked.connect(self.go_to_results_panel)
        
        # Results panel signals
        self.results_panel.new_job_requested.connect(self.reset_workflow)
        
    def on_files_selected(self, files):
        """Handle files selected from import panel."""
        logger.info(f"Main window received {len(files)} files from import panel")
        
        # Verify that we have valid files before proceeding
        if not files:
            logger.warning("No valid files received, not proceeding to next step")
            return
            
        self.queue_manager.add_files(files)
        self.convert_panel.set_queued_files(files)

    def go_to_convert_panel(self):
        """Transition from Import panel to Convert panel, passing necessary data."""
        parent_folder = self.import_panel.parent_folder
        if parent_folder:
            self.convert_panel.set_parent_folder_path(parent_folder)
            logger.info(f"Passing parent folder path to ConvertPanel: {parent_folder}")
        else:
            logger.warning("No parent folder path available from ImportPanel to pass to ConvertPanel.")
        
        self.stacked_widget.setCurrentIndex(1) # ConvertPanel is index 1

    def go_to_verify_panel(self, main_path, original_path, converted_path):
        """Transition from Convert panel to Verify panel."""
        logger.info(f"Transitioning to Verify Panel. Main: {main_path}, Orig: {original_path}, Conv: {converted_path}")
        if not main_path or not original_path or not converted_path:
            logger.error(f"Cannot go to verify panel, one or more paths are missing. Main='{main_path}', Orig='{original_path}', Conv='{converted_path}'")
            # Optionally show a message to the user
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Path Error", "Cannot proceed to verification due to missing folder path information.")
            return
        self.verify_panel.set_paths(main_path, original_path, converted_path)
        self.stacked_widget.setCurrentIndex(2) # Verify Panel is index 2
        # Verification is triggered by a button inside VerifyPanel now.

    def go_to_results_panel(self):
        """Transition to the Results panel, typically from Verify panel."""
        logger.info("Transitioning to Results Panel.")
        
        parent_folder_path_for_results = self.convert_panel.parent_folder_path
        # Or, if VerifyPanel modifies/confirms the main project path, get it from there:
        # parent_folder_path_for_results = self.verify_panel.main_project_folder_path
        
        if parent_folder_path_for_results:
            self.results_panel.set_parent_folder_path(parent_folder_path_for_results)
            logger.info(f"Passing parent folder path to ResultsPanel: {parent_folder_path_for_results}")
        else:
            logger.warning("No parent folder path available to pass to ResultsPanel.")
        
        # If VerifyPanel generates a summary or status, pass it to ResultsPanel
        # For example:
        # verification_summary = self.verify_panel.get_summary()
        # self.results_panel.set_verification_summary(verification_summary)
        
        # For now, set_compression_results might be less relevant if verification is the primary source of truth
        # self.results_panel.set_compression_results({}) # Pass an empty dict or relevant data
        
        self.stacked_widget.setCurrentIndex(3) # Results Panel is index 3
        
    def on_compression_complete(self, results):
        """
        Handle compression completion from convert panel.
        This signal is emitted by ConvertPanel when its processing queue finishes,
        BEFORE it emits 'verification_needed'.
        Its primary role now is for logging or if any immediate data from 'results'
        (currently an empty dict) needs to be handled.
        Actual navigation to the next step (VerifyPanel) is triggered by 'verification_needed'.
        """
        logger.info(f"Main window received 'compression_complete' signal from ConvertPanel. Results: {results}")
        # No direct navigation from here anymore.
        # ConvertPanel.finish_compression will emit 'verification_needed' if successful,
        # which then calls self.go_to_verify_panel.
        # This method can be used if there's any specific action to take right after
        # the queue_manager finishes, but before verification paths are determined.
        pass

    def reset_workflow(self):
        """Reset the workflow to start a new job."""
        logger.info("Resetting workflow - clearing queue and going to step 1")
        self.queue_manager.clear_queue()
        
        # Reset all panel states
        self.import_panel.reset_panel()
        self.convert_panel.reset_panel()
        if hasattr(self, 'verify_panel'): # Check if verify_panel exists
            self.verify_panel.reset_panel_state()
        self.results_panel.reset_panel()
        
        self.stacked_widget.setCurrentIndex(0)
        logger.info(f"Current index set to {self.stacked_widget.currentIndex()}")
    
    def save_window_geometry(self):
        """Save the window's geometry (size and position)"""
        settings = QSettings("ForeverYours", "CompressionTool")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        logger.info("Saved window geometry and state")
    
    def restore_window_geometry(self):
        """Restore the window's geometry from saved settings"""
        settings = QSettings("ForeverYours", "CompressionTool")
        if settings.contains("geometry"):
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))
            logger.info("Restored window geometry and state from settings")
        else:
            logger.info("No saved window geometry found, using defaults")
    
    def closeEvent(self, event):
        """Override close event to save window geometry before closing"""
        self.save_window_geometry()
        super().closeEvent(event)


def main():
    """
    Initialize and run the application.
    """
    try:
        logger.info("Starting Forever Yours Compression Tool")
        
        # Initialize application
        app = QApplication(sys.argv)
        app.setApplicationName("Forever Yours Compression")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()