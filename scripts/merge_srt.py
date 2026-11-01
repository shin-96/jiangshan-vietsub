#!/usr/bin/env python3
"""Gộp mọi .srt trong 1 thư mục (theo tên file) thành 1 SRT, đánh số lại.

Dùng: python3 scripts/merge_srt.py <thư mục> > merged.srt
"""
import re, sys
from pathlib import Path

CUE = re.compile(r"\d+\n(\d{2}:\d{2}:\d{2},\d{2,3} --> \d{2}:\d{2}:\d{2},\d{2,3})\n(.+?)(?=\n\n|\Z)", re.S)
cues = []
for f in sorted(Path(sys.argv[1]).glob("*.srt")):
    cues += CUE.findall(f.read_text(encoding="utf-8"))
def sec(span):
    h, m, r = span.split(" --> ")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))
cues.sort(key=lambda c: sec(c[0]))
out = [f"{i}\n{span}\n{' '.join(t.split())}\n" for i, (span, t) in enumerate(cues, 1)]
sys.stdout.write("\n".join(out))
