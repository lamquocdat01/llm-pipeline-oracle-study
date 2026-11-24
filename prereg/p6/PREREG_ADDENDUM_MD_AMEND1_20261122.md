# PREREG ADDENDUM — SỬA ĐỔI 1 (MD, P6 · R2-02 · đo bù S3C)

Soạn 22-11-2026 ~09:50 ICT (Claude Code). Sửa mục (a) của `P6/PREREG_ADDENDUM_MD_20261121.md` (commit f931522).
**Phải commit file này cùng mã runner TRƯỚC mọi lời gọi model mới** (kể cả smoke). Bằng chứng: `P6/INCIDENT_S3C_20261122.md`.

## Tự khai
Sửa đổi này viết **sau** khi đã biết năm lượt hỏng đêm 21→22-11 (số item lỗi, thông báo lỗi, giờ) và nguyên nhân hạ tầng,
nhưng **trước** khi có bất kỳ đầu ra hợp lệ nào của các ô M1-2, T1-2, R1-B-2 (ba ô này hiện có 0 lần ok; các item ok lẻ
— 1 item của M1-2_r, 16 item của R1-B-2 — thuộc lượt vô hiệu, không được dùng và không được mở xem để quyết định gì).
Vòng 3 chưa chạy lần nào. **Không tham số gọi nào đổi**: model, digest/trọng số ghim, phiên bản server (A 0.30.10,
B 0.40.16), prompt, temperature, seed, `num_predict`, `num_thread`, BM25 top-k, 40 câu oracle, mỗi lần một lần khởi động
server — giữ nguyên như (a). Mười hai lần ok (G … P1-2) giữ nguyên, không chạy lại.

## (a) Lượt vô hiệu do hạ tầng
Các lượt hỏng trong sự cố ổ đĩa đã ghi ở INCIDENT — **M1-2, M1-2_r, T1-2, T1-2_r, R1-B-2** — là vô hiệu do hạ tầng
(ổ D đầy ⇒ pagefile không nở được ⇒ server trả HTTP 500), không phải "hỏng" theo luật V2-08 (f) và không phải "loại".
Giữ nguyên trong `S3C_20261121_v1.jsonl` / `.manifest.jsonl` (chỉ append, không xoá dòng); **không dùng trong phân tích**
(`p2/s3c.py` `VO_HIEU`; `study/analysis_p6/run_s3c.py` `doc()` loại tường minh).

## (b) Chạy lại
Chạy lại **đúng một lần** mỗi biến thể với tên **M1-2_i, T1-2_i, R1-B-2_i** (`s3c.CHAY_LAI`), cùng biến thể và server với
ô gốc. Sau đó luật "hỏng (> 10 % item lỗi) → `<tên>_r` → hỏng lần hai ⇒ loại" áp lại như cũ (vd. M1-2_i → M1-2_i_r).
Lần `_i`/`_i_r` ok điền vào ô kế hoạch gốc (M1-2, T1-2, R1-B-2) khi phân tích (`s3c.o_ke_hoach`); tổng vẫn 22 ô.
Một biến thể bị loại sau `_i_r` thì không chạy lại nữa (ghi nhận từ manifest, kể cả qua các đêm).

## (c) Kiểm dung lượng trước MỖI lần
Trước mỗi lần (kể cả `_r`): ổ chứa kết quả (D:) trống **≥ 20 GiB** (`shutil.disk_usage`, cùng đơn vị với
`Get-PSDrive D` Free/1GB). Thiếu ⇒ dừng, mã thoát 6, checkpoint; **không tính là lần hỏng**. Nếu dừng ngay trước `_r`
thì lần chạy tiếp theo chỉ chạy `_r` của lần đó (không chạy lại lần đầu). Kiểm RAM (≥ 6 GB, chờ tới 30 phút) và giờ
(dừng trước 08:00) như cũ.

