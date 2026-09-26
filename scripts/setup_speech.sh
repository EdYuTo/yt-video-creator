#!/usr/bin/env bash
# One-time: a private Python env for transcription and face detection.
#   ~/.cache/yt-video-creator/venv  (mlx-whisper on Apple Silicon, faster-whisper elsewhere,
#                                    numpy, opencv-python-headless)
#   ~/.cache/yt-video-creator/yunet.onnx  (OpenCV YuNet face detector, 230 KB)
# Whisper models download from Hugging Face on first use; audio itself never leaves the machine.
# Prints the python path to use for transcribe.py / faces.py.
set -euo pipefail
HOME_DIR="$HOME/.cache/yt-video-creator"
VENV="$HOME_DIR/venv"
mkdir -p "$HOME_DIR"

PY="$(command -v python3.12 || command -v python3.11 || command -v python3)"
if [ ! -x "$VENV/bin/python" ]; then
  "$PY" -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --upgrade pip
if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
  "$VENV/bin/pip" install -q mlx-whisper numpy opencv-python-headless pillow
else
  "$VENV/bin/pip" install -q faster-whisper numpy opencv-python-headless pillow
fi

if [ ! -s "$HOME_DIR/yunet.onnx" ]; then
  curl -fsSL -o "$HOME_DIR/yunet.onnx" \
    https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx
fi
echo "$VENV/bin/python"
