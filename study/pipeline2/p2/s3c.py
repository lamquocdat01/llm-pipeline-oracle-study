r"""Đo bù P6 (R2-02), kế hoạch `P6/PREREG_ADDENDUM_MD_20261121.md` mục (a).

Pinned generate (qwen2.5:3b; M1 = 7b), 6 thay đổi × 3 lần + 3 control + 1 golden = 22 lần; MỖI lần sau một lần khởi động
server đúng phiên bản (A 0.30.10; B 0.40.16 cho R1-B). Dùng lại hàm của `p2/s3.py`; KHÔNG đổi file đó, KHÔNG ghi vào file
của study 2/3/V2-09. Ghi `results/S3C_20261121_v1.jsonl` (+ manifest), chỉ append; manifest là checkpoint.
Sửa đổi 1 (22-11, `P6/PREREG_ADDENDUM_MD_AMEND1_20261122.md`): VO_HIEU, CHAY_LAI, D_TOI_THIEU_GIB, thu_tu_chay ở cuối file.
"""
from __future__ import annotations

import json
import random
from dataclasses import replace

from . import P2_DIR, s3

RESULT = P2_DIR / "results" / "S3C_20261121_v1.jsonl"
MANIFEST = P2_DIR / "results" / "S3C_20261121_v1.manifest.jsonl"
SEED_VONG = 20261121
BIEN_THE = ("C", "P1", "P2", "M1", "T1", "K1", "R1-B")
SO_VONG = 3


def thu_tu() -> list[str]:
    """G trước; 3 vòng, mỗi vòng {C, P1, P2, M1, T1, K1, R1-B} xáo bằng Random(20261121 + vòng)."""
    ds = ["G"]
    for v in range(1, SO_VONG + 1):
        vong = list(BIEN_THE)
        random.Random(SEED_VONG + v).shuffle(vong)
        ds += [f"{x}-{v}" for x in vong]
    return ds


def goc(ten: str) -> str:
    """'P1-2' → 'P1'; 'R1-B-3' → 'R1-B'; 'G' → 'G'."""
    return ten if ten == "G" else ten.rsplit("-", 1)[0]


def bien_the(ten: str) -> s3.BienThe:
    g = goc(ten)
    bt = s3.bien_the("golden" if g in ("G", "C") else g)
    return replace(bt, ten=ten, stages_chay=("generate",))


def runtime(ten: str) -> str:
    return s3.OLLAMA_B if goc(ten) == "R1-B" else s3.OLLAMA_A


def da_co() -> set[str]:
    if not MANIFEST.exists():
        return set()
    out = set()
    for l in MANIFEST.read_text(encoding="utf-8").splitlines():
        m = json.loads(l)
        if m.get("trang_thai") == "ok":
            out.add(m["run"].removesuffix("_r"))
    return out


def su_co_truoc() -> bool:
    if not MANIFEST.exists():
        return False
    return any(json.loads(l).get("trang_thai") == "su_co" for l in MANIFEST.read_text(encoding="utf-8").splitlines())


def phut_uoc(ten: str) -> int:
    return 45 if goc(ten) == "M1" else 25


# ------------------------------------------------------------------ sửa đổi 1 (P6/PREREG_ADDENDUM_MD_AMEND1_20261122.md)
# (a) lượt hỏng do ổ D đầy đêm 21→22-11 (P6/INCIDENT_S3C_20261122.md): vô hiệu do hạ tầng, GIỮ trong jsonl/manifest,
#     không dùng trong phân tích.
VO_HIEU = ("M1-2", "M1-2_r", "T1-2", "T1-2_r", "R1-B-2")
# (b) chạy lại đúng một lần mỗi biến thể; sau đó luật "hỏng → _r → loại" như cũ (vd. M1-2_i → M1-2_i_r).
CHAY_LAI = {"M1-2": "M1-2_i", "T1-2": "T1-2_i", "R1-B-2": "R1-B-2_i"}
# (c) trước MỖI lần (kể cả _r): ổ chứa kết quả trống ≥ 20 GiB (Get-PSDrive Free/1GB), thiếu ⇒ dừng, checkpoint.
D_TOI_THIEU_GIB = 20.0


def o_ke_hoach(ten: str) -> str:
    """Tên lần thực → ô của kế hoạch gốc: 'M1-2_i_r' → 'M1-2'; 'C-3_r' → 'C-3'."""
    return ten.removesuffix("_r").removesuffix("_i")


def thu_tu_chay() -> list[str]:
    """(d) Ba lần chạy lại trước (theo thứ tự ô gốc), rồi vòng 3 đúng thứ tự xáo đã ghi; ô đã ok của vòng 1–2 giữ chỗ."""
    ds = thu_tu()
    n12 = 1 + 2 * len(BIEN_THE)
    return [t for t in ds[:n12] if t not in CHAY_LAI] + [CHAY_LAI[t] for t in ds[:n12] if t in CHAY_LAI] + ds[n12:]


def trang_thai_lan() -> dict[str, str]:
    """tên lần (bỏ _r) → 'ok' | 'loai' (hỏng cả lần đầu lẫn _r) | 'cho_r' (lần đầu hỏng, chưa có _r) — từ manifest."""
    if not MANIFEST.exists():
        return {}
    hong: dict[str, set[str]] = {}
    out: dict[str, str] = {}
    for l in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        m = json.loads(l)
        ten = m["run"].removesuffix("_r")
        if m.get("trang_thai") == "ok":
            out[ten] = "ok"
        elif m.get("trang_thai") == "hong":
            hong.setdefault(ten, set()).add(m["run"])
    for ten, s in hong.items():
        if out.get(ten) != "ok":
            out[ten] = "loai" if ten + "_r" in s else "cho_r"
    return out
