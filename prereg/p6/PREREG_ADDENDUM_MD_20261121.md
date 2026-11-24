# PREREG ADDENDUM P6 (MD) — đo bù R2-02 và hai phân tích lại B1, B2 · 21-11-2026

Phần BỔ SUNG cho kế hoạch phân tích của study 2/3 (`study/pipeline2/prereg/PREREG_V2.md`, V2-01…V2-09). Không sửa,
không thay bất kỳ luật, dữ liệu hay verdict đã đăng ký nào. Mọi số sinh từ file này mang nhãn **P6 addendum**.

**Thời điểm và tự khai (trước khi chạy):** viết ngày 21-11-2026, SAU khi đã biết mọi kết quả study 2, 3, V2-09 và đã
đọc phản biện R2 (`P5/R2_REVIEW_MD_JSS_20261121.md`). Vì vậy đây không phải kế hoạch "mù"; nó chỉ cố định định nghĩa,
ngưỡng, thứ tự và luật diễn giải TRƯỚC khi chạy các phân tích B1, B2 và TRƯỚC lời gọi model đầu tiên của (a). Commit
chứa file này + mã (`study/pipeline2/p2/s3c.py`, `study/pipeline2/scripts/run_s3c.py`, `study/analysis_p6/`) là mốc.
Thay đổi sau mốc ⇒ ghi ở mục "Lệch kế hoạch" của `P6/RESULTS_ADDENDUM_MD.md`, kèm lý do và thời điểm.

---

## (a) Đo bù R2-02: lặp thay đổi tiêm ở pinned generate, mỗi lần sau một lần khởi động server

**Câu hỏi.** Khi mỗi lần chạy bắt đầu từ một server vừa khởi động (điều kiện mà ở V2-09 cho golden và 3 control khớp
nhau), decision suite bỏ sót bao nhiêu thay đổi tính đúng do mỗi thay đổi tiêm gây ra, và con số đó có lặp lại không?

