#!/usr/bin/env python3
""" Vá lỗ hổng chép lời: Whisper chạy file dài thỉnh thoảng nuốt mất 15-30s thoại
(VAD/no_speech ở đoạn ồn). Script này tìm khoảng câm >12s trong zh.srt, chép lại
đúng cửa sổ đó bằng file ngắn (đáng tin hơn hẳn), dịch các cue mới và chèn vào
cả zh.srt lẫn vi.srt.

Dùng: .venv/bin/python scripts/06_repair_gaps.py <audio.wav> <zh.srt> <vi.srt>
"""
import json, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

audio, zh_f, vi_f = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
CUE = re.compile(r"\d+\n(\d{2}:\d{2}:\d{2},\d{2,3}) --> (\d{2}:\d{2}:\d{2},\d{2,3})\n(.+?)(?=\n\n|\Z)", re.S)
FILLER = re.compile(r"^[呵嗯哼哈啊嘿嘻呃哦唉哎呀]+[。！？!?~～、…\s]*$")
GLOSS = json.loads(Path("glossary.json").read_text(encoding="utf-8"))

def sec(t):
    h, m, r = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(r.replace(",", "."))

def ts(t):
    return f"{int(t//3600):02d}:{int(t%3600//60):02d}:{t%60:06.3f}".replace(".", ",")

def load(f):
    return [[sec(a), sec(b), " ".join(t.split())] for a, b, t in CUE.findall(f.read_text(encoding="utf-8"))]

def save(f, cues):
    cues.sort(key=lambda c: c[0])
    f.write_text("\n".join(f"{i}\n{ts(s)} --> {ts(e)}\n{t}\n" for i, (s, e, t) in enumerate(cues, 1)),
                 encoding="utf-8")

zh = load(zh_f)
gaps, prev = [], 0.0
for s, e, _ in zh:
    if s - prev > 12:
        gaps.append((prev, s))
    prev = max(prev, e)
print("gaps:", [(f"{a:.0f}-{b:.0f}") for a, b in gaps], flush=True)
if not gaps:
    print("NO GAPS"); sys.exit(0)

from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
PROMPT = "瞎丢丢，长眉道人，沈先生，夏侯琢，高希宁，燕青之，不让江山，大楚，宁国。"
new_zh = []
for a, b in gaps:
    w0, w1 = max(a - 4, 0), b + 4
    wav = f"/tmp/repair-{int(w0)}.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(w0), "-t", str(w1 - w0),
                    "-i", audio, wav], check=True)
    segs, _ = model.transcribe(wav, language="zh", vad_filter=True, word_timestamps=True,
                               initial_prompt=PROMPT)
    # Chia cue theo mốc từ như 02 (tối đa ~3.2s, ngắt ở dấu câu) — không để cue khổng lồ.
    # GS_REPAIR_EXCLUDE="0:43,56:73" — khoảng tuyệt đối không chèn cue (nhạc mở đầu,
    # hoặc vùng đã có bản dịch tay tốt hơn).
    import os
    excl = []
    for r in os.environ.get("GS_REPAIR_EXCLUDE", "").split(","):
        if ":" in r:
            x, y = r.split(":"); excl.append((float(x), float(y)))
    def excluded(gs, ge):
        return any(gs < y and ge > x for x, y in excl)
    for s in segs:
        words = [w for w in (s.words or []) if w.word.strip()]
        if not words:
            t = s.text.strip()
            gs, ge = w0 + s.start, w0 + s.end
            if t and not FILLER.match(t) and ge > a + 1 and gs < b - 0.5 and not excluded(gs, ge):
                new_zh.append([max(gs, a), min(ge, b), t])
            continue
        cur, cs = "", None
        for w in words:
            if cs is None:
                cs = w.start
            cur += w.word
            if w.end - cs >= 3.2 or w.word.strip().endswith(("。", "！", "？", "；", ".", "!", "?", ";")):
                t = cur.strip()
                gs, ge = w0 + cs, w0 + w.end
                if t and not FILLER.match(t) and ge > a + 1 and gs < b - 0.5 and not excluded(gs, ge):
                    new_zh.append([max(gs - 0.15, a), min(ge - 0.05, b), t])
                cur, cs = "", None
        if cur.strip():
            t = cur.strip()
            gs, ge = w0 + cs, w0 + words[-1].end
            if not FILLER.match(t) and ge > a + 1 and gs < b - 0.5 and not excluded(gs, ge):
                new_zh.append([max(gs - 0.15, a), min(ge - 0.05, b), t])
    print(f"gap {a:.0f}-{b:.0f}: +{len(new_zh)} cues tích lũy", flush=True)

if not new_zh:
    print("NO NEW CUES (đúng là đoạn lặng/nhạc)"); sys.exit(0)

def gloss(s):
    for k in sorted(GLOSS, key=len, reverse=True):
        s = s.replace(k, GLOSS[k])
    return s

def translate_blob(blob):
    url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=vi&dt=t&q="
           + urllib.parse.quote(blob))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for att in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
            return "".join(p[0] for p in data[0])
        except Exception as ex:
            print("  retry", att, ex, flush=True); time.sleep(20)
    raise RuntimeError("translate failed")

def translate_lines(texts):
    blob = "\n".join(f"@@{i}@@ {t}" for i, t in enumerate(texts))
    try:
        vi, cur = {}, None
        for line in translate_blob(blob).splitlines():
            line = line.strip()
            if line.startswith("@@") and "@@" in line[2:]:
                head, _, rest = line[2:].partition("@@")
                if head.strip().isdigit():
                    cur = int(head.strip()); vi[cur] = rest.strip(); continue
            if cur is not None:
                vi[cur] = (vi.get(cur, "") + " " + line).strip()
        if len(vi) >= max(1, len(texts) - 1):
            return [vi.get(i, texts[i]) for i in range(len(texts))]
        raise RuntimeError("marker mismatch")
    except Exception:
        if len(texts) == 1:
            return texts
        mid = len(texts) // 2
        return translate_lines(texts[:mid]) + translate_lines(texts[mid:])

texts = [gloss(t) for _, _, t in new_zh]
vi_texts = translate_lines(texts)
new_vi = [[s, e, vt] for (s, e, _), vt in zip(new_zh, vi_texts)]

zh += new_zh
save(zh_f, zh)
vi = load(vi_f)
vi += new_vi
save(vi_f, vi)
print(f"PATCHED: +{len(new_zh)} cues -> {zh_f} & {vi_f}")
