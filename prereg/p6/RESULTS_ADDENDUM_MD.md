# RESULTS_ADDENDUM_MD — kết quả P6 addendum (B1, B2, (a) S3C xong) · 21-11 / 24-11-2026

Kế hoạch: `P6/PREREG_ADDENDUM_MD_20261121.md`, commit **f931522** (2026-11-21T09:11:38+07:00). Mọi phân tích dưới đây
chạy SAU mốc đó (B1 09:12, B2 09:13). Số sinh bởi script, không gõ tay:
`study/analysis_p6/out/numbers_p6_b1.json`, `numbers_p6_b2.json` (lệnh ở đầu mỗi script; cần `THS_DATASETS=D:\Datasets`).
Nhãn mọi số: **P6 addendum** (kế hoạch viết sau khi biết kết quả cũ và đọc R2 — không phải phân tích mù).

## B1 — drift / chập chờn / false alarm (study 2, R2-05)

**Kết quả: không có test nào thuộc lớp drift hay "golden lệch" ở bất kỳ ô nào, ở cả hai mức.** Mọi test từng đỏ trên
code không đổi đều có ≥ 2 điểm đổi (chập chờn). Giả thuyết của R2-05 (đỏ bền do golden lỗi thời / dịch vụ hosted đổi)
**bị bác bởi dữ liệu**; luật diễn giải ghi trước (< 50 % lượt đỏ do drift) ⇒ bài viết rằng các báo đỏ này là biến thiên
lần-đến-lần, không phải lệch bền so với golden.

| Ô | Mức | Test chập chờn / 40 | Lượt test-đỏ | Đỏ mỗi lần, golden đăng ký | Luân phiên golden: TB [min, max] | Mọi cặp (190) |
|---|---|---|---|---|---|---|
| route, hosted | decision | 2 | 26 | 0,034 | 0,023 [0,018; 0,034] | 0,023 |
| route, hosted | artefact | 23 | 218 | 0,287 | 0,284 [0,266; 0,318] | 0,284 |
| generate, hosted | decision | 1 | 11 | 0,014 | 0,013 [0,012; 0,014] | 0,013 |
| generate, hosted | artefact | 7 | 66 | 0,087 | 0,090 [0,082; 0,100] | 0,090 |
| generate, local | decision | 3 | 9 | 0,012 | 0,019 [0,012; 0,067] | 0,019 |
| generate, local | artefact | 14 | 33 | 0,043 | 0,075 [0,043; 0,278] | 0,075 |
| classify, hosted | artefact | 2 | 19 | 0,025 | 0,026 [0,025; 0,028] | 0,026 |
| classify hosted dec., classify local, route local, retrieve | cả hai | 0 | 0 | 0 | 0 | 0 |

Đọc: golden đăng ký (lần đầu) không phải lần bất thường — tỉ lệ đỏ mỗi lần của nó nằm trong khoảng luân phiên ở mọi ô
(ở route hosted decision nó là cận trên: 0,034 so với TB 0,023). Với generate local, chọn golden khác có thể cho tới 0,278
(một lần bất thường làm golden). Không điểm đổi nào của lớp drift trùng chuyển đoạn runtime (không có drift).

## B2 — oracle khác và chuẩn ngoài thay thế (study 3, V2-09, study 2; R2-03, R2-04, R2-15)

### B2.4 Chuẩn ngoài thay thế S-F1 (R2-03) — đổi claim

| Số | Trước (chuẩn substring, bài JSS v2.1) | Sau: chuẩn S-F1 (max token-F1 với gold ≥ 0,5) |
|---|---|---|
| Test generate truly changed (lần thay đổi study 3) | 58 (hosted 15, local 43) | **40** (hosted 10, local 30) |
| Decision suite bỏ sót | **10** / 58 (hosted 1, local 9) | **6** / 40 (hosted 1, local 5) |
| Chiều của ca bỏ sót | 1 đúng→sai, 9 sai→đúng | **3 đúng→sai, 3 sai→đúng** (hosted 0/1; local 3/2) |
| Token-F1 < 0,8 (so golden) bắt | 58 / 58 | **37 / 40** (hosted 10/10, local 27/30) |
| Token-F1 < 0,5 bắt | 54 / 58 | 34 / 40 (hosted 8, local 26) |
| Truly changed theo cả hai chuẩn | — | hosted 8, local 24; chỉ substring: 7, 19; chỉ S-F1: 2, 6 |
| Test-lần hai chuẩn bất đồng về tính đúng | — | hosted 61 / 200, local 79 / 320 |

