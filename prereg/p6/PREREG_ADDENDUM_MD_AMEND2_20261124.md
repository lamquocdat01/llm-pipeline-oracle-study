# PREREG ADDENDUM — SỬA ĐỔI 2 (MD, P6 · R2-02 · đo bù S3C) · 24-11-2026

Soạn 24-11-2026 ~15:00 ICT (Claude Code), theo quyết định của anh Đạt 24-11 14:40 (máy đang rảnh, chạy ngay).
Sửa mục (a) của `P6/PREREG_ADDENDUM_MD_20261121.md` (commit f931522) và sửa đổi 1
`P6/PREREG_ADDENDUM_MD_AMEND1_20261122.md` (2baee43 + phụ lục A f35b649). **Commit file này cùng mã runner TRƯỚC mọi
lời gọi model mới (kể cả smoke).** Bằng chứng: `P6/INCIDENT_S3C_20261122.md`, mục "Đêm 23→24-11".

## Tự khai
Viết **sau** ba đêm liền hỏng do hạ tầng (21→22: ổ D đầy, 5 lượt vô hiệu; 22→23: thiếu corpus, 0 lời gọi; 23→24:
server không trả `/api/tags` trong 10 s, 0 lời gọi) và **trước** mọi đầu ra hợp lệ của 10 lần còn lại (M1-2_i, T1-2_i,
R1-B-2_i, K1-3, M1-3, P2-3, T1-3, C-3, P1-3, R1-B-3 — cả 10 hiện có 0 dòng manifest). Mười hai lần ok (G … P1-2) đã biết
từ trước; chưa có phân tích S3C nào được chạy trên chúng (`study/analysis_p6/run_s3c.py` chưa chạy trên dữ liệu S3C).
B1, B2 đã chạy và đã vào bản thảo (Pha 3A, 9d7bbf7).

## (a) Chạy ngoài khung đêm 23:00–08:00 cho lượt này
Cờ `run_s3c.py local --bo-khung-dem`: không chờ khung đêm; hạn 08:00 thay bằng hạn lượt (e)(ii).
Lý do: ba đêm hỏng do hạ tầng, không do thiết kế. Khung đêm chỉ nhằm máy không bận việc khác; điều kiện thay thế:
máy rảnh (không job nặng, không tiến trình ollama/llama-server trước lượt), không chạy pytest/LaTeX/embedding trong
lúc đo, và **ghi tải máy** trước mỗi lần (d). Ban ngày người dùng có thể dùng máy nhẹ; đây là lệch so với điều kiện
đêm của kế hoạch gốc và sẽ được khai trong bài.

## (b) Chờ server sẵn sàng trước khi kiểm ghim
Sau khi khởi động server (`s3.bat_ollama`, như cũ), thử `/api/version` rồi `/api/tags` cho tới khi cả hai trả lời, tối
đa **180 s**, mỗi lần thử timeout **30 s**, nghỉ 5 s giữa các lần (`run_s3c.cho_san_sang`). Vẫn không được ⇒ dừng,
**mã 7**, checkpoint, **không tính là lần hỏng** (không ghi dòng manifest), ghi là một sự cố hạ tầng của lượt (e).
Kiểm ghim (`s3.kiem_ghim`, phiên bản, digest, SHA-256 trọng số) giữ nguyên và vẫn chặn (mã 5) như kế hoạch (a).

## (c) Thoát vì lỗi vẫn dọn server
Mọi ngoại lệ trong `local` ⇒ gọi `dung_het` (dừng `ollama*` và `llama-server*` của A/B — phụ lục A) rồi mới ném lại;
ghi là một sự cố hạ tầng của lượt. Không còn `ollama serve` mồ côi như hai đêm 22→23 và 23→24.

## (d) Ghi tải máy
Trước mỗi lần (sau khi dọn server cũ, trước khi khởi động server mới): `cpu_pct_truoc` (psutil, trung bình 3 s) và
`ram_trong_gb_truoc` vào dòng manifest của lần đó (thêm trường; trường cũ giữ nguyên) và vào log.

