# 🐍 Python Implementation Guide - Forever Yours Compression

This document provides implementation details and best practices for working with the Forever Yours RAW Compression Tool codebase.

## 📚 Code Structure

The application follows a modular design pattern with clear separation of concerns:

### Core Modules

- **`file_preparation.py`**: Handles scanning directories, validating files, and preparing file paths
- **`video_compression.py`**: Manages FFmpeg interaction, compression settings, and process execution
- **`queue_manager.py`**: Controls the compression queue, file status tracking, and results management

### GUI Components

- **`step1_import.py`**: First step UI for folder selection and file import
- **`step2_convert.py`**: Second step UI for compression settings and execution
- **`step3_results.py`**: Third step UI for displaying compression results and statistics

## 🧠 Key Implementation Details

### Video Compression Process

The compression process is implemented as follows:

1. **File Validation**:
   ```python
   def validate_video_file(file_path: str) -> bool:
       # Check file exists and has valid extension
       # Optionally verify with FFmpeg that file is not corrupted
   ```

2. **Command Generation**:
   ```python
   def build_ffmpeg_command(input_path: str, output_path: str, settings: Optional[Dict] = None) -> List[str]:
       # Construct FFmpeg command with proper parameters
       # Apply all necessary video and audio settings
   ```

3. **Compression Execution**:
   ```python
   def compress_video(input_path: str, output_path: str, settings: Optional[Dict] = None, 
                      progress_callback: Optional[Callable] = None) -> bool:
       # Execute FFmpeg process
       # Monitor progress and provide updates via callback
       # Handle errors and return success/failure
   ```

### Progress Tracking

Real-time progress tracking is implemented by:

1. Parsing FFmpeg output with regex to extract time information:
   ```python
   def parse_progress(line: str, total_duration: float) -> Optional[float]:
       """Extract progress information from FFmpeg output line."""
       time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
       if time_match:
           hours, minutes, seconds = map(float, time_match.groups())
           current_time = hours * 3600 + minutes * 60 + seconds
           progress = min(current_time / total_duration, 1.0)
           return progress
   ```

2. Providing nested progress callbacks:
   - File-level progress
   - Overall queue progress

### Queue Management

The queue system manages multiple files through:

1. **File Status Tracking**:
   ```python
   class QueueStatus(Enum):
       PENDING = "pending"
       PROCESSING = "processing"
       COMPLETED = "completed"
       FAILED = "failed"
       CANCELLED = "cancelled"
   ```

2. **Sequential Processing**:
   ```python
   def process_queue(self, output_dir: Optional[str] = None, 
                   settings: Optional[Dict] = None,
                   progress_callback: Optional[Callable] = None) -> bool:
       # Process each file sequentially
       # Update status as files complete
       # Collect results for reporting
   ```

## 🔄 Signal and Slot Connections

The application uses PyQt's signal and slot mechanism for communication between components:

```python
# In main.py
self.import_panel.files_selected.connect(self.on_files_selected)
self.import_panel.next_clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
self.convert_panel.compression_complete.connect(self.on_compression_complete)
```

## 🧪 Error Handling

Error handling follows these guidelines:

1. **Graceful Failures**:
   - Comprehensive try/except blocks
   - Detailed error logging
   - User-friendly error messages

2. **Process Termination**:
   ```python
   def terminate_current_compression():
       """Safely terminate running compression process."""
       if _current_compression_process is not None:
           _compression_cancelled = True
           _current_compression_process.terminate()
   ```

3. **File Validation Fallbacks**:
   - Files that fail validation can still be added to the queue
   - Runtime errors don't block the entire workflow

## 📊 Results and Statistics

Compression results are calculated and formatted as:

```python
def _calculate_compression_result(self, input_path: str, output_path: str, duration: float) -> Dict:
    """Calculate compression metrics for a file."""
    input_size = os.path.getsize(input_path)
    output_size = os.path.getsize(output_path)
    size_diff = input_size - output_size
    percentage = (size_diff / input_size) * 100 if input_size > 0 else 0
    
    # Return detailed statistics dictionary
```

## 🖌️ UI Best Practices

The user interface follows these patterns:

1. **Three-Step Workflow**:
   - Each step is a distinct panel in a QStackedWidget
   - Navigation controlled by signal emissions

2. **Progress Feedback**:
   - Individual file progress
   - Overall job progress
   - Time remaining estimates
   - Real-time statistics updates

3. **Responsive Design**:
   - QTableWidget for displaying results
   - QProgressBar components for visual feedback
   - Proper layout management for resizable windows

## 🛠️ Testing and Debugging

For development and testing:

1. **Enable Debug Logging**:
   ```python
   from core.log_rotation import get_line_limited_logger
   
   # Get a logger with log rotation (100 lines maximum)
   logger = get_line_limited_logger(
       __name__,
       'logs/compress.log',
       max_lines=100,
       level=logging.DEBUG,  # Change from INFO to DEBUG
       log_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

2. **Monitor Real-Time Output**:
   - Check `logs/compress.log` for detailed operation logs (limited to most recent 100 entries)
   - Use the "Show Log Output" option in the UI during compression

3. **Handling Edge Cases**:
   - Test with very large files
   - Test with short video clips
   - Test with various audio configurations
