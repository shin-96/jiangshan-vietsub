#!/usr/bin/env bash
# Chạy trọn 1 phần 60 phút: chép -> dịch -> sinh ASS -> cháy hardsub.
# Dùng: bash scripts/run_part.sh <số phần 1-9> [model]
# Phần N phủ [ (N-1)*3600 , N*3600 ) giây của hợp tập. File ra: out/GiangSon-P<NN>.mp4
set -euo pipefail
cd "$(dirname "$0")/.."
P=${1:?thiếu số phần}
MODEL=${2:-small}
START=$(( (P-1) * 3600 ))
PAD=$(printf "%02d" "$P")
W="work/part$PAD"
mkdir -p "$W" out

# Tải đúng đoạn của phần bằng --download-sections (tải nguyên file bị CDN Bilibili chặn 567,
# tải theo đoạn thì qua). Video 720p AVC + audio trong cùng 1 lần tải.
END=$((START + 3600))
if [ ! -f "$W/video.mp4" ]; then
  .venv/bin/yt-dlp --no-warnings -f "100048+30216" --download-sections "*$START-$END" \
    -o "$W/video.mp4" "https://www.bilibili.com/video/BV1AE421N7MP/"
fi
LEN=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/video.mp4" | cut -d. -f1)
echo "[P$PAD] start=${START}s len=${LEN}s model=$MODEL"

# 1) Audio của phần từ chính file video đoạn (giọng/tiếng khớp tuyệt đối)
[ -f "$W/audio.wav" ] || ffmpeg -y -v error -i "$W/video.mp4" -ar 16000 -ac 1 "$W/audio.wav"

# 2) Chép lời Trung (chia sẵn 10p, chạy tiếp được)
.venv/bin/python scripts/02_transcribe.py "$W/audio.wav" "$W/zh" "$MODEL"
python3 scripts/merge_srt.py "$W/zh" > "$W/zh.srt"
# Kiểm tra toàn vẹn: gộp mà ra 0 cue là lỗi định dạng, dừng ngay đừng chạy tiếp
NZ=$(grep -c " --> " "$W/zh.srt" || true)
echo "[P$PAD] zh cues: $NZ"
[ "$NZ" -gt 100 ] || { echo "LOI: zh.srt chi co $NZ cue"; exit 1; }

# 3) Dịch -> Việt (chỉ phần 1 mới bỏ 43s nhạc mở đầu)
if [ ! -f "$W/vi/part-0000.srt" ]; then
  mkdir -p "$W/zh_in" "$W/vi"
  cp "$W/zh.srt" "$W/zh_in/part-0000.srt"
  if [ "$P" = "1" ]; then export GS_SKIP="0:43"; else export GS_SKIP=""; fi
  .venv/bin/python scripts/03_translate.py "$W/zh_in" "$W/vi"
fi
# 3.5) Vá lỗ hổng chép lời (Whisper nuốt thoại ở đoạn ồn) + quét artifact
if [ "$P" = "1" ]; then export GS_REPAIR_EXCLUDE="0:43,56:73"; else export GS_REPAIR_EXCLUDE=""; fi
.venv/bin/python scripts/06_repair_gaps.py "$W/audio.wav" "$W/zh.srt" "$W/vi/part-0000.srt" || true
python3 scripts/qc_srt.py "$W/vi/part-0000.srt" || true

cp "$W/vi/part-0000.srt" "$W/vi.srt"
NV=$(grep -c " --> " "$W/vi.srt" || true)
echo "[P$PAD] vi cues: $NV"
[ "$NV" -gt 100 ] || { echo "LOI: vi.srt chi co $NV cue"; exit 1; }

# 4) Sinh ASS ghim tọa độ + 5) cháy hardsub từ video đoạn 720p
python3 scripts/05_ass.py "$W/vi.srt" "$W/vi.ass" 1280 720
NA=$(grep -c "^Dialogue:" "$W/vi.ass" || true)
[ "$NA" -gt 100 ] || { echo "LOI: vi.ass chi co $NA dong thoai"; exit 1; }
ffmpeg -y -v error -i "$W/video.mp4" \
  -vf "ass=$W/vi.ass" -c:v libx264 -preset veryfast -crf 23 -c:a aac "out/GiangSon-P$PAD.mp4"
echo "[P$PAD] DONE -> out/GiangSon-P$PAD.mp4"
