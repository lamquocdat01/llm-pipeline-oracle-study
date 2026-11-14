"""Thống kê + luật chấm §6 (PREREG_V2), sao y luật v1.1 `desktop/scripts/cham_m6_m7.py` (A04.4, A04.5).

Không import file v1.1 (nó kéo theo cả runner); test `test_stats.py` khoá đúng các số v1.1 đã công bố.
"""
from __future__ import annotations

import math

Z = 1.959963984540054
ON, KHONG = "ổn định", "không"
NGUONG_ON, NGUONG_KHONG, RANH_GIOI, TREN_ON, N_LUC = 0.05, 0.20, 0.125, 0.10, 35


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """p1 − p2 và khoảng hybrid score (Newcombe 1998, phương pháp 10). n = 0 ở một bên ⇒ (nan, -1, 1)."""
    if n1 == 0 or n2 == 0:
        return (float("nan"), -1.0, 1.0)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return (d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def phan_quyet(du_doan: str, k: int, n: int) -> dict:
    """§6 nguyên văn (A04.4): ổn định đúng ⇔ k/n ≤ 5 % và cận trên Wilson ≤ 10 %; sai ⇔ k/n ≥ 20 %; vùng giữa
    không phân định nhưng sai nếu điểm ở nửa ngược (ranh 12,5 %). Không ổn định: đối xứng. n < 35 ⇒ thiếu lực
    (chỉ cho dự đoán ổn định); đơn vị thiếu lực vẫn vào mẫu số nếu sai."""
    if n == 0:
        return {"k": 0, "n": 0, "ty_le": None, "wilson": [0.0, 1.0], "phan_quyet": "không có cặp",
                "thieu_luc": True, "vao_mau_so": False}
    p = k / n
    lo, hi = wilson(k, n)
    if du_doan == ON:
        if p <= NGUONG_ON and hi <= TREN_ON:
            v = "đúng"
        elif p >= NGUONG_KHONG or p > RANH_GIOI:
            v = "sai"
        else:
            v = "không phân định"
        thieu_luc = n < N_LUC
    else:
        if p >= NGUONG_KHONG:
            v = "đúng"
        elif p <= NGUONG_ON or p < RANH_GIOI:
            v = "sai"
        else:
            v = "không phân định"
        thieu_luc = False
    return {"k": k, "n": n, "ty_le": p, "wilson": [lo, hi], "phan_quyet": v, "thieu_luc": thieu_luc,
            "vao_mau_so": (not thieu_luc) or v == "sai"}


def margin(k_art: int, n_art: int, k_dec: int, n_dec: int) -> dict:
    """Margin = R^art − R^dec, Newcombe hybrid 95 % (như §5, V2-06 và M6 v1.1)."""
    d, lo, hi = newcombe(k_art, n_art, k_dec, n_dec)
    return {"k_art": k_art, "n_art": n_art, "k_dec": k_dec, "n_dec": n_dec,
            "r_art": (k_art / n_art) if n_art else None, "r_dec": (k_dec / n_dec) if n_dec else None,
            "margin": d, "lo": lo, "hi": hi}


def chua_0(lo: float, hi: float) -> bool:
    return lo <= 0.0 <= hi


def median(xs: list[float]) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2
