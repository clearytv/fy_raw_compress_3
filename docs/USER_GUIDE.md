# Forever Yours RAW Compression Tool: User Guide

## Table of Contents
- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Detailed Workflow](#detailed-workflow)
  - [Step 1: Import Folder](#step-1-import-folder)
  - [Step 2: Convert Files](#step-2-convert-files)
  - [Step 3: Results](#step-3-results)
- [Compression Settings](#compression-settings)
- [Tips for Optimal Results](#tips-for-optimal-results)
- [Troubleshooting](#troubleshooting)

## Introduction

Forever Yours RAW Compression Tool is designed specifically for wedding videographers who need to compress large RAW video files while maintaining visual quality. The tool leverages Apple's VideoToolbox hardware encoder to create significantly smaller files with the same resolution, frame rate, and audio quality.

## Getting Started

Before using the application, ensure you have:

- A Mac with Apple Silicon (M1/M2/M3) processor
- FFmpeg installed with VideoToolbox support (see README.md for installation)
- Sufficient storage space for both original and compressed files
- Video files in .mov or .mp4 format, preferably in a standard wedding folder structure

To launch the application:

1. Open your terminal
2. Navigate to the application directory
3. Run the command: `python main.py`

## Detailed Workflow

The compression workflow consists of three simple steps:

### Step 1: Import Folder

This first screen allows you to select and validate the source files for compression.

#### Key Features:

- **Folder Selection**: Click the "Browse" button to select the parent folder containing your wedding footage. The tool works best with the standard wedding folder structure (typically 03 MEDIA/01 VIDEO/CAM folders).

- **CAM Folders**: After selecting a folder, the tool automatically scans for and displays any CAM folders found within the structure.

- **Files to Process**: All valid video files (.mov, .mp4) found in the selected folders will be displayed here.

- **Rename Option**: The "Rename '01 VIDEO' folders to '01 VIDEO.old'" checkbox allows you to automatically rename the original folders after compression, keeping your file structure organized.

#### Instructions:

1. Click "Browse" to select your wedding footage parent folder
2. Wait for the scan to complete
3. Review the detected CAM folders and files
4. Decide whether to rename original folders (checked by default)
5. Click "Next" when ready to proceed

### Step 2: Convert Files

This screen manages the compression process itself.

#### Key Features:

- **Files Queued**: Shows all files ready for compression, with estimated size savings.

- **Output Settings**: Select where compressed files will be saved:
  - "Same as source" (default): Places compressed versions alongside originals
  - Custom location: Click "Browse" to select a different output directory

- **Compression Settings**: The "Use recommended compression settings" checkbox ensures optimal quality and file size reduction (recommended for most users).

- **Progress Bars**: During compression, these show both individual file and overall job progress.

- **Time Information**: Shows elapsed time and estimated time remaining.

- **Log Output**: Toggle this option to see detailed technical information during compression.

#### Instructions:

1. Review the queued files
2. Set your output directory if needed (default is same location as source)
3. Keep the recommended compression settings (checked by default)
4. Click "Start Compression" to begin the process
5. Monitor progress through the progress bars
6. Wait for compression to complete
7. Click "Next" to view results

### Step 3: Results

This screen provides detailed information about the compression results.

#### Key Features:

- **Compression Summary**: Shows key statistics:
  - Files Processed: Total number of files compressed
  - Total Time: Total duration of the compression process
  - Space Saved: Total disk space recovered
  - Size Reduction: Overall percentage reduction

- **File Results Table**: Detailed breakdown of each file:
  - Original Size: Size before compression
  - Compressed Size: Size after compression
  - Space Saved: Difference between original and compressed
  - Reduction: Percentage reduction for each file
  - Status: Shows "Completed" or "Failed" for each file

- **Action Buttons**:
  - "Start New Job": Begins a new compression process
  - "Quit": Exits the application

#### Understanding Your Results:

The results screen helps you evaluate the compression effectiveness:

- **Good Results**: Typically show 60-80% size reduction while maintaining quality
- **Expected File Size**: Compressed files are usually 20-40% of the original size
- **Compression Ratio**: The higher the reduction percentage, the better the space savings

## Compression Settings

The Forever Yours RAW Compression Tool uses optimized H.265 (HEVC) settings to achieve the best balance between quality and file size:

| Setting | Value | Purpose |
|---------|-------|---------|
| Codec | HEVC (H.265) | Modern codec with superior compression |
| Encoder | hevc_videotoolbox | Uses Apple Silicon hardware acceleration |
| Profile | Main 10 | Supports 10-bit color depth |
| Quality | 75 (High) | High quality with optimal file size |
| Color Settings | Rec. 709 (bt709) | Standard color space for HD video |
| Pixel Format | yuv420p10le | 10-bit color depth with 4:2:0 chroma subsampling |
| Tag | hvc1 | Ensures compatibility with Apple devices |
| Faststart | Enabled | Allows playback before full download |
| Audio | Copy (passthrough) | Preserves original audio quality |

These settings ensure:
- No visual quality loss compared to original files
- Maximum compatibility with modern devices
- Significant file size reduction
- Fast encoding using hardware acceleration

## Tips for Optimal Results

Follow these guidelines to get the best results from the compression tool:

### Source Files

- **Clean Source Files**: Use original camera files whenever possible
- **Avoid Pre-processed Files**: Compressing already compressed files may reduce quality
- **Folder Structure**: The standard wedding structure (03 MEDIA/01 VIDEO/CAM folders) works best
- **File Formats**: .mov and .mp4 files are fully supported

### Compression Process

- **Disk Space**: Ensure you have at least as much free space as your original files
- **Mac Performance**: Close other intensive applications while compressing
- **Batch Size**: For very large collections, consider breaking the job into multiple batches
- **Output Location**: Saving to a fast SSD will improve performance

### After Compression

- **Verify Results**: Always check a few compressed files to ensure quality meets expectations
- **Backup Original Files**: Keep originals until you've verified the compressed versions
- **Export Reports**: Save reports for client documentation and reference

## Troubleshooting

### Common Issues and Solutions

#### Application Won't Start

- **Python Version**: Ensure you're using Python 3.8 or higher
- **Missing Dependencies**: Try reinstalling requirements with `pip install -r docs/requirements.txt`
- **Permission Issues**: Make sure the application directory is accessible

#### Files Not Detected

- **Incorrect Folder Structure**: Ensure your files are within the expected CAM folders
- **Unsupported Formats**: Only .mov and .mp4 files are supported
- **File Corruption**: Damaged files may not be detected

#### Compression Errors

- **FFmpeg Missing**: Make sure FFmpeg is installed properly with VideoToolbox support
- **Hardware Compatibility**: Verify you're using an Apple Silicon Mac
- **Disk Space**: Ensure sufficient free space on the output drive
- **File Access**: Check that files aren't being used by other applications

#### Poor Compression Results

- **Already Compressed**: Source files may already be heavily compressed
- **Complex Content**: Some footage types (like fast motion) compress less efficiently
- **Short Files**: Very short clips may not show significant size reduction

### Getting Help

If you encounter issues not covered here:

1. Check the application logs in the `logs/compress.log` file (contains the most recent 100 log entries)
2. Take screenshots of any error messages
3. Note the specific steps that led to the issue
4. Contact support with these details

### Recovery Steps

If compression fails midway:

1. The application maintains a record of completed files
2. Failed files are clearly marked in the results
3. You can start a new job to process just the failed files
4. Check the log output for specific error details

## System Requirements

The following Python packages are required to run the application:

```
PyQt6>=6.4.0
psutil>=5.9.0
ffmpeg-python>=0.2.0
```

To install these requirements, run: `pip install -r docs/requirements.txt`