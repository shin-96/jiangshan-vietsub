#!/usr/bin/env python3
"""Chép lời Trung bằng faster-whisper, chia đoạn 10 phút để chạy tiếp được.

Dùng: .venv/bin/python scripts/02_transcribe.py work/audio.wav zh/ [model]
Mặc định model 'base' (nhanh, ~85-90% lời thoại thường). Dùng 'small'/'medium' cho bản chính.
"""
import json, subprocess, sys
from pathlib import Path

src = Path(sys.argv[1]); outdir = Path(sys.argv[2]); model_name = sys.argv[3] if len(sys.argv) > 3 else "base"
outdir.mkdir(parents=True, exist_ok=True)
CHUNK = 600  # giây

dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                     "-of", "csv=p=0", str(src)]))
from faster_whisper import WhisperModel
model = WhisperModel(model_name, device="cpu", compute_type="int8")
PROMPT = "瞎丢丢，长眉道人，沈先生，夏侯琢，高希宁，燕青之，不让江山，大楚，宁国。"

def ts(t):
    return f"{int(t//3600):02d}:{int(t%3600//60):02d}:{t%60:06.3f}".replace(".", ",")

for start in range(0, int(dur), CHUNK):
    name = f"part-{start//CHUNK:04d}"
    srt = outdir / f"{name}.srt"
    if srt.exists():
        print("skip", name); continue
    wav = f"/tmp/gs-{name}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(CHUNK),
                    "-i", str(src), wav], check=True)
    segs, _ = model.transcribe(wav, language="zh", vad_filter=True, word_timestamps=True,
                               initial_prompt=PROMPT)
    # Chia cue theo mốc từ: cue tối đa ~3.2s, ngắt ở dấu câu -> chữ bám sát tiếng,
    # đoạn thoại nhanh thì cue cũng ngắn và đổi nhanh theo. Bỏ cue chỉ toàn
    # tiếng tượng thanh / thán từ (hừm, ha ha, ừ...) vì user chốt không dịch loại này.
    import re
    FILLER = re.compile(r"^[呵嗯哼哈啊嘿嘻呃哦唉哎呀]+[。！？!?~～、…\s]*$")
    cues = []  # (start, end, text) theo giờ cục bộ của chunk
    for s in segs:
        words = [w for w in (s.words or []) if w.word.strip()]
        if not words:  # không có mốc từ thì lấy nguyên segment
            t = s.text.strip()
            if t and not FILLER.match(t):
                cues.append((s.start, s.end, t))
            continue
        cur, cs = "", None
        for w in words:
            if cs is None:
                cs = w.start
            cur += w.word
            long_enough = w.end - cs >= 3.2
            sentence_end = w.word.strip().endswith(("。", "！", "？", "；", ".", "!", "?", ";"))
            if long_enough or sentence_end:
                t = cur.strip()
                if t and not FILLER.match(t):
                    cues.append((cs, w.end, t))
                cur, cs = "", None
        if cur.strip() and not FILLER.match(cur.strip()):
            cues.append((cs, words[-1].end, cur.strip()))
    lines = []
    for i, (cs, ce, t) in enumerate(cues, 1):
        # Dịch mốc về giờ toàn cục + cho chữ hiện sớm hơn tiếng 0.15s (trễ là khó chịu nhất)
        gs = start + max(cs - 0.15, 0)
        ge = start + max(ce - 0.05, cs + 0.35)
        lines.append(f"{i}\n{ts(gs)} --> {ts(ge)}\n{t}\n")
    srt.write_text("\n".join(lines), encoding="utf-8")
    print("done", name, len(lines), "cues", flush=True)
print("ALL DONE")
