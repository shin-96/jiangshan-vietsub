#!/usr/bin/env python3
"""QC nhanh file SRT Việt: đếm cue, tìm cue chứa @@/chữ Trung/mẩu cụt, tìm khoảng câm >12s.

Dùng: python3 scripts/qc_srt.py <vi.srt>
"""
import re, sys

CUE = re.compile(r"\d+\n(\d{2}:\d{2}:\d{2},\d{2,3}) --> (\d{2}:\d{2}:\d{2},\d{2,3})\n(.+?)(?=\n\n|\Z)", re.S)

def sec(t):
    h, m, r = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))

cues = CUE.findall(open(sys.argv[1], encoding="utf-8").read())
print(f"cues: {len(cues)}")
bad = [(a, t) for a, b, t in cues if "@@" in t or re.search(r"[\u4e00-\u9fff]", t)]
print(f"cue chứa @@/chữ Trung: {len(bad)}")
for a, t in bad[:20]:
    print("  ", a, " ".join(t.split())[:70])
prev = None
gaps = []
for a, b, t in cues:
    s = sec(a)
    if prev is not None and s - prev > 12:
        gaps.append((prev, s))
    prev = max(prev or 0, sec(b))
print(f"khoảng câm >12s: {len(gaps)}")
for g0, g1 in gaps[:20]:
    print(f"   {g0:.0f}s -> {g1:.0f}s ({g1-g0:.0f}s)")