**Claim đổi:** (i) "gần như mọi ca bỏ sót là sai→đúng" chỉ đúng dưới chuẩn substring; dưới S-F1 một nửa là đúng→sai ⇒
bài phải nói chiều của ca bỏ sót **phụ thuộc chuẩn ngoài**. (ii) "token-F1 < 0,8 không bỏ sót ca nào" chỉ đúng dưới chuẩn
substring; dưới S-F1 nó bỏ sót 3/40. (iii) Hai chuẩn bất đồng ở 25–31 % test-lần ⇒ chuẩn ngoài là nguồn bất định lớn;
Threats phải nêu (một người dựng luật, không người chấm thứ hai).

### B2.1–2.2 Đường token-F1 và embedding (generate, chuẩn substring)

Recall / precision trên lần thay đổi study 3; FA = tỉ lệ test đỏ mỗi lần trên 3 control study 3 của nhánh.

| Oracle | Hosted R | Hosted P | Hosted FA | Pinned R | Pinned P | Pinned FA |
|---|---|---|---|---|---|---|
| decision | 0,93 | 0,47 | 0,017 | 0,79 | 0,43 | 0,167 |
| exact match | 1,00 | 0,21 | 0,083 | 1,00 | 0,25 | 0,517 |
| F1 < 0,20 | 0,93 | 1,00 | 0,017 | 0,63 | 0,73 | 0,067 |
| F1 < 0,40 | **1,00** | 1,00 | 0,017 | 0,79 | 0,48 | 0,133 |
| F1 < 0,50 | 1,00 | 0,68 | 0,017 | 0,91 | 0,38 | 0,217 |
| F1 < 0,80 | 1,00 | 0,36 | 0,017 | **1,00** | 0,28 | 0,450 |
| emb < 0,85 | 0,93 | 1,00 | 0,017 | 0,53 | 0,85 | 0,042 |
| emb < 0,90 | 1,00 | 0,94 | 0,017 | 0,65 | 0,54 | 0,125 |
| emb < 0,95 | 1,00 | 0,52 | 0,017 | 0,88 | 0,34 | 0,225 |
| emb < 0,99 | 1,00 | 0,27 | 0,017 | **1,00** | 0,26 | 0,458 |

Toàn lưới (20 τ F1, 21 τ emb) trong `numbers_p6_b2.json`. **Đọc (theo luật 6, không chọn ngưỡng):** ở nhánh hosted,
mọi ngưỡng F1 từ 0,40 tới 0,90 và emb từ 0,90 tới 0,99 đạt recall 1 với FA 0,017 (bằng decision). Ở nhánh pinned
**không ngưỡng nào trong lưới đạt recall 1 với FA dưới 0,45** (F1: nhỏ nhất 0,450 ở τ = 0,80; emb: 0,458 ở 0,99) —
FA của mọi oracle văn bản bám theo dao động nền của control pinned (exact match 0,517). Control V2-09 (sau khởi động
server, cùng 3B): exact match 0,583, decision 0,125, F1<0,8 0,508 — cùng mức.

Study 2 (code không đổi, false alarm mỗi lần): hosted generate exact 0,087, decision 0,014, F1<0,8 0,024, F1<0,5 0,014,
emb<0,9 0,014, emb<0,95 0,024; local generate exact 0,043, decision 0,012, F1<0,8 0,037, emb<0,9 0,012.

### B2.3 Trường JSON (classify, R2-15)

| | Exact match | Trường JSON | Decision |
|---|---|---|---|
| FA mỗi lần, study 2 hosted | 0,025 | **0** | 0 |
| FA mỗi lần, control study 3 hosted | 0,017 | **0** | 0 |
| Lần thay đổi hosted: recall / precision | 1,00 / 0,50 (19 FP) | **1,00 / 1,00** | 1,00 / 1,00 |
| Lần thay đổi local: recall / precision | 1,00 / 1,00 | 1,00 / 0,91 (3 FP) | 1,00 / 1,00 |

So trường JSON sau parse xoá mọi false alarm của exact match ở classify (19 test hosted chỉ khác bọc code fence) — đúng
như R2-15 dự đoán: so sánh exact match trên JSON thô là đối chứng yếu. Ở classify, decision và trường JSON tương đương.

## (a) Đo bù R2-02 — S3C, 22/22 (xong 24-11-2026 17:49)
Kế hoạch: (a) f931522 + sửa đổi 1 (2baee43, phụ lục A f35b649) + sửa đổi 2 (a116649, 24-11 14:52:09). Sự cố ba đêm và
kết cục lượt ban ngày: `P6/INCIDENT_S3C_20261122.md`. Số: `study/analysis_p6/out/numbers_p6_s3c.json`
(`run_s3c.py`, chạy 24-11 sau khi runner dừng hẳn, có embedding). 22/22 ô đủ 40 item, 0 lần hỏng trong lượt cuối;
ô M1-2, T1-2, R1-B-2 lấy từ M1-2_i, T1-2_i, R1-B-2_i. **Không biến thể nào thiếu lần lặp.**

