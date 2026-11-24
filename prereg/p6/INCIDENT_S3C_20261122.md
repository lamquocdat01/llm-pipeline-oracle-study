# INCIDENT — đo bù S3C đêm 21→22-11-2026 (bài MD, P6 · R2-02)

Lập 22-11-2026 09:50 ICT (Claude Code). Chỉ đọc log/manifest/Event Log; không lời gọi model, không sửa jsonl/manifest.
Nguyên nhân anh Đạt xác nhận: ổ D hết dung lượng. Bằng chứng dưới đây khớp và chỉ rõ thứ đã chiếm chỗ.

## 1. Trạng thái runner (`run_s3c.py status`, trước khi sửa runner)

```
xong 12/22; còn: ['M1-2', 'T1-2', 'R1-B-2', 'K1-3', 'M1-3', 'P2-3', 'T1-3', 'C-3', 'P1-3', 'R1-B-3']
G ok      2026-11-21T23:00:13 → 23:12:33  0 lỗi  0.30.10
K1-1 ok   23:12:38 → 23:20:58  0  0.30.10
C-1 ok    23:21:00 → 23:34:16  0  0.30.10
P2-1 ok   23:34:19 → 23:48:10  0  0.30.10
M1-1 ok   23:48:24 → 00:15:33  0  0.30.10
P1-1 ok   00:15:38 → 00:28:27  0  0.30.10
R1-B-1 ok 00:28:36 → 00:38:38  0  0.40.16
T1-1 ok   00:38:46 → 00:52:13  0  0.30.10
K1-2 ok   00:52:17 → 01:00:39  0  0.30.10
P2-2 ok   01:00:46 → 01:14:09  0  0.30.10
C-2 ok    01:14:15 → 01:27:27  0  0.30.10
P1-2 ok   01:27:31 → 01:40:06  0  0.30.10
M1-2 hong   01:40:11 → 03:04:55  40 lỗi  0.30.10
M1-2_r hong 03:04:55 → 04:29:36  39 lỗi  0.30.10
T1-2 hong   04:29:42 → 05:54:25  40 lỗi  0.30.10
T1-2_r hong 05:54:25 → 07:19:09  40 lỗi  0.30.10
R1-B-2 hong 07:19:19 → 08:16:31  24 lỗi  0.40.16
```
Mọi lần: `ghim_loi = []` (phiên bản + digest + SHA-256 trọng số khớp), không có `su_co`. RAM trống lúc bắt đầu mỗi lần
9,4–16,6 GB (manifest `ram_trong_gb`) ⇒ RAM vật lý không thiếu; thứ cạn là dung lượng đĩa cho pagefile (mục 3).

## 2. Lỗi nguyên văn của các item hỏng (`S3C_20261121_v1.jsonl`, trường `err`)

| Lần | item lỗi / 40 | thông báo nguyên văn (duy nhất) | mẫu ok/lỗi theo thứ tự item |
|---|---|---|---|
| M1-2   | 40 | `Loi429: HTTP Error 500: Internal Server Error` | 40 × lỗi |
| M1-2_r | 39 | `Loi429: HTTP Error 500: Internal Server Error` | 39 lỗi, item cuối (qid `5ad3a733604f3c001a3feacc`) ok |
| T1-2   | 40 | `Loi429: HTTP Error 500: Internal Server Error` | 40 × lỗi |
| T1-2_r | 40 | `Loi429: HTTP Error 500: Internal Server Error` | 40 × lỗi |
| R1-B-2 | 24 | `Loi429: HTTP Error 500: Internal Server Error` | 24 lỗi đầu, 16 item cuối ok |

(`Loi429` là tên lớp ngoại lệ chung của `goi_co_thu_lai` sau khi hết lượt thử lại; nội dung thật là HTTP 500 từ server
Ollama cục bộ.) Mỗi lần hỏng kéo dài ~85 phút (M1/T1) vì mỗi item chờ hết các lượt thử lại.

## 3. Mốc thời gian ổ D đầy

