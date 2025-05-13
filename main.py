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

# Set up logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/compress.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import GUI components
from gui.step1_import import ImportPanel
from gui.step2_convert import ConvertPanel
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
        self.resize(800, 600)
        
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
        self.results_panel = ResultsPanel(self)
        
        # Add panels to stacked widget
        self.stacked_widget.addWidget(self.import_panel)
        self.stacked_widget.addWidget(self.convert_panel)
        self.stacked_widget.addWidget(self.results_panel)
        
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
        self.import_panel.next_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        
        # Convert panel signals
        self.convert_panel.compression_complete.connect(self.on_compression_complete)
        self.convert_panel.back_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.convert_panel.next_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        
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
        
    def on_compression_complete(self, results):
        """Handle compression completion from convert panel."""
        logger.info("Main window received compression complete signal")
        
        # Verify that we have valid results before proceeding
        if not results:
            logger.warning("No compression results received, not advancing to results panel")
            return
            
        self.results_panel.set_compression_results(results)
        self.stacked_widget.setCurrentIndex(2)
        
    def reset_workflow(self):
        """Reset the workflow to start a new job."""
        logger.info("Resetting workflow - clearing queue and going to step 1")
        self.queue_manager.clear_queue()
        self.stacked_widget.setCurrentIndex(0)
        logger.info(f"Current index set to {self.stacked_widget.currentIndex()}")


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