**Cố định.**
- Nhánh: local (caller-pinned). Stage: **generate** duy nhất. 40 câu oracle (`runner/plan_p2.json` → `mau.oracle_qids`).
- Model: `qwen2.5:3b`, manifest digest `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`,
  weights SHA-256 `5ee4f07cdb9beadbbb293e85803c569b01bd37ed059d2715faa7bb405f31caa6`. M1 dùng `qwen2.5:7b`, digest
  `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, weights `2bada8a7…3730` (ghim `p2/s3.py` `PIN_S3`).
- Server A: Ollama **0.30.10** (bản cài, `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`); server B (chỉ R1-B): **0.40.16**
  bản portable đã dùng ở study 3/V2-09 (đường dẫn và SHA-256 của exe ghi vào manifest từng lần). Runner **từ chối chạy**
  nếu `/api/version` ≠ kỳ vọng hoặc digest/weights lệch (`s3.kiem_ghim`) ⇒ sự cố, dừng toàn bộ.
- Tham số gọi: như study 3 (`s3.local_goi`: temperature của biến thể, seed 0, `num_predict` = `backends.MAX_OUT`,
  `num_thread` = `so_luong()`); prompt = `s3.GOC["generate"]` hoặc của biến thể; BM25 top-k = 5 (K1: 3).
- Sáu thay đổi (đúng định nghĩa `s3.bien_the`): **P1** (Rephrase), **P2** (prompt thay thế), **M1** (model 7b),
  **T1** (temperature 0,8), **K1** (top-3), **R1-B** (server 0.40.16). Một control **C** (prompt gốc, server A).
- **Số lần: 3 mỗi thay đổi, 3 control, 1 golden = 22 lần.** Lý do không chọn 5: thời gian một lần sau khởi động server
  ở study 3/V2-09 là 15–20 phút cho ba stage (generate chiếm phần lớn), M1 khoảng 38 phút ⇒ 5 lần (36 lần chạy) ước
  > 8 giờ máy; 3 lần ước 5–6 giờ, vừa một đêm 23:00–08:00.
- **Thứ tự:** golden G trước. Sau đó 3 vòng; mỗi vòng gồm {C, P1, P2, M1, T1, K1, R1-B}, xáo bằng
  `random.Random(20261121 + vòng).shuffle` (vòng = 1, 2, 3). Tên lần: `G`, `<biến thể>-<vòng>` (vd. `P1-2`, `C-3`).
- **Trước MỖI lần (kể cả G):** dừng mọi tiến trình ollama, khởi động server đúng phiên bản (B cho R1-B, A cho còn lại),
  kiểm phiên bản + ghim; không có lời gọi khởi động nào khác. M1: kiểm thêm ghim 7b.
- **Lần hỏng:** > 10 % item lỗi ⇒ chạy lại một lần với tên `<tên>_r` (luật V2-08 (f)); hỏng lần hai ⇒ loại, báo.
- **Điều kiện dừng:** RAM trống < 6 GB trước một lần ⇒ chờ tới 30 phút, vẫn thiếu ⇒ dừng (checkpoint); không đủ giờ
  trước 08:00 cho lần kế (ước 25 phút, M1 45 phút) ⇒ dừng, đêm sau chạy tiếp từ checkpoint đúng thứ tự; sự cố phiên
  bản/ghim ⇒ dừng toàn bộ, không chạy tiếp tới khi anh xem.
- **Ghi:** `study/pipeline2/results/S3C_20261121_v1.jsonl` (+ `.manifest.jsonl`), chỉ append; checkpoint = manifest.
  Không ghi vào file của study 2/3/V2-09.

**Thống kê sẽ báo (script `study/analysis_p6/run_s3c.py`, chạy sau khi đủ 22 lần):**
1. Nền: với mỗi control C-v (v = 1..3) so với G: số test đỏ theo decision, exact match (`av3.chuan_hoa`), token-F1 < τ
   (τ ∈ lưới mục B2), embedding < τ_e (lưới B2).
2. Với mỗi thay đổi x và mỗi lần x-v so với G: số test "truly changed" theo chuẩn ngoài `av3.dung` (chuẩn chính) và
   theo chuẩn thay thế S-F1 (mục B2.4); số bị decision suite bỏ sót (truly changed mà decision không đỏ); số bị exact
   match bỏ sót; theo chiều đúng→sai / sai→đúng.
3. Gộp 3 lần mỗi thay đổi: tỉ lệ bỏ sót = Σ sót / Σ truly changed, Wilson 95 %, và khoảng bootstrap cụm theo câu hỏi
   (`cluster_ratio` của posthoc3, B = 2000, 5 seed `av3.SEEDS`, lấy khoảng rộng nhất). Gộp mọi thay đổi: như trên.
4. Độ lặp: với mỗi thay đổi, số câu (trên 40) có cả 3 lần cho decision giống nhau và artefact (chuẩn hoá) giống nhau.
5. Đối chiếu số cũ "decision suite bỏ sót 10 trên 58" (study 3, 1 lần mỗi thay đổi, nền không sạch).

**Luật diễn giải (ghi trước):**
- **I1.** Nếu cả 3 control có 0 test đỏ theo decision VÀ 0 theo exact match so với G ⇒ nền = 0; mọi test đỏ ở lần
  thay đổi được quy cho thay đổi; tỉ lệ bỏ sót mục 3 là kết quả chính của (a).
- **I2.** Nếu control đỏ > 0 ⇒ loại khỏi mẫu số các câu đỏ ở bất kỳ control nào (theo oracle đang xét) làm tỉ lệ chính;
  báo kèm tỉ lệ trên toàn bộ câu làm phụ, và Δ (thay đổi − control) theo `av3.boot_delta`.
- **I3.** Bài thay "missed 10 of 58" bằng số gộp mục 3 bất kể giá trị. Nếu cận dưới Wilson của tỉ lệ bỏ sót gộp = 0
  và số bỏ sót = 0 ⇒ viết "không quan sát thấy bỏ sót trong điều kiện này". Nếu > 0 ⇒ báo tỉ lệ và chiều.
- **I4.** Nếu 3 lần của một thay đổi giống hệt nhau từng byte ⇒ ghi rõ lặp không thêm thông tin độc lập về biến thiên
  câu trả lời (n hiệu dụng = 40 câu), không trình bày 3 lần như 3 mẫu độc lập.
- **I5.** Không đổi chuẩn ngoài, ngưỡng hay mẫu số sau khi thấy số.

## (b) B1 — tách drift, biến thiên chập chờn và false alarm (study 2, dữ liệu đã lưu, R2-05)

**Dữ liệu:** obs của study 2 (`results/oracle/obs_lan*.json`), đúng các lần đọc của phân tích đăng ký
(`av2.oracle_an.phan_tich`: 20 lần hosted, 20 lần local, lần đầu = golden). 7 ô stage × nhánh, 40 test mỗi ô.
Mức: decision (`==`) và artefact (`chuan_hoa` ==). Script `study/analysis_p6/run_b1.py`.

**Định nghĩa (dùng nhất quán trong bài sửa):**
- **False alarm** (giữ định nghĩa cũ): test đỏ so với golden trên code không đổi.
- Chuỗi giá trị của một test qua 20 lần theo thời gian v₀…v₁₉ (v₀ = golden). Một **điểm đổi** là i với vᵢ ≠ vᵢ₋₁.
- **Ổn định:** 0 điểm đổi.
- **Drift (lệch bền):** đúng 1 điểm đổi tại j, 1 ≤ j ≤ 18 (sau điểm đổi còn ≥ 2 lần, đều bằng nhau). Phân nhóm
  **"golden lệch"** khi j = 1 (mọi lần sau golden bằng nhau và khác golden).
- **Biến thiên chập chờn (intermittent):** ≥ 2 điểm đổi.
- **Chưa phân loại:** đúng 1 điểm đổi tại j = 19.
- (Thuật ngữ: "flaky test" vẫn là thuộc tính của test theo [nguồn] như bài đã dùng; drift và chập chờn là hai nguồn
  gây false alarm. Không gọi drift là flaky.)

**Báo:** (1) số test mỗi ô theo 4 lớp, ở cả hai mức; (2) phần trăm lượt test-đỏ (test × lần) do mỗi lớp gây ra;
(3) **luân phiên golden:** với mỗi g ∈ 0..19 làm golden, tỉ lệ test đỏ mỗi lần trung bình trên 19 lần còn lại; báo
trung bình, nhỏ nhất, lớn nhất qua g, và giá trị tại g = 0 (đăng ký); (4) **mọi cặp:** tỉ lệ cặp (i < j, 190 cặp) lệch,
trung bình trên test; (5) với ô local, đánh dấu điểm đổi trùng đoạn cập nhật runtime (`rd.doan` A/B) — mô tả.
**Diễn giải ghi trước:** nếu ≥ 50 % lượt test-đỏ của một ô do drift (gồm golden lệch) ⇒ bài viết rằng ở ô đó phần lớn
báo đỏ là lệch bền so với golden, không phải dao động lần-đến-lần, và hệ quả thực hành (làm mới golden thay vì chạy
lại). Dưới 50 % ⇒ viết ngược lại. Không đổi ngưỡng 50 % sau khi thấy số.

## (c) B2 — đường token-F1, oracle embedding, oracle trường JSON, chuẩn ngoài thay thế (R2-03, R2-04, R2-15)

**Dữ liệu:** study 3 (`S3_20261112_v1`), lần thay đổi + 3 control, so với golden của nhánh; V2-09 (`S3B_20261113_v1`)
3 control C1–C3 so với golden của V2-09; study 2 cho false alarm mỗi lần (như B1). Sau khi (a) xong: áp cùng mã cho S3C.
Script `study/analysis_p6/run_b2.py`. Không gọi model sinh; embedding chạy cục bộ.

1. **Token-F1** (`f1` của posthoc3, chuẩn hoá SQuAD) giữa lần chạy và golden; đỏ nếu F1 < τ.
   **Lưới cố định: τ ∈ {0,05; 0,10; …; 1,00}** (20 giá trị). Không chọn ngưỡng "tốt nhất"; báo toàn đường. Hai ngưỡng
   0,8 và 0,5 đã in trong bài trước được ghi rõ là **chọn sau khi đã thấy đầu ra**.
2. **Embedding cosine**: `intfloat/multilingual-e5-small`, revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`
   (bản cache cục bộ, `sentence-transformers` 6.0.1, `torch` 2.14.0+cpu, chuẩn hoá L2, tiền tố `"query: "` cho cả hai
   văn bản); đỏ nếu cos < τₑ. **Lưới: τₑ ∈ {0,80; 0,81; …; 1,00}** (21 giá trị). Không chọn ngưỡng tốt nhất.