Nguồn: `Microsoft-Windows-Ntfs/Operational` (ID 142 tóm tắt hằng giờ, ID 141 "disk was full"), System, Application.

| Giờ (ICT) | Sự kiện |
|---|---|
| 21-11 23:17:52 | Ntfs 142 (D:): trống 21 GB |
| 22-11 00:17:54 | Ntfs 142: trống giảm 21 → 11,49 GB trong giờ qua |
| **01:00:46** | **Ntfs 141 — "An operation failed because the disk was full." Process: System; Volume D:; Free 11 659 030 528 B; Requested 13 430 140 928 B; Page file size 30 229 704 704 B** |
| 01:17:55 | Ntfs 142: trống 11,49 → 5,31 GB |
| **01:40:12** | **Application Popup 26: "Windows - Virtual Memory Minimum Too Low : Your system is low on virtual memory. Windows is increasing the size of your virtual memory paging file…"** — 1 s sau khi M1-2 bắt đầu (01:40:11) |
| 02:18:00 | Ntfs 142: trống 5,31 GB → **256 MB** (sàn) |
| 03:18 → 07:18 | Ntfs 142 mỗi giờ: trống 255,9–256 MB (ổ D đầy suốt khung M1-2, M1-2_r, T1-2, T1-2_r) |
| 08:00:08 | `D:\Datasets\move_to_C_20261122.ps1` chạy DRY RUN, ghi `freeD=0.2 GiB` (`MOVE_20261122.log`; log dừng ở dòng AAP_home) |
| 08:00:17 | Application Error 1000/WER BEX64: `llama-server.exe` của 0.40.16 (`D:\Datasets\_tools\ollama_0.40.16\lib\ollama\`) crash `0xc0000409` trong `ucrtbase.dll`, khởi động 08:00:17 và chết ngay (trong R1-B-2) |
| **08:00:36** | **Ntfs 141 lần hai: Free 289 206 272 B; Requested 19 327 635 456 B; Page file size 41 600 036 864 B** |
| 08:00–08:18 | Ntfs 142: trống 0,26 → 5,10 GB (có chỗ được giải phóng) — trùng 16 item cuối của R1-B-2 chạy ok |
| 08:16:31 | R1-B-2 kết thúc: hỏng (24/40) |
| 08:17:45 → 08:19:03 | Kernel-Power 105 (đổi nguồn điện), Winlogon 7002 (logoff), Kernel-Power 187 (tiến trình user-mode gọi `SetSuspendState`), 42 (vào sleep, lý do "Application API") |
| 08:19 | Task `Microduck_P6_S3C` bị kết thúc: Last Result `-2147023829` = `0x8007042B` (tiến trình kết thúc ngang). Vì thế `R1-B-2_r` **không** chạy (không có dòng manifest) và log không có dòng `exit=` |
| 08:49:56 | Resume from hibernate |

**Ollama `server.log`:** không có cho đêm này. Runner khởi động `ollama serve` với stdout/stderr = DEVNULL
(`p2/s3.py` `bat_ollama`), còn `%LOCALAPPDATA%\Ollama\server*.log` chỉ có bản của app tray, mới nhất 07-11-2026.
Thông báo 500 của server vì vậy không có chi tiết phía server; bằng chứng phía hệ điều hành là Ntfs 141 + popup ở trên.

**Log runner:** `study/pipeline2/results/S3C_local_20261121_2255.log` (UTF-16, do `*>>` của PowerShell), 35 dòng, khớp manifest.

## 4. Thứ đã chiếm dung lượng trong khung 01:30–08:20

**`D:\pagefile.sys`** (pagefile hệ thống tự quản — `AutomaticManagedPagefile = True`, nằm trên D).
Hai sự kiện Ntfs 141 cho phép cân bằng chính xác:

| | Page file | D trống | Tổng |
|---|---:|---:|---:|
| 01:00:46 | 30 229 704 704 | 11 659 030 528 | 41 888 735 232 |
| 08:00:36 | 41 600 036 864 | 289 206 272 | 41 889 243 136 |

Pagefile tăng 11 370 332 160 B (≈ 10,6 GiB) đúng bằng phần trống mất đi; mọi ghi khác trên D trong 7 giờ ấy cộng lại
chỉ +0,5 MB. Tức là **toàn bộ dung lượng mất trong khung này là pagefile nở ra**, không phải dataset, log hay file kết quả
(jsonl S3C cả đêm chỉ 210 KB). Phần mất 21 → 11,5 GB trước 01:00 không có cặp số pagefile để cân bằng (chưa chứng minh
được, nhưng cùng chiều). Windows còn đòi nở thêm 13,4 GB (01:00) rồi 19,3 GB (08:00) và bị từ chối vì D đầy ⇒ commit
limit chạm trần ⇒ server Ollama không cấp phát được bộ nhớ khi nạp/chạy model ⇒ HTTP 500.

**Chưa xác định:** tiến trình nào đẩy commit charge lên (không có log commit theo tiến trình; Resource-Exhaustion-Detector
không có sự kiện). RAM vật lý trống ≥ 9,4 GB lúc bắt đầu mỗi lần nên đây là bộ nhớ *commit* (cấp phát chưa dùng), không phải
RAM. Ứng viên, CHƯA kiểm: các tiến trình con của server bị kill mỗi lần (`dung_ollama` chỉ kill tên bắt đầu bằng
`ollama`; runner con của 0.40.16 tên `llama-server.exe`), VM WSL/Cowork (`vmmem` 4 GB private lúc 09:40), cập nhật app
Claude lúc 04:28 (SCM 7045). Hiện tại (09:48): pagefile 25 943 MB, D trống 52 165 132 288 B (48,58 GiB).

**Bổ sung 10:00 (sau smoke 22-11):** đã thấy ứng viên thứ nhất xảy ra thật — sau smoke, `llama-server.exe` của 0.30.10
(PID 29856, khởi động 09:51:58, cha đã chết) còn sống, giữ 2,18 GB private; con của 0.40.16 tự thoát. Suy ra mỗi lần trên
server A đêm qua để lại một tiến trình như vậy (11 lần trước 01:40 ≈ 27 GB commit), khớp cỡ với pagefile nở. Đây vẫn là
**suy luận**, không phải đo đêm qua (mọi tiến trình mất khi logoff 08:19). Xử lý: phụ lục A của sửa đổi 1.

## 5. Toàn vẹn 12 lần ok (G … P1-2)

`S3C_20261121_v1.jsonl`: 210 639 B, kết thúc bằng `\n`, 0 byte NUL, 680 dòng, **0 dòng JSON hỏng**.
Mỗi lần trong G, K1-1, C-1, P2-1, M1-1, P1-1, R1-B-1, T1-1, K1-2, P2-2, C-2, P1-2: **đúng 40 item, 40 ok, 40 qid khác
nhau, 0 artefact rỗng, cùng một tập khoá**. Manifest 17 dòng, đều đọc được. Không cắt dòng.
SHA-256 lúc lập: jsonl `bda0aa0df913a34c5821caefc525a8cfde0192e463e6f37c7b22fe10c453235c`,
manifest `1e6ec079ce7626b9f51da609e14bf1e12e2e5601d50887db8a4d5dee526c7951`.

## 6. Hệ quả

Năm lượt M1-2, M1-2_r, T1-2, T1-2_r, R1-B-2 hỏng do hạ tầng (ổ D đầy ⇒ pagefile không nở được), không phải do biến thể.
Theo luật cũ, M1-2 và T1-2 đã "hỏng hai lần ⇒ loại" và runner cũ sẽ chạy lại chúng lần thứ ba nếu khởi động tiếp
(`da_co()` không ghi nhớ "loại") — cả hai đều trái kế hoạch. Xử lý: sửa đổi kế hoạch
`P6/PREREG_ADDENDUM_MD_AMEND1_20261122.md`, commit trước mọi lời gọi mới.

## Đêm 22→23-11

Lập 23-11-2026 06:40 ICT (Claude Code). Không sửa jsonl/manifest, không đổi tham số, không lời gọi model ngoài smoke.

**Nguyên nhân:** runner dừng ngay ở lần đầu tiên (M1-2_i) vì thiếu corpus `D:\Datasets\pipeline2_corpus\dev-v2.0.json`.
Thư mục `pipeline2_corpus` đã bị chuyển sang `C:\Datasets\pipeline2_corpus` trong đợt dọn ổ D sáng 22-11 **mà không để lại
junction** ở `D:\Datasets` (mọi thư mục ở `C:\Datasets` hiện đều không có junction tương ứng; `D:\Datasets` không có
reparse point nào). Thời điểm chuyển: sau smoke 22-11 10:07–10:09 (corpus còn đọc được trên D) — `LastWriteTime` của
`C:\Datasets\pipeline2_corpus` là 22-11 11:32:16. Đây không phải `move_to_C_20261122.ps1 -Execute`: `MOVE_20261122.log`
chỉ có một lượt DRY RUN 08:00 và `pipeline2_corpus` không nằm trong danh sách ưu tiên của script.

**Bằng chứng** (`study/pipeline2/results/S3C_local_20261122_2255.log`, UTF-16, 5 286 B):
- `[2026-11-22T23:00:01+07:00] bắt đầu đo bù P6 (khung đêm)`
- `[2026-11-22T23:00:33+07:00] khởi động …\Programs\Ollama\ollama.exe → 0.30.10; ghim khớp`
- Traceback `run_s3c.py local → chay_mot → s3.mot_lan → executors.du_lieu → corpus.nap`:
  `FileNotFoundError: [Errno 2] No such file or directory: 'D:\Datasets\pipeline2_corpus\dev-v2.0.json'`
- dòng cuối `exit=1`. Task `Microduck_P6_S3C`: Last Run 22-11 22:55, **Last Result 0** — mã này là của dòng
  `Out-File` cuối `s3c_local_task.ps1`, không phải của runner; chỉ dòng `exit=` trong log là đáng tin.
- Lỗi xảy ra khi nạp dữ liệu, **trước** khi ghi item hay dòng manifest nào ⇒ **0 lời gọi mẫu**. SHA-256 sáng 23-11 trùng
  đúng mục 5: jsonl `bda0aa0d…3235c` (210 639 B), manifest `1e6ec079…7951` (17 dòng). `run_s3c.py status` 23-11:
  `xong 12/22; loại []; còn: M1-2_i, T1-2_i, R1-B-2_i, K1-3, M1-3, P2-3, T1-3, C-3, P1-3, R1-B-3` — không đổi.
- Phụ: vì runner thoát bằng ngoại lệ (không qua `dung_het`), `ollama serve` của 0.30.10 (PID 32528, khởi động
  22-11 23:00:03, cha PID 24260 đã chết, 57 MB private) còn sống tới sáng; không có `llama-server` (model chưa nạp).
  Smoke 23-11 dừng nó qua `dung_het` trước khi khởi động server.

**Khắc phục (23-11 06:25–06:35):**
1. Chép (không junction, không xoá bản C) `C:\Datasets\pipeline2_corpus` → `D:\Datasets\pipeline2_corpus` (2 file,
   4 371 569 B). SHA-256 `dev-v2.0.json` = `80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8` = bản ghim
   `p2/corpus.py`; `DATA_SOURCES.md` trùng bản C.
2. Rà đường dẫn: exe 0.30.10 (`%LOCALAPPDATA%\Programs\Ollama`, sha `e44b55b3f103…`) và 0.40.16
   (`D:\Datasets\_tools\ollama_0.40.16`, sha `4ccefcbfecc5…`), kho model `%USERPROFILE%\.ollama\models` (manifest qwen2.5:3b
   `357c53fb…`, 7b `845dbda0…` khớp ghim; blob trọng số có mặt), `desktop\.venv` — đều không bị đợt chuyển đụng tới.
   Ghi nhận ngoài runner: biến môi trường User `THS_DATASETS = D:\THS_Datasets` (task script tự đặt `D:\Datasets` nên
   runner không bị ảnh hưởng).
3. Smoke 2 câu (file riêng `results/S3C_SMOKE_20261123.jsonl`, không thuộc mẫu) 06:32–06:34: 0.30.10 ghim khớp ok 51 s;
   0.40.16 ghim khớp ok 44 s; 4/4 item ok; sau smoke không còn tiến trình `ollama`/`llama-server` nào.

**Hệ quả:** không có lượt hỏng, không có lượt vô hiệu mới; **không tham số nào đổi** (biến thể, thứ tự, ngưỡng, ghim, seed,
oracle qid giữ nguyên); **không cần sửa đổi kế hoạch** — sửa đổi 1 (2baee43 + phụ lục A f35b649) vẫn áp dụng nguyên
văn cho 10 lần còn lại. Đặt lại task một lần lúc 22:55 23-11 (`P6/SCHEDULE_LOG_20261123.txt`).

## Đêm 23→24-11

Lập 24-11-2026 ~15:00 ICT (Claude Code). Chỉ đọc log/manifest/Event Log; không sửa jsonl/manifest.

**Diễn biến** (`study/pipeline2/results/S3C_local_20261123_2302.log`, UTF-16, 7 178 B, sửa lần cuối 23:24):
- Task `Microduck_P6_S3C` mở lúc **23:02** (tên log `_2302`; lịch 22:55). Dòng đầu của runner
  `[2026-11-23T23:11:56+07:00] bắt đầu đo bù P6 (khung đêm)` — tức ~10 phút chỉ để khởi động Python và nạp module
  (bình thường vài giây), trước cả vòng chờ khung đêm.
- `khoi_dong` → `s3.bat_ollama` (0.30.10): `ollama serve` PID 40924 khởi động **23:19:17** (theo `StartTime` tiến trình),
  `/api/version` trả lời, rồi `s3.kiem_ghim` → `mrunner.thuc.ollama_digest` gọi `/api/tags` với timeout 10 s ⇒
  **`TimeoutError: timed out`**; dòng cuối `exit=1`.
- Lỗi xảy ra **trước** khi ghi item hay dòng manifest nào ⇒ **0 lời gọi mẫu**. SHA-256 24-11 trùng mục 5: jsonl
  `bda0aa0d…3235c`, manifest `1e6ec079…7951` (17 dòng); `run_s3c.py status`: xong 12/22, còn 10, không đổi.
- Vì runner thoát bằng ngoại lệ (không qua `dung_het`), `ollama serve` PID 40924 (cha đã chết, 55 MB private) còn sống
  tới chiều 24-11 — lần thứ hai gặp cùng kiểu mồ côi (xem "Đêm 22→23-11"). Không có `llama-server` (model chưa nạp).

**Thứ làm máy bận: chưa xác định** (tìm ≤ 10 phút). Đã xem: System (không sự kiện 22:50–23:30), Application (chỉ
Security-SPP 16384/16394 lúc 22:57–23:04), Defender/Operational, Kernel-Power Thermal, Resource-Exhaustion-Detector,
Diagnostics-Performance (đều trống), TaskScheduler/Operational (không có sự kiện — log có thể đang tắt), Ntfs 142 lúc
23:00:08 (D trống 34–43 GB — không thiếu đĩa). Ứng viên CHƯA kiểm: đồng bộ OneDrive / Google Drive (OneDrive có
~31 000 s CPU tích luỹ vào chiều 24-11), VM `vmmem` 4 GB, các phiên app Claude. Không có số tải máy lúc 23:02–23:24
(runner chưa ghi CPU % — sửa ở sửa đổi 2 (d)).

**Hệ quả:** không lượt hỏng, không lượt vô hiệu mới, không tham số nào đổi. Đây là đêm thứ ba liên tiếp không có lần ok
nào do hạ tầng (21→22: ổ D đầy; 22→23: thiếu corpus; 23→24: server chưa sẵn sàng trong 10 s). Xử lý:
`P6/PREREG_ADDENDUM_MD_AMEND2_20261124.md` (chạy ban ngày một lượt cuối, chờ server sẵn sàng, `dung_het` khi lỗi,
ghi tải máy, hạn chót).

## Kết cục lượt ban ngày 24-11 (sửa đổi 2, commit a116649 14:52:09)

Smoke 14:52–14:54 (`results/S3C_SMOKE_20261124.jsonl`, không thuộc mẫu): 0.30.10 và 0.40.16 ghim khớp, 4/4 ok. Runner
`local --bo-khung-dem` (`scripts/s3c_now_task.ps1`, log `results/S3C_local_20261124_1454.log`), lượt
`results/S3C_LUOT_20261124.json`: bắt đầu 14:54:39, hạn 19:24:39, **0 sự cố**, kết thúc 17:49:36 "xong mọi lần theo thứ
tự", dòng cuối `exit=0`. Sau lượt: 0 tiến trình `ollama`/`llama-server`. **Đủ 22/22**, không lần nào hỏng, không loại.

| Lần | giờ | item | lỗi | server | CPU % trước | RAM trống trước (GB) |
|---|---|---|---|---|---|---|
| M1-2_i | 14:55:00 – 15:28:26 | 40 | 0 | 0.30.10 | 42.4 | 8.07 |
| T1-2_i | 15:34:31 – 15:47:43 | 40 | 0 | 0.30.10 | 1.8 | 11.0 |
| R1-B-2_i | 15:47:48 – 15:57:47 | 40 | 0 | 0.40.16 | 8.1 | 11.08 |
| K1-3 | 15:57:53 – 16:06:23 | 40 | 0 | 0.30.10 | 6.8 | 10.81 |
| M1-3 | 16:06:30 – 16:33:20 | 40 | 0 | 0.30.10 | 8.7 | 10.76 |
| P2-3 | 16:39:29 – 16:53:07 | 40 | 0 | 0.30.10 | 7.7 | 11.27 |
| T1-3 | 16:53:12 – 17:07:09 | 40 | 0 | 0.30.10 | 8.3 | 11.16 |
| C-3 | 17:07:16 – 17:21:32 | 40 | 0 | 0.30.10 | 14.3 | 11.42 |
| P1-3 | 17:21:37 – 17:36:11 | 40 | 0 | 0.30.10 | 12.6 | 12.49 |
| R1-B-3 | 17:36:16 – 17:49:36 | 40 | 0 | 0.40.16 | 97.8 | 12.75 |

**Tải máy (ghi nhận, không phải điều kiện của kế hoạch gốc):** lượt chạy ban ngày, người dùng có mặt. Khoảng 15:17 thấy
ba job Python của đề tài khác đang chạy (`calibrate_thresholds.py --v4` trên VIRAT, `meva_subset_v4.py --fetch`,
`run_block_v4.py --mock`) — không dừng (không thuộc phiên này); RAM vật lý trống lúc đó 3,8 GB khi 7b đang nạp. CPU
trước R1-B-3 đo 97,8 % (trung bình 3 s, ngay sau khi dọn server cũ) — nguồn chưa xác định. Ngưỡng RAM ≥ 6 GB (available)
không lần nào chặn. Tham số gọi cố định (seed 0, ghim) nên tải máy chỉ ảnh hưởng thời lượng, không được thiết kế để
ảnh hưởng đầu ra; ảnh hưởng của tải lên số học trên CPU là **chưa kiểm**.
SHA-256 sau lượt: jsonl `b2933a65356e9538a4a2f6f5143d2adb7e73fe39e03c671c958d6f07d21ba574`,
manifest `83e9451d6ff23f71f9e13cef2a59c2d68d7a9529db05d032541619e30e8c084d` (27 dòng).