**Nền (I1).** Ba control C-1, C-2, C-3 so với G: 0 test đỏ theo decision, 0 theo exact match, 0 theo mọi ngưỡng token-F1
và embedding ≤ 0,99 — và **giống G từng byte trên 40/40 câu** (decision + artefact thô). Chỉ embedding τₑ = 1,00 đỏ
0,050 mỗi lần (2/40): cos của hai văn bản giống hệt nhau tính ra nhỏ hơn 1 do làm tròn số thực — ngưỡng suy biến, ghi nhận,
không đổi lưới. ⇒ **I1 áp dụng: nền = 0**, mọi test đỏ ở lần thay đổi quy cho thay đổi; I2 không cần (vẫn báo Δ).

**C-3 so với C-1, C-2 (prompt mục C2).** C-1, C-2 chạy đêm 21-11 khi có `llama-server` mồ côi (INCIDENT mục 4); C-3 chạy
24-11 trên máy đã dọn (phụ lục A). Cả ba giống G từng byte ⇒ **không phát hiện khác biệt**; tiến trình mồ côi không để lại
dấu vết đo được trên đầu ra.

**Độ lặp (I4).** Với cả sáu thay đổi, ba lần **giống hệt nhau từng byte trên 40/40 câu** (kể cả T1, temperature 0,8 với
seed 0). Theo I4: ba lần không thêm thông tin độc lập về biến thiên câu trả lời; n hiệu dụng = 40 câu mỗi thay đổi; tỉ lệ
chính báo theo lần đầu (`hieu_dung`), số gộp ba lần (`gop`, k và n nhân 3) chỉ ghi để đối chiếu với kế hoạch, không trình
bày như 120 mẫu. Khoảng bootstrap cụm theo câu giống nhau ở hai cách đếm (mỗi cụm nhân 3).

**Tỉ lệ bỏ sót của decision suite (pinned generate, sau khởi động server, nền 0) — I3:**

| Chuẩn | bỏ sót / truly changed (lần đầu mỗi thay đổi) | Wilson 95 % | bootstrap cụm theo câu (5 seed, rộng nhất) | chiều | gộp 3 lần (đối chiếu) |
|---|---|---|---|---|---|
| substring (`av3.dung`, chính) | **8 / 40 = 0,200** | [0,105; 0,348] | [0,049; 0,381] (18 câu) | 0 đúng→sai, 8 sai→đúng | 24/120 |
| S-F1 (thay thế) | **7 / 31 = 0,226** | [0,114; 0,398] | [0,000; 0,463] (12 câu) | 7 đúng→sai, 0 sai→đúng | 21/93 |

Cận dưới Wilson > 0 ⇒ theo I3 bài báo tỉ lệ và chiều (không viết "không quan sát thấy bỏ sót").
Chiều đảo hoàn toàn giữa hai chuẩn (substring: mọi ca sót là sai→đúng; S-F1: mọi ca sót là đúng→sai) — củng cố claim
Pha 3A "chiều phụ thuộc chuẩn".

**Theo thay đổi (lần đầu; substring truly/sót · S-F1 truly/sót; Δ decision so control, `av3.boot_delta`):**

| Thay đổi | Sub. | S-F1 | dec đỏ | exact đỏ | Δ_dec [95 %] |
|---|---|---|---|---|---|
| Rephrase (P1) | 9 / 3 | 6 / 1 | 12 | 29 | 0,300 [0,150; 0,450] |
| Drop constraint (P2) | 8 / 0 | 6 / 1 | 29 | 33 | 0,725 [0,575; 0,850] |
| Larger model (M1) | 10 / 2 | 7 / 1 | 11 | 32 | 0,275 [0,150; 0,425] |
| Top-3 retrieval (K1) | 6 / 0 | 5 / 1 | 10 | 26 | 0,250 [0,125; 0,400] |
| Temperature 0,8 (T1) | 4 / 1 | 4 / 1 | 8 | 29 | 0,200 [0,075; 0,325] |
| Server 0.40.16 (R1-B) | 3 / 2 | 3 / 2 | 5 | 25 | 0,125 [0,025; 0,250] |
| **Tổng** | **40 / 8** | **31 / 7** | 75 | 174 | |

