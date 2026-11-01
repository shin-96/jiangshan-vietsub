#!/usr/bin/env python3
"""Sinh ASS từ SRT để cháy hardsub: sub Việt ghim chết 1 tọa độ đè lên hàng sub Trung.

- Tọa độ chuẩn 360p (640x360): \\pos(320,317), FontSize 17 — tự nhân tỉ lệ theo cỡ khung thật.
- Cue dài >52 ký tự tách thành 2 cue nối tiếp (chia thời lượng theo tỉ lệ ký tự)
  để sub luôn 1 dòng — xuống 2 dòng là nguyên nhân sub trông như nhảy vị trí.
- Hộp đen sau chữ: BorderStyle 3, mờ 90%.

Dùng: python3 scripts/05_ass.py <vi.srt> <out.ass> <width> <height>
"""
import re, sys
from pathlib import Path

src, out, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
CUE = re.compile(r"\d+\n(\d{2}:\d{2}:\d{2},\d{2,3}) --> (\d{2}:\d{2}:\d{2},\d{2,3})\n(.+?)(?=\n\n|\Z)", re.S)

def sec(t):
    h, m, r = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))

def at(t):
    return f"{int(t//3600)}:{int(t%3600//60):02d}:{int(t%60):02d}.{int(round((t%1)*100)):02d}"

cues = []
for a, b, txt in CUE.findall(Path(src).read_text(encoding="utf-8")):
    txt = " ".join(txt.split())
    s, e = sec(a), sec(b)
    if len(txt) > 52:
        words = txt.split()
        mid = len(words) // 2
        for k in range(mid, len(words)):
            if words[k-1].endswith((",", ":", "…", ";")):
                mid = k
                break
        p1, p2 = " ".join(words[:mid]), " ".join(words[mid:])
        cut = s + (e - s) * len(p1) / max(len(txt), 1)
        cues.append((s, cut, p1))
        cues.append((cut, e, p2))
    else:
        cues.append((s, e, txt))

sx, sy = W / 640, H / 360
fs = max(int(17 * sy), 10)
px, py = int(320 * sx), int(317 * sy)
hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: VI,DejaVu Sans,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&HE6000000,0,0,0,0,100,100,0,0,3,1,0,8,10,10,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = [hdr]
for s, e, t in cues:
    t = t.replace("\\", "").replace("{", "").replace("}", "")
    lines.append(f"Dialogue: 0,{at(s)},{at(e)},VI,,0,0,0,,{{\\an8\\pos({px},{py})}}{t}")
Path(out).write_text("\n".join(lines), encoding="utf-8")
print(f"ASS: {len(cues)} cues -> {out} (pos {px},{py}, fs {fs})")
