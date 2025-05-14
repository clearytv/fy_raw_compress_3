# 🗜️ Forever Yours – RAW Compression Spec

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
- **Bitrate**: VBR, target 24 Mbps
- **Color Settings**: Rec. 709 (`bt709`)
- **Pixel Format**: `yuv420p10le`
- **Audio**: `copy` (pass-through)
- **Tag**: `hvc1` (for Apple compatibility)
- **Faststart**: Yes (for streamable MP4)

---

## 🧾 FFmpeg Command Template

```bash
ffmpeg -hide_banner -y \
-i "input.mov" \
-c:v hevc_videotoolbox \
-profile:v main10 \
-b:v 24M \
-pix_fmt yuv420p10le \
-color_primaries bt709 -color_trc bt709 -colorspace bt709 \
-tag:v hvc1 \
-movflags +faststart \
-c:a copy \
"output_folder/input.mov"
```

> ⚠️ Note: You should not use `"input.mov"` or `"output_folder/input.mov"` literally. Your script should detect the real input file and dynamically generate the output path to match it — keeping the **original filename exactly the same**, but saving it to the new folder.

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
2. Applies the above encoding
3. **Preserves the original filename**
4. Optionally stores output in a user-selected or auto-structured folder