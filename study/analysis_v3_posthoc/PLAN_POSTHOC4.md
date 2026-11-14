# PLAN_POSTHOC4: phân tích post hoc lần 4 (P3G, 14-11-2026), ghi TRƯỚC khi chạy

Viết sau kiểm đóng lỗi vòng 4 (`P3/R2_CLOSURE4_MD_20261114.md`, R3, R4, mục 4.8). Mọi số mang nhãn **post hoc**. Không đổi verdict đăng ký. Chỉ đọc đầu ra đã lưu; không gọi model; **không thêm ngưỡng mới** (dùng τ = 0,8 và 0,5 của `PLAN_POSTHOC3.md`).

Script: `run_v3_posthoc4.py` → `out/numbers_v3_posthoc4.json`.

## N. Luật naive trên hai bộ cặp (13 đơn vị pipeline 2, `av2.cells.DV_P2`)

- **Nguồn:** `study/analysis_v2/out/numbers_v2.json`, `don_vi[o]`.
- **Cặp same-runtime (V2-07):** dùng `k`, `n`.
- **Cặp đăng ký (run 1 → 5):** dùng `cap_1to5_dang_ky.k` và `.n` nếu có; không có thì dùng `k`, `n` (ô không đổi cặp).
- **Naive:** `av2.stats.phan_quyet("ổn định", k, n)`.
- **Matrix:** verdict đã lưu (`phan_quyet`, `cap_1to5_dang_ky.phan_quyet`).
- **In cho mỗi bộ cặp:**
  - số đúng, sai, undecided;
  - số đúng / số phân định;
  - đạt ngưỡng 2/3 hay không;
  - danh sách ô theo verdict.

## F. Token-F1 phía phát hiện (study 3, generate)

Tập 58 test truly changed, đúng định nghĩa `av3.dung` như P3F.
- **Phát hiện bởi token-F1** nếu F1(lần chạy, golden) < τ; tính cho τ = 0,8 và τ = 0,5.
- **Đếm:**
  - phát hiện trên 58 và theo chiều (đúng→sai, sai→đúng);
  - phát hiện trên 10 ca decision sót, theo chiều;
  - để đối chiếu, decision và exact match trên cùng tập.
- **Route field:** không có chuẩn ngoài ở route, nên không có phía phát hiện; ghi rõ.

## Q. Bảng đếm theo câu hỏi

Cho mỗi câu có ít nhất một thay đổi tính đúng ở generate (study 3, lần thay đổi):
- answerable hay không;
- số thay đổi theo chiều;
- số ca decision sót.

Đây là đầu vào của hai khoảng cluster bootstrap đã in ở P3F, để người đọc tính lại được.
