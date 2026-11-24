# POSTHOC_R2B_MD — phân tích lại sau phản biện vòng 2 (bài MD, JSS) · 24-11-2026

**Nhãn: POST HOC.** Viết 24-11-2026, SAU khi đã thấy mọi số S3C (`numbers_p6_s3c.json`) và SAU phản biện vòng 2
(`P6/R2B_REVIEW_MD_JSS_20261124.md`). Không có kế hoạch ghi trước; không gọi model; chỉ đọc dữ liệu đã lưu (S3, S3B,
S3C). Script: `study/analysis_p6/run_posthoc_r2b.py` → `study/analysis_p6/out/numbers_p6_r2b.json`. File này và script
được commit TRƯỚC khi số vào bài.

## 1. Lạnh / ấm (R2B-01) — nhánh pinned (qwen2.5:3b), server 0.30.10, prompt gốc

Nhãn run: **lạnh** = lượt đầu qua 40 câu sau một lần khởi động server (golden; follow-up A1–A3 và study 3 R1-A2 chạy sau
khi quay về 0.30.10, tức sau một lần khởi động); **ấm** = lặp lại prompt gốc trong cùng tiến trình server (C*, D*).

| | follow-up (S3B) | study 3 (S3) |
|---|---|---|
| Run lạnh giống nhau từng byte (generate) | **có**: golden = A1 = A2 = A3 | **có**: golden = R1-A2 |
| Run ấm với nhau (generate, số test khác byte) | C2 = C3 = D1 = D2 = D3 (0); C1 khác chúng 1 test | C1 = C3 (0); C2 khác chúng 19 test |
| Run ấm so với golden lạnh (decision / exact) | 5 / 23–24 mỗi run | C2: 4 / 18; C1, C3: 8 / 22 |
| classify, route | mọi run (lạnh và ấm) giống nhau từng byte | như vậy |
| FA mỗi run, golden lạnh, trên các run ấm: dec / exact / F1<0,8 / F1<0,5 / emb<0,9 | 0,125 / 0,579 / 0,504 / 0,150 / 0,100 | 0,167 / 0,517 / 0,450 / 0,217 / 0,125 |
| FA mỗi run khi golden là MỘT RUN ẤM (trung bình qua lựa chọn; max) | dec 0; exact **0,008** (max 0,025); F1<0,8 0,008; F1<0,5 0; emb<0,9 0 | dec 0,067 (0,100); exact 0,317 (0,475); F1<0,8 0,267 (0,400); F1<0,5 0,083; emb<0,9 0,050 |
| Phân lớp chuỗi golden → ấm → lạnh (Table 3) | exact: 24 chập chờn, 16 ổn định; decision 5 / 35 | exact 24 / 16; decision 8 / 32 |

Đọc: ở cả hai đợt, đầu ra phụ thuộc **trạng thái tiến trình server**: mọi run lạnh tái lập golden từng byte, và ở follow-up
năm trong sáu run ấm giống hệt nhau, chỉ khác golden. Phần lớn false alarm của oracle văn bản ở ô pinned generate vì
vậy là **khoảng cách lạnh–ấm** (so run ấm với golden lạnh), không phải dao động giữa các run. Ở study 3 còn một thành phần
giữa các run ấm (C2 khác C1, C3 trên 19 test; C2 chạy sau các biến thể khác, kể cả lần nạp model 7b — chưa kiểm vì sao).
Theo định nghĩa Table 3, chuỗi golden → ấm → lạnh có hai điểm đổi nên là "chập chờn", không phải drift; nhưng hình dạng
thật là **phụ thuộc trạng thái** (giá trị theo lạnh/ấm), một lớp mà Table 3 không có. Bài vì vậy: (i) giới hạn "none from
drift" và bước 4 về study 2; (ii) nêu kết quả âm FA ≥ 0,450 có điều kiện hai tầng (server chạy liên tục VÀ golden lạnh);
(iii) báo FA với golden ấm. Cơ chế (cache prompt của server) vẫn chưa kiểm.

## 2. Hai chuẩn ở đo lặp S3C (R2B-02) — lần đầu mỗi thay đổi

| | substring | S-F1 |
|---|---|---|
| ca bỏ sót (test) | 8 | 7 |
| trên số câu hỏi | **4** | **2** |
| chiều | 8 sai→đúng | 7 đúng→sai |
| câu answerable | 8/8 | 7/7 |
| độ dài câu trả lời (token, golden → lần thay đổi, trung bình) | 44,5 → 41,1 (4 dài hơn, 4 ngắn hơn) | 8,1 → 36,0 (7/7 dài hơn) |

**Giao nhau: 0 ca chung, 0 câu hỏi chung** (hợp: 15 ca trên 6 câu hỏi). Hai chuẩn đồng ý về tính đúng trên
**207/280 = 0,739** test-run (40 câu × golden + 6 lần thay đổi). Ca bỏ sót theo S-F1 đều là câu trả lời dài ra (đúng như
phản biện đoán: token-F1 so với gold ngắn giảm); ca theo substring không có xu hướng độ dài.
⇒ Bài thôi gọi là "changes of correctness" vô điều kiện; viết "changes under the substring / token-F1 standard", nói rõ
hai chuẩn đánh dấu hai tập ca rời nhau và bài không kết luận về chiều; kết luận còn đứng: nội dung câu trả lời đổi, lặp
lại được, trên nền 0, trong khi quyết định trích dẫn giữ — decision suite không thấy, exact match thấy. Không phân xử
người chấm (anh Đạt bỏ B3): giới hạn + việc tương lai.

## 3. Đơn vị mẫu (R2B-04)
- 40 test truly changed (substring) gộp qua 6 thay đổi nằm trên **18 câu hỏi**; 8 ca bỏ sót trên **4** câu. S-F1: 31 trên
  12 câu; 7 bỏ sót trên 2 câu. Khoảng theo câu hỏi (bootstrap cụm, 5 seed): substring [0,049; 0,381]; S-F1 [0,000; 0,463].
- Bỏ sót chỉ có thể xảy ra ở câu answerable: substring **8/20 = 0,40**, Wilson [0,219; 0,613]; S-F1 **7/11 = 0,64**,
  Wilson [0,354; 0,848] (Wilson coi test độc lập — quá hẹp; báo kèm khoảng theo câu hỏi).
- Precision trên lần thay đổi (substring): exact 40/174 = 0,23; decision 32/75 = 0,43.

## 4. 7/40 (follow-up) ↔ 5/40 (đo lặp) ở generate dưới 0.40.16 (R2B-06)
- Golden lạnh của đo lặp (chỉ chạy generate) khác golden lạnh của follow-up (chạy classify, route rồi generate trong cùng
  run) trên **15** test generate (3 decision); run 0.40.16 của hai đợt khác nhau trên 10 test (3 decision). Trong mỗi đợt,
  ba run 0.40.16 giống nhau từng byte.
- Run 0.40.16 của đo lặp so với golden của nó: 5 decision; run 0.40.16 của follow-up so với golden của nó: 7.
⇒ Cả hai số đúng trong thiết kế của nó; khác nhau vì đầu ra "lạnh" còn phụ thuộc các lời gọi trước đó trong cùng tiến
trình (ở đây: hai stage chạy trước generate). Củng cố R2B-08: "khởi động lại" là điều kiện cho cùng một chuỗi gọi, không
phải điều kiện đủ chung.
