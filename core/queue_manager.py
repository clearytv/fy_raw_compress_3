#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Queue Manager Module

This module handles the compression queue:
- Managing the list of files to be processed
- Tracking compression status for each file
- Sequential processing of the queue
- Providing status updates to the UI
"""

import os
import logging
import time
from enum import Enum
from typing import List, Dict, Tuple, Optional, Callable

logger = logging.getLogger(__name__)

# Import other core modules
from core.video_compression import compress_video, estimate_file_size


class QueueStatus(Enum):
    """Enum representing the status of a file in the queue."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueueManager:
    """
    Manages the queue of files to be compressed.
    
    Handles tracking file status and processing the queue.
    """
    
    def __init__(self):
        """Initialize an empty compression queue."""
        self.queue = []  # List of file paths
        self.status = {}  # Dictionary mapping file paths to status
        self.results = {}  # Dictionary storing compression results
        self.current_index = -1
        self.is_processing = False
        
        logger.info("Queue manager initialized")
    
    def add_files(self, file_paths: List[str]) -> int:
        """
        Add files to the compression queue.
        
        Args:
            file_paths: List of file paths to add to the queue
            
        Returns:
            Number of files successfully added to the queue
        """
        added_count = 0
        
        for path in file_paths:
            if path not in self.queue and os.path.isfile(path):
                self.queue.append(path)
                self.status[path] = QueueStatus.PENDING
                added_count += 1
        
        logger.info(f"Added {added_count} files to queue")
        return added_count
    
    def remove_file(self, file_path: str) -> bool:
        """
        Remove a file from the queue.
        
        Args:
            file_path: Path of file to remove
            
        Returns:
            True if the file was removed, False otherwise
        """
        if file_path in self.queue:
            self.queue.remove(file_path)
            if file_path in self.status:
                del self.status[file_path]
            if file_path in self.results:
                del self.results[file_path]
            
            logger.info(f"Removed file from queue: {file_path}")
            return True
        
        return False
    
    def clear_queue(self) -> None:
        """Clear all files from the queue."""
        self.queue = []
        self.status = {}
        self.results = {}
        self.current_index = -1
        self.is_processing = False
        
        logger.info("Queue cleared")
    
    def process_queue(
        self,
        output_dir: Optional[str] = None,
        settings: Optional[Dict] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Process all files in the queue.
        
        Args:
            output_dir: Directory to store compressed files
            settings: Compression settings to use
            progress_callback: Callback for progress updates
            
        Returns:
            True if all files were processed successfully, False otherwise
        """
        if self.is_processing:
            logger.warning("Queue is already being processed")
            return False
        
        # Initialize processing
        self.is_processing = True
        self.current_index = 0
        self._cancelled = False
        logger.info("Starting queue processing")
        
        # Track overall success
        all_success = True
        
        try:
            # Process each file sequentially
            while self.current_index < len(self.queue) and not self._cancelled:
                current_file = self.queue[self.current_index]
                
                # Update status to processing
                self.status[current_file] = QueueStatus.PROCESSING
                
                # Generate output filename
                from core.file_preparation import generate_output_filename
                file_output = generate_output_filename(current_file, output_dir)
                
                # Create wrapper for progress updates
                def file_progress_callback(progress: float):
                    # Calculate overall progress by factoring in current file's progress
                    # and position in queue
                    overall_progress = (self.current_index + progress) / len(self.queue)
                    if progress_callback:
                        progress_callback(current_file, overall_progress)
                
                # Process current file
                logger.info(f"Processing file {self.current_index + 1}/{len(self.queue)}: {current_file}")
                
                # Import compression function here to avoid circular imports
                from core.video_compression import compress_video
                start_time = time.time()
                success = compress_video(
                    current_file, file_output, settings, file_progress_callback)
                end_time = time.time()
                
                # Update status and result
                if success:
                    self.status[current_file] = QueueStatus.COMPLETED
                    compression_result = self._calculate_compression_result(current_file, file_output, end_time - start_time)
                    self.results[current_file] = compression_result
                    logger.info(f"Successfully compressed {current_file}")
                else:
                    self.status[current_file] = QueueStatus.FAILED
                    self.results[current_file] = {"error": "Compression failed"}
                    logger.error(f"Failed to compress {current_file}")
                    all_success = False
                
                # Move to next file
                self.current_index += 1
                
                # Update progress
                if progress_callback:
                    overall_progress = self.current_index / len(self.queue)
                    progress_callback(current_file, overall_progress)
                    
            # If cancelled, mark remaining files
            if self._cancelled:
                logger.info("Queue processing was cancelled")
                for i in range(self.current_index, len(self.queue)):
                    file_path = self.queue[i]
                    self.status[file_path] = QueueStatus.CANCELLED
        
        except Exception as e:
            logger.error(f"Error during queue processing: {str(e)}", exc_info=True)
            all_success = False
        
        finally:
            self.is_processing = False
            logger.info("Queue processing completed")
            return all_success
    
    def get_queue_status(self) -> Dict:
        """
        Get the current status of the queue.
        
        Returns:
            Dictionary with queue statistics
        """
        stats = {
            "total": len(self.queue),
            "pending": sum(1 for s in self.status.values() if s == QueueStatus.PENDING),
            "processing": sum(1 for s in self.status.values() if s == QueueStatus.PROCESSING),
            "completed": sum(1 for s in self.status.values() if s == QueueStatus.COMPLETED),
            "failed": sum(1 for s in self.status.values() if s == QueueStatus.FAILED),
            "cancelled": sum(1 for s in self.status.values() if s == QueueStatus.CANCELLED),
        }
        
        return stats
    
    def get_results(self) -> Dict:
        """
        Get the results of the compression process.
        
        Returns:
            Dictionary mapping file paths to compression results
        """
        return self.results
        
    def _calculate_compression_result(self, input_path: str, output_path: str, duration: float) -> Dict:
        """
        Calculate and format the compression results for a file.
        
        Args:
            input_path: Path to the original file
            output_path: Path to the compressed file
            duration: Duration of the compression in seconds
            
        Returns:
            Dictionary with compression results
        """
        result = {}
        
        try:
            # Get file sizes
            input_size = os.path.getsize(input_path)
            output_size = os.path.getsize(output_path)
            
            # Calculate size reduction
            size_diff = input_size - output_size
            percentage = (size_diff / input_size) * 100 if input_size > 0 else 0
            
            # Format sizes
            result["input_size"] = input_size
            result["output_size"] = output_size
            result["size_diff"] = size_diff
            result["reduction_percent"] = percentage
            result["input_path"] = input_path
            result["output_path"] = output_path
            result["duration"] = duration
            
            # Format human-readable sizes
            result["input_size_human"] = self._format_file_size(input_size)
            result["output_size_human"] = self._format_file_size(output_size)
            result["size_diff_human"] = self._format_file_size(size_diff)
            
            logger.info(f"Compression result: {percentage:.1f}% reduction, saved {result['size_diff_human']}")
        
        except Exception as e:
            logger.error(f"Error calculating compression result: {str(e)}")
            result["error"] = str(e)
        
        return result
        
    def cancel_processing(self) -> bool:
        """
        Cancel ongoing queue processing.
        
        Returns:
            True if cancellation was initiated, False if not processing
        """
        if not self.is_processing:
            logger.warning("Cannot cancel: queue is not being processed")
            return False
            
        logger.info("Cancelling queue processing")
        self._cancelled = True
        return True
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted string (e.g., "12.34 MB")
        """
        if size_bytes < 0:
            return "0 B"
        
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        suffix_index = 0
        
        while size_bytes >= 1024 and suffix_index < len(suffixes) - 1:
            size_bytes /= 1024.0
            suffix_index += 1
            
        return f"{size_bytes:.2f} {suffixes[suffix_index]}"