3. **Trường JSON** (classify): bỏ rào ```` ``` ````, `json.loads`, so `answerable` và `language`; parse hỏng ⇒ giá trị
   "PARSE_FAIL". Đỏ nếu bộ (answerable, language) khác golden. Báo false alarm mỗi lần (study 2, study 3 control) và
   phát hiện trên test classify truly changed.
4. **Chuẩn ngoài thay thế ở generate (R2-03):** S-F1 = câu trả lời được coi đúng nếu (không trả lời được ⇒ decision
   abstain) hoặc (trả lời được ⇒ decision ≠ abstain và max token-F1 so với các gold answer ≥ 0,5). Cùng với chuẩn
   substring cũ (`av3.dung`), báo: số truly changed, số decision bỏ sót, theo từng chuẩn và phần giao; số test hai chuẩn
   bất đồng về tính đúng. Không có người chấm thứ hai (một tác giả) ⇒ nêu ở Threats; không dùng LLM judge.
5. **Báo cho mọi oracle** (decision, exact match, F1@τ, embedding@τₑ; classify thêm trường JSON; route thêm route field
   đã có): ma trận nhầm lẫn trên lần thay đổi (đỏ/không × truly changed/không) → recall, precision; và false alarm mỗi
   lần trên control (study 3, V2-09) và study 2 (theo nhánh). Đường precision–recall theo lưới.
6. Diễn giải ghi trước: bài chỉ nói "ở lưới này, không ngưỡng nào đạt recall = 1 với false alarm mỗi lần trên control
   pinned < X" nếu đúng như số; không gọi ngưỡng nào là khuyến nghị; nêu false alarm kèm mọi câu khuyên dùng ngưỡng.

## Lệch kế hoạch
(trống tại mốc commit; mọi lệch ghi ở `P6/RESULTS_ADDENDUM_MD.md`)
