#!/usr/bin/env python3
"""Dịch SRT Trung -> Việt bằng Google Translate free.

- Khóa tên riêng bằng glossary.json TRƯỚC khi dịch (thay chữ Hán bằng tên Hán-Việt Latin,
  Google giữ nguyên đoạn Latin).
- Gộp lô ~40 dòng/lần gọi + ngủ giữa các lô để tránh 429. Lô nào 429 thì chờ 60s thử lại.
- Có cache: chạy lại chỉ dịch phần còn thiếu.

Dùng: .venv/bin/python scripts/03_translate.py zh/ vi/
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

src_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
GLOSS = json.loads(Path("glossary.json").read_text(encoding="utf-8"))

def apply_gloss(s):
    for k in sorted(GLOSS, key=len, reverse=True):
        s = s.replace(k, GLOSS[k])
    return s

def translate_blob(blob):
    url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=zh-CN&tl=vi&dt=t&q="
           + urllib.parse.quote(blob))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            data = json.load(urllib.request.urlopen(req, timeout=30))
            return "".join(p[0] for p in data[0])
        except Exception as e:
            print("  retry", attempt, e, flush=True); time.sleep(20)
    raise RuntimeError("translate failed")

def parse_marked(got, n):
    """Tách kết quả dịch theo marker @@i@@ -> dict {i: text}."""
    vi = {}
    cur = None
    for line in got.splitlines():
        line = line.strip()
        if line.startswith("@@") and "@@" in line[2:]:
            head, _, rest = line[2:].partition("@@")
            if head.strip().isdigit():
                cur = int(head.strip()); vi[cur] = rest.strip(); continue
        if cur is not None:
            vi[cur] = (vi.get(cur, "") + " " + line).strip()
    return vi

def translate_lines(texts):
    """Dịch 1 lô dòng, tự chia nhỏ khi URL quá dài (HTTP 400) hoặc endpoint lỗi.
    Lô 1 dòng mà vẫn lỗi thì trả lại nguyên văn (đã khóa glossary) để pipeline không chết."""
    blob = "\n".join(f"@@{i}@@ {t}" for i, t in enumerate(texts))
    try:
        vi = parse_marked(translate_blob(blob), len(texts))
        if len(vi) >= max(1, len(texts) - 1):
            return [vi.get(i, texts[i]) for i in range(len(texts))]
        raise RuntimeError(f"marker mismatch {len(vi)}/{len(texts)}")
    except Exception as e:
        if len(texts) == 1:
            print("  FALLBACK giữ nguyên văn:", texts[0][:30], "|", e, flush=True)
            return texts
        mid = len(texts) // 2
        print(f"  split {len(texts)} -> {mid}+{len(texts)-mid} ({e})", flush=True)
        return translate_lines(texts[:mid]) + translate_lines(texts[mid:])

CUE = re.compile(r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{2,3} --> \d{2}:\d{2}:\d{2},\d{2,3})\n(.+?)(?=\n\n|\Z)", re.S)

# Quy tắc user chốt 2026-11-01: KHÔNG dịch đoạn hát / nhạc / tiếng tượng thanh
# (hừm, hư hư, ha ha...) — nghe vẫn đoán được, không ảnh hưởng mạch truyện.
# - Tượng thanh: lọc bằng FILLER ở bước chép (02) và lọc lại ở đây cho chắc.
# - Nhạc/hát: không tự nhận diện đáng tin được, nên khai khoảng giờ cụ thể.
#   Hợp tập này: nhạc mở đầu 0-43s (toàn cục). Part nào không phải đầu video
#   thì chỉnh SKIP_RANGES về [] và khai theo giờ của part đó.
FILLER = re.compile(r"^[呵嗯哼哈啊嘿嘻呃哦唉哎呀]+[。！？!?~～、…\s]*$")
# GS_SKIP="0:43" (mặc định, cho phần chứa đầu video) | GS_SKIP="" cho các phần sau
import os
_gs = os.environ.get("GS_SKIP", "0:43")
SKIP_RANGES = [tuple(float(x) for x in r.split(":")) for r in _gs.split(",") if r.strip()] if _gs else []

def span_start(span):
    h, m, rest = span.split(" --> ")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest.replace(",", "."))

def skipped(span, text):
    st = span_start(span)
    return FILLER.match(text.strip()) or any(a <= st < b for a, b in SKIP_RANGES)

for srt in sorted(src_dir.glob("*.srt")):
    out = out_dir / srt.name
    if out.exists():
        print("skip", srt.name); continue
    cues = [c for c in CUE.findall(srt.read_text(encoding="utf-8")) if not skipped(c[1], c[2])]
    texts = [apply_gloss(t.strip().replace("\n", " ")) for _, _, t in cues]
    # Cache theo lô: chạy lại chỉ dịch phần chưa xong (429/timeout không làm mất tiến độ)
    cache_f = out_dir / (srt.name + ".cache.json")
    vi = {}
    if cache_f.exists():
        vi = {int(k): v for k, v in json.loads(cache_f.read_text(encoding="utf-8")).items()}
        print(srt.name, "cache:", len(vi), "cues", flush=True)
    for b in range(0, len(texts), 40):
        if all((b + i) in vi for i in range(min(40, len(texts) - b))):
            continue
        got = translate_lines(texts[b:b+40])
        for i, t in enumerate(got):
            vi[b + i] = t
        cache_f.write_text(json.dumps(vi, ensure_ascii=False), encoding="utf-8")
        print(srt.name, "batch", b, "ok", flush=True); time.sleep(3)
    lines = [f"{i+1}\n{span}\n{vi.get(i, texts[i])}\n" for i, (_, span, _) in enumerate(cues)]
    out.write_text("\n".join(lines), encoding="utf-8")
    print("done", out, flush=True)
print("ALL DONE")
