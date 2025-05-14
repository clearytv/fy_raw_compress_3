#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log rotation module for Forever Yours RAW Compression Tool.

Provides a custom log handler that keeps the log file to a maximum of 100 lines
by removing oldest entries when adding new ones.
"""

import os
import logging
from collections import deque


class LineCountRotatingFileHandler(logging.FileHandler):
    """
    A custom file handler that rotates logs based on line count.
    
    This handler ensures the log file never exceeds the specified
    maximum number of lines by removing the oldest entries when
    new log messages are added.
    """
    
    def __init__(self, filename, max_lines=100, mode='a', encoding=None):
        """
        Initialize the handler with the specified maximum line count.
        
        Args:
            filename: The log file path
            max_lines: Maximum number of lines to keep in the log file (default: 100)
            mode: File open mode (default: 'a' for append)
            encoding: File encoding (default: system default)
        """
        # Create directory if needed
        log_dir = os.path.dirname(filename)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        self.max_lines = max_lines
        self.line_count = 0
        
        # Initialize with truncate mode first to count lines
        super().__init__(filename, mode='r+' if os.path.exists(filename) else 'w', 
                         encoding=encoding)
        
        # Count lines in existing file if it exists
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            self.count_lines_and_truncate()
        
        # Reopen file in append mode for normal operation
        self.close()
        super().__init__(filename, mode=mode, encoding=encoding)
    
    def count_lines_and_truncate(self):
        """
        Count lines in the existing file and truncate if necessary.
        This is called during initialization to handle existing log files.
        """
        # Read all lines from the file
        self.stream.seek(0)
        lines = self.stream.readlines()
        self.line_count = len(lines)
        
        # If file exceeds max lines, keep only the last max_lines
        if self.line_count > self.max_lines:
            # Truncate file
            self.stream.seek(0)
            self.stream.truncate()
            
            # Write back only the most recent lines
            start_index = self.line_count - self.max_lines
            for line in lines[start_index:]:
                self.stream.write(line)
            
            self.line_count = self.max_lines
    
    def emit(self, record):
        """
        Emit a log record while maintaining the maximum line count.
        
        Args:
            record: The log record to emit
        """
        # Acquire lock to ensure thread safety
        if self.stream is None:
            self.stream = self._open()
            
        # Call parent's emit method to write the record
        super().emit(record)
        
        # Increment line count
        self.line_count += 1
        
        # Check if rotation needed
        if self.line_count > self.max_lines:
            self.rotate()
    
    def rotate(self):
        """
        Rotate the log file by keeping only the most recent entries.
        """
        # Close current stream
        if self.stream:
            self.stream.close()
            self.stream = None
            
        # Read all lines from the file
        with open(self.baseFilename, 'r', encoding=self.encoding) as f:
            lines = f.readlines()
        
        # Keep only the most recent lines
        start_index = len(lines) - self.max_lines
        recent_lines = lines[start_index:]
        
        # Truncate file and write back only the most recent lines
        with open(self.baseFilename, 'w', encoding=self.encoding) as f:
            f.writelines(recent_lines)
        
        # Reopen file and update line count
        self.stream = self._open()
        self.line_count = self.max_lines


def get_line_limited_logger(name, log_file, max_lines=100, level=logging.INFO, 
                           log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'):
    """
    Get a logger with a line count limited file handler.
    
    Args:
        name: Logger name
        log_file: Path to log file
        max_lines: Maximum number of lines to keep in log file
        level: Logging level
        log_format: Log format string
    
    Returns:
        A logger instance with line count rotation
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create line count rotating handler
    handler = LineCountRotatingFileHandler(log_file, max_lines=max_lines)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger