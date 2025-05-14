# 🗜️ Forever Yours – RAW Compression Spec (Final – libx265 CRF Matched to AME)

## 🎯 Purpose

Compress large Apple ProRes `.mov` wedding video files into **full-resolution H.265 versions** using `libx265`, matching the behavior of Adobe Media Encoder (AME). These files preserve the original quality while achieving scene-aware bitrate scaling — just like AME's variable bitrate approach.

---

## ✅ Input Expectations

- Format: `.mov` (ProRes 422 HQ or similar)
- Resolution, framerate, bit depth: **preserve exactly**
- **Audio**: Convert to AAC 320 kbps (to match AME)
- **Filename**: Preserve original filename exactly

---

## 🧪 Output Target

- **Codec**: HEVC (H.265)
- **Encoder**: `libx265` (software)
- **Profile**: Main 10
- **Bitrate Strategy**: CRF-based variable bitrate (targeting AME visual quality)
- **CRF**: `18` (visually lossless / AME equivalent)
- **Color Settings**: Rec. 709 (`bt709`)
- **Pixel Format**: `yuv420p10le`
- **Audio**: AAC 320k (lossy but high-quality, matches AME)
- **Tag**: `hvc1` (for Apple compatibility)
- **Faststart**: Yes (for streamable MP4)

---

## 🧾 FFmpeg Command Template (CRF Based)

```bash
ffmpeg -hide_banner -y \
-i "input.mov" \
-c:v libx265 \
-preset medium \
-crf 18 \
-x265-params "profile=main10" \
-pix_fmt yuv420p10le \
-color_primaries bt709 -color_trc bt709 -colorspace bt709 \
-tag:v hvc1 \
-movflags +faststart \
-c:a aac -b:a 320k \
"output_folder/input.mp4"
```

> ⚠️ **Important**: Replace `input.mov` and output path dynamically in your script. Preserve filenames but change folder as needed.

---

## 🛑 Do Not Apply

- LUTs
- Tone mapping
- Overlays
- Audio filters
- Loudness normalization
- Frame interpolation
- Resolution or framerate changes

---

## 🛠 Goal

Build a batch `.sh` or `.py` script that:
1. Accepts input files or folders
2. Applies the above encoding using `libx265`
3. **Preserves original filename**
4. Outputs to a user-specified or auto-structured folder
