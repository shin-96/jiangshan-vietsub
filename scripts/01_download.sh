#!/usr/bin/env bash
# Tải audio-only của hợp tập 江山一卷 1-60 từ Bilibili (~140MB, 8h44)
set -euo pipefail
mkdir -p work
yt-dlp -f 30216 -o "work/audio.%(ext)s" "https://www.bilibili.com/video/BV1AE421N7MP/"
ffmpeg -y -v error -i work/audio.m4a -ar 16000 -ac 1 work/audio.wav
echo "OK: work/audio.wav"