## (d) Thứ tự
Ba lần chạy lại trước, theo thứ tự ô gốc: **M1-2_i, T1-2_i, R1-B-2_i**; rồi **vòng 3 đúng thứ tự xáo đã ghi**
(`random.Random(20261121 + 3)`): **K1-3, M1-3, P2-3, T1-3, C-3, P1-3, R1-B-3** (`s3c.thu_tu_chay()`; `run_s3c.py plan`).

## (e) Không đổi
Không tham số gọi nào đổi (xem Tự khai). Thống kê, luật I1–I5 và ngưỡng của (a) giữ nguyên.

## Thay đổi mã (tối thiểu, cùng commit)
- `study/pipeline2/p2/s3c.py`: `VO_HIEU`, `CHAY_LAI`, `D_TOI_THIEU_GIB`, `o_ke_hoach`, `thu_tu_chay`, `trang_thai_lan`
  (ok / loại / chờ `_r` từ manifest). `thu_tu()` gốc giữ nguyên.
- `study/pipeline2/scripts/run_s3c.py`: `local` chạy theo `thu_tu_chay`, bỏ ô ok hoặc loại, chạy chỉ `_r` khi lần đầu đã
  hỏng; `kiem_dia` trước mỗi lần và trước `_r` (mã 6); `status` đánh dấu VÔ HIỆU + in dung lượng; `smoke` kiểm cả server
  A (C-0) và B (R1-B-0), 2 câu mỗi server, ghi `results/S3C_SMOKE_<ngày>.jsonl` (không thuộc mẫu).
- `study/analysis_p6/run_s3c.py` `doc()`: loại `VO_HIEU`, gom theo `o_ke_hoach` (chỉ đổi cách đặt khoá; không đổi thống kê).
- `study/pipeline2/tests/test_s3c.py`: 7 test offline (thứ tự, tên, trạng thái manifest, `_r` khi chạy tiếp, ngưỡng đĩa).

## Phụ lục A (22-11 ~10:05, sau commit 2baee43, anh Đạt duyệt) — dừng tiến trình con mồ côi
Smoke sau commit 2baee43 (`results/S3C_SMOKE_20261122.jsonl`, không thuộc mẫu) cho thấy: sau `s3.dung_ollama()`,
`llama-server.exe` của server A (`%LOCALAPPDATA%\Programs\Ollama\lib\ollama\`) vẫn sống, tiến trình cha đã chết, giữ
2,18 GB bộ nhớ private (3b); con của B thì tự thoát. `dung_ollama` chỉ kill tên bắt đầu bằng `ollama`. Mỗi lần trên A vì
vậy để lại một tiến trình mồ côi (~2,2 GB với 3b, ~5 GB với 7b). Đêm 21→22-11 có 11 lần trên A trước 01:40 (≈ 27 GB) —
cùng cỡ với mức pagefile nở (INCIDENT mục 4). **Đây là giả thuyết cho nguyên nhân commit cao, chưa chứng minh** (các tiến
trình đã mất khi logoff lúc 08:19). Thay đổi: `run_s3c.dung_con_mo_coi` kill thêm đúng các `llama-server*` nằm dưới thư
mục A hoặc `--zip-dir` (B), gọi qua `dung_het` ở mọi chỗ trước đây gọi `s3.dung_ollama()` (trước mỗi lần khởi động
server, cuối mẻ, khi dừng ở mã 0/3/5/6). `p2/s3.py` không đổi. **Không tham số gọi nào đổi**: server của mỗi lần vẫn
khởi động mới; chỉ bộ nhớ do lần trước bỏ lại được giải phóng. Mười hai lần ok đêm trước chạy khi có các tiến trình mồ
côi này (chúng nhàn rỗi, không phục vụ lời gọi nào, vì cổng 11434 thuộc server mới). Thêm 1 test (`test_s3c.py`, 8 test).

## Ngoài kế hoạch, chưa làm (đề xuất cho anh)
Pagefile hệ thống tự quản nằm trên D và có thể lại nở ~10–15 GB trong đêm. Kiểm (c) chỉ chặn *trước* mỗi lần.
Đặt pagefile cố định hoặc chuyển sang C là thay đổi cấu hình máy (cần khởi động lại) — không làm trong phiên này.
