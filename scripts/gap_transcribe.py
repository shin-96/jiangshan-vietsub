#!/usr/bin/env python3
"""Chép lại các cửa sổ bị Whisper nuốt (dùng khi vá tay, không cần Google).
Dùng: .venv/bin/python scripts/gap_transcribe.py <audio.wav> <start-end,...>
In ra JSON: [{start,end,text}] cue tiếng Trung đã chia theo word-timestamp.
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path
from faster_whisper import WhisperModel

audio, spec = sys.argv[1], sys.argv[2]
PUNCT = "。！？!?；;，,、"
FILLER = re.compile(r"^[呵嗯哼哈啊嘿嘻呃哦唉哎呀]+[。！？!?~～、…\s]*$")
model = WhisperModel("base", device="cpu", compute_type="int8")
out = []
for part in spec.split(","):
    a, b = (float(x) for x in part.split("-"))
    a, b = max(0.0, a - 4), b + 4
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tmp = tf.name
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(a), "-t", str(b - a),
                    "-i", audio, "-ac", "1", "-ar", "16000", tmp], check=True)
    segs, _ = model.transcribe(tmp, language="zh", beam_size=5, word_timestamps=True,
                               vad_filter=True,
                               initial_prompt="长眉道人 李丢丢 夏侯琢 高希宁 燕青之 唐匹敌 沈先生")
    words = [w for s in segs for w in (s.words or [])]
    cur, start = "", None
    for w in words:
        if start is None:
            start = w.start
        cur += w.word
        if w.word.strip().endswith(tuple(PUNCT)) or w.end - start >= 3.2:
            out.append({"start": round(a + start, 2), "end": round(a + w.end, 2),
                        "text": cur.strip()})
            cur, start = "", None
    if cur.strip():
        out.append({"start": round(a + start, 2), "end": round(a + words[-1].end, 2),
                    "text": cur.strip()})
    Path(tmp).unlink(missing_ok=True)
out = [c for c in out if not FILLER.match(c["text"])]
print(json.dumps(out, ensure_ascii=False, indent=1))
