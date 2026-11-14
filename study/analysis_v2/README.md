# analysis_v2 — N4 của PREREG_V2 (Microduck v2.0)

Phân tích đúng PREREG_V2 §6–§9 + V2-05 (D1–D10) + V2-06 + V2-07. Viết, test trên dữ liệu giả và **commit trước lần
đọc thật đầu tiên** (V2-05 D2); hash ở `FROZEN.md`.

```
python -m venv .venv && .venv\Scripts\pip install -r study\analysis_v2\requirements.txt
.venv\Scripts\python -m pytest -q -p no:cacheprovider study\analysis_v2\tests      # dữ liệu giả (tests/fake.py)
.venv\Scripts\python study\analysis_v2\run_analysis.py                              # dữ liệu thật → out/
```

- `av2/stats.py` Wilson, Newcombe hybrid, luật chấm §6 (sao y v1.1 `cham_m6_m7.py`).
- `av2/cells.py` 29 ô, luật "đổi" §3, cặp chấm: 1→5 (hosted, BM25, P3H), cùng runtime `chon_k` (local, V2-07(b)), t0→t24h (MD3R).
- `av2/oracle_an.py` P2O: 20 lần hợp lệ đầu (hosted, BM25), 20 lần đầu đoạn A/D (local, V2-07(c)); tính lại từ obs và đối chiếu junit.
- `av2/logit.py` H1: ML + SE cluster CR1; tách hoàn toàn ⇒ Firth + bootstrap cluster B = 2 000 × 5 seed.
- `av2/analysis.py` H1/H2/H3, D4, D7, D9, D10, V2-06, "where the matrix was wrong".
- `out/numbers_v2.json` nguồn duy nhất cho mọi số trong bài (khoá sắp xếp, làm tròn 6 chữ số, tất định).