**Oracle trên cả hai phía (lần đầu, gộp sáu thay đổi; FA = mỗi lần trên 3 control S3C):** decision recall 0,800 (sub.) /
0,774 (S-F1), FA 0; exact match recall 1, precision 0,230, FA 0; token-F1 đạt recall 1 (sub.) từ τ = 0,85 và (S-F1) từ
τ = 0,90, FA 0; embedding đạt recall 1 (sub.) tại τₑ = 0,99, FA 0. ⇒ **Ở điều kiện mỗi lần một server mới, mọi oracle văn
bản có FA 0 trên control**, nên exact match bắt mọi thay đổi không mất false alarm nào.

### Bảng trước/sau (mọi số đổi trong bài)

| Đại lượng | Trước (study 3, 1 lần/thay đổi) | Sau (S3C) | Claim |
|---|---|---|---|
| Bỏ sót decision, pinned, substring | 9 / 43 | 8 / 40 = 0,200 [0,105; 0,348] | "existence result" → **tỉ lệ** với nền sạch; giữ cùng cỡ |
| Bỏ sót decision, pinned, S-F1 | 5 / 30 | 7 / 31 = 0,226 [0,114; 0,398] | như trên |
| Bỏ sót, cả hai nhánh, substring | 10 / 58 | (hosted không đo lại) 10/58 giữ cho study 3 | bài nêu cả hai: study 3 (hai nhánh, 1 lần) và S3C (pinned, nền 0) |
| Chiều ca bỏ sót | sub. 1/9, S-F1 3/3 | sub. 0/8, S-F1 7/0 | "phụ thuộc chuẩn" — **mạnh hơn** |
| Nền control pinned generate (dec / exact, mỗi lần) | 0,167 / 0,517 (study 3); V2-09 0,125 / 0,583 | **0 / 0**, giống G từng byte | **đổi**: biến thiên pinned biến mất khi mỗi lần chạy trên server mới khởi động |
| "pinned: không ngưỡng nào đạt recall 1 dưới FA 0,450" | kết quả âm | ở S3C: exact, F1 ≥ 0,85, emb 0,99 đạt recall 1 với FA 0 | **đổi**: kết quả âm chỉ đúng ở điều kiện study 3 (server chạy liên tục); giữ như kết quả có điều kiện |
| "each change run once" | — | 3 lần, giống từng byte | sửa: lặp không thêm mẫu (I4) |

**Diễn giải (ngoài luật I1–I5, mô tả):** điều kiện khác nhau giữa V2-09 (nền đỏ 5 decision/lần) và S3C (nền 0) là: S3C khởi
động lại server trước MỖI lần và chỉ chạy stage generate; V2-09 khởi động lại một lần rồi chạy golden + control liên tiếp
trên cùng server, ba stage. Cơ chế (trạng thái server/cache, thứ tự yêu cầu) **chưa kiểm** — bài nêu là giả thuyết.

## Lệch kế hoạch (tự khai)
1. Môi trường: biến `THS_DATASETS` của máy trỏ `D:\THS_Datasets` (không có corpus) ⇒ đặt `THS_DATASETS=D:\Datasets`
   khi chạy (vị trí corpus theo `D:\Datasets\README.md`; SHA-256 corpus vẫn được `corpus.nap` kiểm). Không đổi mã.
2. Addendum (c) mục 6 ghi "FA < X" nhưng không cố định X ⇒ báo FA nhỏ nhất tại recall = 1 trên lưới (mô tả), không
   đặt ngưỡng phán quyết.
3. Bản 0.40.16 dùng từ `D:\Datasets\_tools\ollama_0.40.16` (chép từ thư mục cũ, 32 file SHA-256 khớp) thay vì đường dẫn
   mặc định trong runner (scratchpad tạm); truyền bằng `--zip-dir`. Exe SHA-256 ghi vào manifest từng lần.
4. (a) chạy qua ba đêm hỏng do hạ tầng và một lượt ban ngày: sửa đổi 1 (lượt vô hiệu, chạy lại `_i`, kiểm đĩa, dừng
   llama-server mồ côi) và sửa đổi 2 (ngoài khung đêm, chờ server sẵn sàng, hạn 4 h 30, lượt cuối). Không tham số gọi
   nào đổi. Lượt cuối chạy khi người dùng có mặt và có job của đề tài khác (INCIDENT, "Kết cục lượt ban ngày").
5. `run_s3c.py` thêm sau mốc f931522 (24-11, trước khi chạy trên dữ liệu S3C): Δ theo I2 (`boot_delta`), đối chiếu
   10/58, ô thiếu theo biến thể; sau khi thấy I4 (giống từng byte) thêm `hieu_dung` (lần đầu mỗi thay đổi), kiểm giống
   từng byte, ma trận nhầm lẫn gộp lần đầu. Không đổi chuẩn ngoài, ngưỡng hay mẫu số (I5); `gop` theo kế hoạch vẫn in.
