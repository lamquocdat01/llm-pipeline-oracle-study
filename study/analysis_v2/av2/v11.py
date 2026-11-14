"""Số v1.1 đã công bố (đã biết trước khi đăng ký v2 — V2-05 D1: báo riêng, không cộng vào H3).
Nguồn: docs/PAPER-NUMBERS.md §11b (M6), §11c (M7, 15 đơn vị). Chép tay, test khoá.
"""
M6_ROUTING_HOSTED = {"dec_k": 10, "art_k": 40, "n": 40, "margin": 0.750, "lo": 0.575, "hi": 0.858}
# M2 (routing, M-protocol t0→t24h) — §11c ô 5–8
M2_T0 = {"dec_k": 0, "art_k": 13, "n": 100, "nhan": "delegated t=0.0 (ô 7/8 v1.1)"}
M2_T08 = {"dec_k": 1, "art_k": 80, "n": 100, "nhan": "delegated t=0.8 (ô 5/6 v1.1)"}
V11_TOM_TAT = {"dung": 9, "sai": 4, "khong_phan_dinh": 2, "thieu_luc_khong_tinh": 3, "loai_a06": 11, "don_vi": 15}
V11_SAI = ["ô 2 STT transcript delegated (S1, S2, S3): dự đoán không, đo 3/31, 13/110, 9/205",
           "ô 12 reply_text pinnable qwen 7b (M4): dự đoán ổn định, đo 9/50"]

# Hàng M-protocol v1.1 cho hồi quy khám phá D3 (pipeline = 1): (ô, nguồn, depth, pinnable, artefact, k, n)
V11_HANG = [
    (1, "S1", 1, 0, 0, 0, 31), (1, "S2", 1, 0, 0, 0, 110), (1, "S3", 1, 0, 0, 0, 205),
    (2, "S1", 1, 0, 1, 3, 31), (2, "S2", 1, 0, 1, 13, 110), (2, "S3", 1, 0, 1, 9, 205),
    (3, "S1", 1, 1, 0, 0, 31), (3, "S2", 1, 1, 0, 0, 110), (3, "S3", 1, 1, 0, 0, 205),
    (4, "S1", 1, 1, 1, 0, 31), (4, "S2", 1, 1, 1, 0, 110), (4, "S3", 1, 1, 1, 0, 205),
    (5, "M2", 2, 0, 0, 1, 100), (6, "M2", 2, 0, 1, 80, 100), (7, "M2", 2, 0, 0, 0, 100), (8, "M2", 2, 0, 1, 13, 100),
    (9, "M2", 2, 1, 0, 0, 100), (10, "M2", 2, 1, 1, 1, 100),
    (11, "M4", 4, 1, 0, 1, 50), (12, "M4", 4, 1, 1, 9, 50), (13, "M4", 4, 1, 0, 1, 50), (14, "M4", 4, 1, 1, 4, 50),
    (15, "M3", 3, 0, 0, 0, 30), (16, "M3", 3, 0, 1, 20, 30), (17, "M3", 3, 0, 1, 21, 30),
]

# Ô v2 ↔ ô tương tự ở v1.1 (cho mục "Where the matrix was wrong": có lặp ở pipeline 1 không). Viết trước khi đọc.
TUONG_TU_V11 = {
    1: "ô 1/3 (STT nhãn ngôn ngữ): đúng", 2: "ô 2 (STT transcript delegated): SAI ở cả S1–S3",
    4: "ô 4/10 (artefact pinnable depth 1–2): đúng", 5: "ô 5/7 (routing lookup delegated): đúng",
    6: "ô 6 (t0.8) đúng; ô 8 (t0) không phân định", 8: "ô 10 (routing text qwen 7b): đúng",
    9: "không có tương tự (BM25 mới ở v2)", 11: "ô 15 (grounding lookup): không phân định (thiếu lực)",
    12: "ô 16 (domain-set): đúng", 13: "ô 17 (grounding text): đúng", 14: "ô 7 (decision delegated): đúng",
    15: "ô 8 (text delegated t0): không phân định", 17: "ô 12 SAI (qwen 7b), ô 14 không phân định (qwen 3b)",
    19: "ô 10 (routing text pinnable): đúng", 21: "ô 12 SAI, ô 14 không phân định (reply_text pinnable)",
    23: "ô 10 (routing text pinnable): đúng", 25: "ô 12 SAI (cùng observable reply_text)",
    26: "ô 5/7: đúng", 27: "ô 6/8", 28: "ô 7: đúng", 29: "ô 8: không phân định",
}