## (e) Hạn chót — lượt này là lượt cuối
Lượt bắt đầu khi runner khởi động lần đầu với `--bo-khung-dem`; trạng thái ở `study/pipeline2/results/S3C_LUOT_<ngày>.json`
(bắt đầu, hạn, danh sách sự cố, kết thúc) để khởi động lại runner trong cùng lượt vẫn giữ hạn và số sự cố. Dừng đo khi:
1. đủ 22/22 (hết thứ tự chạy); hoặc
2. quá **4 giờ 30 phút** kể từ lúc bắt đầu lượt — như luật 08:00 cũ, không bắt đầu một lần nếu ước thời gian của nó
   (`s3c.phut_uoc`: M1 45 phút, còn lại 25) vượt hạn; hoặc
3. gặp **sự cố hạ tầng thứ hai** trong lượt. Sự cố hạ tầng = một lần hỏng (> 10 % item lỗi, kể cả `_r`), server không
   sẵn sàng (b), runner thoát vì ngoại lệ (c), hoặc dừng do RAM < 6 GB / D trống < 20 GiB. Sau sự cố thứ nhất (nếu runner
   đã dừng) được khởi động lại runner **một lần** trong cùng lượt, từ checkpoint; sự cố thứ hai ⇒ kết thúc ngay (không
   chạy `_r` còn lại), mã 8.

Sau khi lượt kết thúc: **không đặt thêm lượt nào**. Phân tích trên dữ liệu có được; nêu rõ biến thể nào thiếu lần lặp
(ô kế hoạch nào không có lần ok) trong RESULTS_ADDENDUM và trong bài. Thống kê mục (a) 1–5 tính trên các ô có dữ liệu;
luật I1–I5 giữ nguyên.

## (f) Không đổi
Không tham số gọi nào đổi: model, digest/trọng số ghim, phiên bản server (A 0.30.10, B 0.40.16), prompt, temperature,
seed, `num_predict`, `num_thread`, BM25 top-k, 40 câu oracle, mỗi lần một lần khởi động server, luật hỏng → `_r` → loại.
Thứ tự: **M1-2_i, T1-2_i, R1-B-2_i**, rồi vòng 3 theo thứ tự xáo đã ghi **K1-3, M1-3, P2-3, T1-3, C-3, P1-3, R1-B-3**
(`s3c.thu_tu_chay()`, không đổi).

## (g) B3 không thực hiện
B3 (người chấm tay, `P6/PREREG_ADDENDUM2_MD_ADJUDICATION_20261121.md`) **không thực hiện** trong bài này: chưa có nhãn.
Không mở `out/adjudication_key.json`. Bài giữ hai chuẩn ngoài ngang hàng (substring `av3.dung` và S-F1), một người dựng
luật; không viết gì về chấm tay mù.

## Thay đổi mã (tối thiểu, cùng commit)
- `study/pipeline2/scripts/run_s3c.py`: `cho_san_sang`, `tai_may`, lớp `Luot`, `local` bọc `try` (gọi `dung_het` khi
  ngoại lệ), `_local` (thân cũ + nhánh `--bo-khung-dem`, mã 7/8), `chay_mot(khi_hong=…)`, `status` in trạng thái lượt,
  cờ `--bo-khung-dem` và `--luot`. Không có cờ ⇒ hành vi đêm như cũ (thêm (b), (c), (d)).
- `study/pipeline2/scripts/s3c_now_task.ps1`: chạy `local --bo-khung-dem`, log `results/S3C_local_<ngày_giờ>.log`.
- `study/pipeline2/tests/test_s3c.py`: +5 test offline (chờ sẵn sàng thử lại / hết hạn; hạn 4 h 30 + sự cố thứ hai giữ qua
  khởi động lại; dừng trước `_r` khi sự cố thứ hai; ngoại lệ vẫn `dung_het`) — 13 test.
- `p2/s3.py`, `p2/s3c.py`, `mrunner/` không đổi.

## Mốc
Hash và giờ commit ghi ở `P6/RUN_GUIDE_MD.md` và INCIDENT (một commit không chứa được hash của chính nó).
