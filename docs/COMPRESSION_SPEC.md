# 🗜️ Forever Yours – RAW Compression Specification

## 🎯 Purpose

Compress large RAW wedding video files into **smaller H.265 HEVC versions** using **Apple's VideoToolbox hardware encoder**. These files are **archival-quality proxies**: no effects, no color grading, no overlays. They look and sound exactly like the original — just smaller in size.

---

## ✅ Input Expectations

- **Format**: `.mov`, `.mp4`
- **Resolution, framerate, bit depth**: Preserved exactly
- **Audio**: Pass through untouched (preserves original codec, bitrate, sample rate, and channels)
- **Filename**: Preserved exactly (but converted to .mp4 extension for consistency)

---

## 🧪 Output Target

- **Codec**: HEVC (H.265)
- **Encoder**: `hevc_videotoolbox` (Apple Silicon hardware acceleration)
- **Profile**: Main 10
- **Quality**: High quality (80) using variable bit rate
- **Color Settings**: Rec. 709 (`bt709`)
- **Pixel Format**: `yuv420p10le`
- **Audio**: `copy` (pass-through, preserves original audio)
- **Tag**: `hvc1` (for Apple compatibility)
- **Faststart**: Enabled (for streamable MP4)

---

## 🧾 FFmpeg Command Used

```bash
ffmpeg -hide_banner -y \
-i "input.mov" \
-c:v hevc_videotoolbox \
-profile:v main10 \
-q:v 80 \
-pix_fmt yuv420p10le \
-color_primaries bt709 -color_trc bt709 -colorspace bt709 \
-tag:v hvc1 \
-movflags +faststart \
-c:a copy \
"output.mp4"
```

> **Note**: The actual implementation dynamically handles file paths. For example:
>
> - **Input**: `/path/to/raw/A001_C001.mov`
> - **Output**: `/path/to/compressed/A001_C001.mp4`

---

## 🛑 What Is Not Applied

- LUTs or color grading
- Tone mapping
- Overlays (text, image, timecode)
- Loudness normalization
- Audio filters or remapping
- Frame interpolation
- Resolution, framerate, or color space changes

---

## 🛠 Implementation Summary

The Forever Yours RAW Compression Tool provides:

1. User-friendly GUI with a three-step workflow
2. Automatic detection of CAM folders within wedding media structure
3. Hardware-accelerated encoding using Apple's VideoToolbox
4. Detailed compression statistics for each file
5. Batch processing capability for multiple files
6. Export of detailed compression reports

The implementation follows strict development guidelines to ensure maintainability and reliability, including modular code organization, comprehensive logging, and clear separation between UI and core logic.