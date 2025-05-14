# 🗜️ Forever Yours – RAW Compression Spec (Updated)

## 🎯 Purpose

Compress large RAW wedding video files into **smaller H.265 HEVC versions** using **Apple's VideoToolbox hardware encoder**. These files are **archival-quality proxies**: no effects, no color grading, no overlays. They must look and sound exactly like the original — just smaller in size.

---

## ✅ Input Expectations

- Format: `.mov`, `.mp4`
- Resolution, framerate, bit depth: **preserve exactly**
- **Audio**: Pass through untouched (preserve original codec, bitrate, sample rate, and channels)
- **Filename**: Preserve original filename exactly

---

## 🧪 Output Target

- **Codec**: HEVC (H.265)
- **Encoder**: `hevc_videotoolbox` (Apple Silicon hardware acceleration)
- **Profile**: Main 10
- **Quality**: High quality (82) using variable bit rate
- **Color Settings**: Rec. 709 (`bt709`)
- **Pixel Format**: `yuv420p10le`
- **Audio**: `copy` (pass-through, e.g. PCM or AAC from source)
- **Tag**: `hvc1` (for Apple compatibility)
- **Faststart**: Yes (for streamable MP4)

---

## 🧾 FFmpeg Command Template

\`\`\`bash
ffmpeg -hide_banner -y \
-i "input.mov" \
-c:v hevc_videotoolbox \
-profile:v main10 \
-q:v 75 \
-pix_fmt yuv420p10le \
-color_primaries bt709 -color_trc bt709 -colorspace bt709 \
-tag:v hvc1 \
-movflags +faststart \
-c:a copy \
"output_folder/input.mov"
\`\`\`

> ⚠️ **Important**: Do **not** use `"input.mov"` or `"output_folder/input.mov"` literally.
>
> Your script should **dynamically detect** the actual input filename and ensure the **output filename is identical**, just saved to a new location. For example:
>
> - **Input**: `/path/to/raw/A001_C001.mov`
> - **Output**: `/converted/A001_C001.mov`

---

## 🛑 Do Not Apply

- LUTs
- Tone mapping
- Overlays (text, image, timecode)
- Loudness normalization
- Audio filters or remapping
- Frame interpolation
- Resolution, framerate, or color space changes

---

## 🛠 Goal

Build a script, CLI tool, or drag-and-drop utility that:
1. Accepts input files or folders
2. Applies the above encoding using Apple’s hardware acceleration
3. **Preserves the original filename**
4. Optionally stores output in a user-selected or auto-structured folder