# 🗜️ Forever Yours – RAW Compression Tool

A professional-grade application for compressing large RAW wedding video files into smaller H.265 HEVC versions using Apple's VideoToolbox hardware encoder.

## 📋 Overview

Forever Yours RAW Compression Tool creates archival-quality proxies of your original video files while preserving:
- Original resolution and framerate
- Original audio tracks
- Original visual quality (no effects, color grading, or overlays)

The result is a significantly smaller file that looks and sounds exactly like the original, optimized for storage and playback on modern devices.

## ✨ Key Features

- **Efficient Compression**: Achieve up to 80% file size reduction while maintaining visual quality
- **Hardware Acceleration**: Utilizes Apple Silicon (M1/M2/M3) for fast encoding
- **Batch Processing**: Process multiple files or entire folders at once
- **Wedding-Focused Workflow**: Automatically detects CAM folders within wedding media structure
- **Detailed Statistics**: Track file size savings and compression performance
- **User-Friendly Interface**: Simple three-step workflow with clear progress indicators
- **Export Reports**: Generate detailed compression reports for client documentation

## 🖥️ System Requirements

- **Operating System**: macOS with Apple Silicon (M1/M2/M3) processor
- **Python**: Version 3.8 or higher
- **FFmpeg**: Required for video processing (with VideoToolbox support)
- **Storage**: Sufficient space for both original and compressed files

## 🔧 Installation

### Prerequisites

Before installing the Forever Yours Compression Tool, you need to ensure FFmpeg is properly installed on your system.

#### Install FFmpeg

FFmpeg is required to perform the video compression. The easiest way to install it is using Homebrew:

```bash
brew install ffmpeg
```

Verify your installation:

```bash
ffmpeg -version
```

Ensure the output includes `--enable-videotoolbox` in the configuration options.

### Install the Forever Yours Compression Tool

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/fy_raw_compress.git
   cd fy_raw_compress
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r docs/requirements.txt
   ```

## 🚀 Quick Start Guide

1. **Launch the application**:
   ```bash
   python main.py
   ```

2. **Step 1: Import Folder**
   - Click "Browse" to select a wedding footage folder
   - The tool will scan for video files within CAM folders
   - Review detected files and choose whether to rename original folders

3. **Step 2: Convert Files**
   - Set output directory (optional)
   - Verify compression settings
   - Click "Start Compression"
   - Monitor progress as files are processed

4. **Step 3: Results**
   - Review compression statistics and file size savings
   - Export compression report (optional)
   - Open output folder to access compressed files
   - Start a new job or exit the application

## 🏗️ Project Structure

```
├── main.py                   # Main application entry point
├── gui/                      # User interface components
│   ├── step1_import.py       # File import and validation UI
│   ├── step2_convert.py      # Compression settings and process UI
│   └── step3_results.py      # Results and statistics UI
├── core/                     # Core functionality modules
│   ├── file_preparation.py   # File validation and preparation
│   ├── video_compression.py  # FFmpeg command generation and execution
│   └── queue_manager.py      # Compression queue management
├── logs/                     # Log files
│   └── compress.log          # Application log
├── docs/                     # Documentation files
│   ├── forever_yours_compression_spec.md  # Compression specifications
│   ├── PROJECT_RULES.md       # Development guidelines
│   ├── python_fy_compress_files.md  # Python implementation details
│   ├── requirements.txt       # Python dependencies
│   └── USER_GUIDE.md          # Detailed usage instructions
```

## 🎞️ Compression Details

The tool uses the following FFmpeg settings for optimal compression:

- **Codec**: HEVC (H.265)
- **Encoder**: `hevc_videotoolbox` (Apple Silicon hardware acceleration)
- **Profile**: Main 10
- **Bitrate**: VBR, target 24 Mbps
- **Color Settings**: Rec. 709 (`bt709`)
- **Pixel Format**: `yuv420p10le`
- **Audio**: Original audio preserved (pass-through)
- **Tag**: `hvc1` (for Apple compatibility)
- **Faststart**: Enabled (for streamable MP4)

## 💻 Development Setup

For developers looking to contribute or modify the tool:

1. Fork and clone the repository
2. Install dependencies:
   ```bash
   pip install -r docs/requirements.txt
   ```
3. Run the application in development mode:
   ```bash
   python main.py
   ```

### Development Guidelines

This project follows strict development rules:
- Modular code (max 150 lines per file)
- Single-purpose functions
- Maximum nesting of 2 levels
- Strict separation of UI and core logic
- Comprehensive logging

For detailed development guidelines, see [PROJECT_RULES.md](docs/PROJECT_RULES.md).

## 📄 License

[MIT License](LICENSE) - Copyright (c) 2025 Forever Yours