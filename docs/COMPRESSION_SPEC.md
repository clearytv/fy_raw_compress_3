# 🗜️ Forever Yours – RAW Compression Spec (Final – libx265 Controlled)

## 🎯 Purpose

Compress large Apple ProRes `.mov` wedding video files into **full-resolution H.265 versions** using `libx265`. These files preserve the original quality while achieving predictable, controllable file sizes — unlike Apple's `videotoolbox` which fails to honor bitrate settings.

---

## ✅ Input Expectations

- Format: `.mov` (ProRes 422 HQ or similar)
- Resolution, framerate, bit depth: **preserve exactly**
- **Audio**: Pass through untouched (preserve original codec, bitrate, sample rate, and channels)
- **Filename**: Preserve original filename exactly

---

## 🧪 Output Target

- **Codec**: HEVC (H.265)
- **Encoder**: `libx265` (software)
- **Profile**: Main 10
- **Bitrate**: Constant, target ~24 Mbps
- **Rate Control**: `-b:v` + `-maxrate` + `-bufsize` enforced properly
- **Color Settings**: Rec. 709 (`bt709`)
- **Pixel Format**: `yuv420p10le`
- **Audio**: `copy` (e.g., PCM, AAC — untouched)
- **Tag**: `hvc1` (for Apple compatibility)
- **Faststart**: Yes (for streamable MP4)

---

## 🧾 FFmpeg Command Template (libx265)

```bash
ffmpeg -hide_banner -y \
-i "input.mov" \
-c:v libx265 \
-preset medium \
-x265-params "profile=main10:vbv-maxrate=24000:vbv-bufsize=48000" \
-b:v 24M \
-pix_fmt yuv420p10le \
-color_primaries bt709 -color_trc bt709 -colorspace bt709 \
-tag:v hvc1 \
-movflags +faststart \
-c:a copy \
"output_folder/input.mov"
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
