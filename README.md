# Giang Sơn Nhất Quyển — Vietsub (江山一卷 1–60)

Dự án dịch phụ đề tiếng Việt cho hoạt hình cát điêu (沙雕动画) **《江山一卷》**
(tên khác: 《我虾仁不让江山！》, nguyên tác tiểu thuyết 《不让江山》 — *Bất Nhượng Giang Sơn*, tác giả 知白).

Nguồn video: Bilibili `BV1AE421N7MP` — hợp tập 1–60, dài **8 giờ 44 phút**.
Chỉ dịch **phụ đề (.srt)**, không re-upload video. Dùng cho mục đích xem cá nhân.

## Pipeline (3 bước, đều miễn phí)

```bash
# 0. Cài đặt
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
#   + yt-dlp và ffmpeg cài sẵn trong máy

# 1. Tải audio từ Bilibili (chỉ audio ~140MB, không tải cả video 2-3GB)
bash scripts/01_download.sh

# 2. Nghe chép tiếng Trung bằng faster-whisper (CPU chạy được, GPU nhanh hơn nhiều)
.venv/bin/python scripts/02_transcribe.py work/audio.m4a zh/
#   -> zh/part-XXXX.srt (chia theo đoạn 10 phút, chạy tiếp được nếu中断)

# 3. Dịch Trung -> Việt (Google Translate miễn phí, có glossary khóa tên riêng)
.venv/bin/python scripts/03_translate.py zh/ vi/
#   -> vi/part-XXXX.srt
```

## Glossary — vì sao bắt buộc?

Dịch máy thuần dịch tên riêng theo phiên âm pinyin (*Changmei, Xiadiudi…*) hoặc dịch nghĩa đen.
`glossary.json` khóa sẵn tên Hán-Việt trước khi dịch: 长眉道人 → Trường Mi đạo nhân,
瞎丢丢 → Lý Đâu Đâu… Thêm tên mới vào file đó, đừng sửa tay trong SRT.

## Quy tắc phụ đề (user chốt 2026-11-01)

- **Sync:** cue chia theo mốc từng từ (word timestamps), tối đa ~3,2 giây/cue, ngắt ở dấu câu —
  đoạn thoại nhanh thì chữ đổi nhanh theo; mọi cue hiện sớm hơn tiếng 0,15s.
  Không dùng mốc giờ làm tròn tay (bản demo đầu bị trễ chữ chính vì lỗi này).
- **Vị trí khi cháy hardsub:** sub Việt dùng hộp đen nhỏ theo từng cue như fansub thường (KHÔNG kéo dải đen
  ngang cả khung), nhưng **ghim chết một tọa độ** đè thẳng lên hàng sub Trung của gốc bằng thẻ
  `\pos` trong file ASS (sinh từ SRT ở bước cháy) — chuẩn 360p: `\pos(320,317)`, hộp đen mờ 90%;
  bản 720p nhân đôi tọa độ/cỡ chữ. Mép trên của sub luôn ở cùng một y, câu ngắn câu dài
  không nhảy vị trí. Cue dài >52 ký tự phải tách thành 2 cue nối tiếp để không bao giờ xuống 2 dòng
  (xuống dòng là nguyên nhân sub trông như dịch chuyển).
- **Ngữ vực:** dịch sát mức của gốc, kể cả câu chửi tục trong lời thoại — giữ đúng độ tục tương đương
  tiếng Việt, không tự kiểm duyệt cũng không thêm nặng. Dịch máy đôi khi tự làm nhẹ câu tục;
  khi soát phải trả lại đúng mức (vd 放屁 → "nói xàm", 打死你 → "đánh chết ngươi").
- **Không dịch:** đoạn hát/nhạc và tiếng tượng thanh/thán từ (hừm, hư hư, ha ha...) — bỏ hẳn cue.
  Khoảng nhạc khai trong `SKIP_RANGES` ở `scripts/03_translate.py` (hợp tập này: nhạc mở đầu 0–43s);
  tượng thanh được lọc tự động ở cả bước chép (02) lẫn bước dịch (03).

## Chất lượng đã kiểm chứng (sample/)

- Đoạn mẫu 3 phút đầu đã chạy thật: `sample/sample180.zh.json` (bản chép Whisper)
  và `sample/sample_vi_v3.srt` (bản Việt theo mốc từ thật, 0:43–3:05, đã áp 2 quy tắc trên).
- Lời thoại thường: Whisper `base` chép đúng ~85–90%. Lên model `small`/`medium` sẽ tốt hơn.
- Đoạn hát mở đầu + hát tuồng: chép/dịch đều kém — theo quy tắc trên thì bỏ hẳn, không dịch.
- Google Translate free từ IP lạ dễ bị 429: script đã gộp lô + chờ giữa các lô;
  nếu vẫn 429, đổi mạng hoặc gắn key DeepL/LLM ở bước 3 (script hỗ trợ cắm sau).

## Xem phim với phụ đề

Mở video Bilibili/YouTube + file `.srt` tương ứng bằng VLC (kéo thả file sub vào),
hoặc dùng extension tải sub ngoài khi xem trên trình duyệt.
Mốc thời gian của SRT khớp với bản hợp tập Bilibili ở trên.

## Bổ sung 2026-11-02
- Tên nhân vật: BẮT BUỘC dịch Hán-Việt cho dễ nhớ (glossary 52 mục — Cao Hy Ninh, Hạ Hầu Trác...), kể cả danh xưng: sư phụ, tiên sinh, lão gia, phu nhân. Sau khi dịch phải quét lại sub tìm pinyin/tiếng Anh sót (Siye, Qingzhi...) và sửa trước khi cháy.
- Giao file: video ~600MB/phần không tải được qua chat — đóng zip rồi cắt mảnh 50MB (`split -b 50M`), up kho Muse, người dùng ghép bằng `copy /b` trên Windows.
