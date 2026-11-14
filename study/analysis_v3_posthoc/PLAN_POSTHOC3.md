# PLAN_POSTHOC3: phân tích post hoc lần 3 (P3F, 14-11-2026), ghi TRƯỚC khi chạy

Viết sau phản biện nội bộ vòng 4 (`P3/R2_REVIEW4_MD_20261114.md`, G.1 mục 3, 5, 6). Mọi số sinh ra mang nhãn **post hoc**. Không đổi verdict đăng ký nào. Chỉ đọc đầu ra đã lưu; không gọi model.

Script: `run_v3_posthoc3.py` → `out/numbers_v3_posthoc3.json`. File này được commit **trước** lần chạy đầu của script.

## Q. Ca sót ở generate, theo câu hỏi (study 3, `S3_20261112_v1`)

1. Với mỗi nhánh và mỗi lần chạy thay đổi (không phải golden hay C1–C3), mỗi câu: tính đúng có đổi so với golden không (hàm `av3.dung`), và có bị sót không (artefact đỏ, decision không đổi).
2. Đếm:
   - số câu answerable có ít nhất một thay đổi tính đúng;
   - số câu có ít nhất một ca sót.
3. Bảng chéo nhánh × chiều (đúng→sai, sai→đúng) × answerable: số thay đổi, số sót.
4. Cluster bootstrap theo câu hỏi cho tỉ lệ sót: tỉ số tổng, 2 000 mẫu × 5 seed của `av3.SEEDS`, lấy khoảng rộng nhất. Áp cho:
   - 10/58 (mọi câu có thay đổi; số đăng ký);
   - 10/28 (chỉ câu answerable; post hoc).
5. Mức nền: số test "truly changed" trên mỗi lần đối chứng C1–C3 của từng nhánh. Đặt mức nền = trung bình × số lần thay đổi; in số quan sát, số kỳ vọng và phần vượt. Làm hai lần: với C1–C3 của study 3, và (nhánh pinned) với C1′–C3′ của V2-09.
6. Bảng mô tả 5 câu có ca sót gồm: qid, câu hỏi, đáp án vàng, nhánh, lần chạy, decision, và đáp án golden, đáp án lần chạy (cắt ngắn).

## O. Oracle tính offline

Tính trên hai tập:
- **(i) study 2**, các lần oracle NC2: đúng các lần mà `analysis_v2/av2/oracle_an.py` chọn (hosted: 19 lần sau golden; local: các lần cùng runtime);
- **(ii) study 3**, ba đối chứng C1–C3 của mỗi nhánh so với golden.

Các oracle, mỗi test trên mỗi lần chạy:
- **D:** decision khác golden (bộ decision hiện có).
- **A:** artefact chuẩn hoá khác golden (bộ artefact hiện có).
- **A-route:** chỉ ở route. So trường `ROUTE` lấy từ dòng đầu bắt đầu bằng `ROUTE:` sau chuẩn hoá, bỏ câu `REASON`. Không có dòng `ROUTE:` thì so cả văn bản.
- **F1 (generate):** token-F1 kiểu SQuAD giữa văn bản lần chạy và văn bản golden. Chuẩn hoá: chữ thường, bỏ dấu câu, bỏ mạo từ a/an/the, gộp khoảng trắng. Đỏ nếu F1 < τ.
  - **τ = 0,8 (chính)**; τ = 0,5 (độ nhạy). **Ngưỡng cố định tại đây, trước khi chạy.**
  - Hai văn bản rỗng: F1 = 1.
- **E (chuẩn ngoài, classify và generate):** tính đúng (`av3.dung`) khác golden. Câu nào một trong hai lần không chấm được thì bỏ qua câu đó.

Báo cho mỗi ô stage × nhánh × oracle:
- **Đỏ mỗi lần chạy:**
  - tỉ lệ trung bình qua các lần;
  - min–max theo lần;
  - khoảng 95 % bằng cluster bootstrap theo test, đúng quy trình ở Q.4.
- **Tích luỹ:** số test đỏ ở ít nhất một lần.
- **Kiểm cấu trúc:** số test có D đỏ mà A không đỏ trên cùng lần. Kỳ vọng 0, vì decision là hàm của artefact.

## S. Trạng thái server (đọc log, không đo)

1. `prompt_eval_count` trong `P2_20261102_v1.jsonl` và `P3_20261102_v1.jsonl`, theo (model, stage, câu): số giá trị khác nhau qua các lần.
   - Nếu mỗi prompt luôn cùng một giá trị, log không cho biết cache tiền tố có được dùng lại hay không.
   - S3 và S3B chỉ ghi `eval_count`.
2. 20 lần oracle NC2 ở nhánh pinned (generate), từng lần:
   - trùng golden hay không;
   - giờ mốc;
   - khoảng cách tới lần trước;
   - thời lượng (`ts_end − ts` trong `P2O`).
   - Bảng chéo mốc đêm (00:00, 06:00) với mốc ngày (12:00, 18:00) theo trùng / không trùng; Fisher exact hai phía.
   - Chỉ mô tả, không suy cơ chế.
