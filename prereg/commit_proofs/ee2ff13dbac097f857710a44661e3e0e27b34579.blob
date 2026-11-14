r"""Đợt đo bù V2-09 (AMENDMENT V2-09, PREREG_V2): đối chứng local (a), P1′ + kiểm thao tác (b), R1 lặp (c).

Dùng lại hàm của `p2/s3.py` (gọi model, ghim, đổi server); KHÔNG đổi file đó và KHÔNG ghi vào file kết quả của
nghiên cứu 3. Ghi `results/S3B_20261113_v1.jsonl` (+ manifest), chỉ append.
"""
from __future__ import annotations

import json
import random

from . import P2_DIR, prompts, s3

RESULT = P2_DIR / "results" / "S3B_20261113_v1.jsonl"
MANIFEST = P2_DIR / "results" / "S3B_20261113_v1.manifest.jsonl"
TRAN_USD = 0.20
DU_PHONG_USD = 0.03
SEED_MC = 20261114

# ------------------------------------------------------------------ P1′: một từ đồng nghĩa mỗi stage (V2-09 (b))
DOI_P1P = {
    "classify": ("Decide whether the passage contains the answer", "Determine whether the passage contains the answer"),
    "route": ("Decide one route:", "Choose one route:"),
    "generate": ("Cite every claim with its document id", "Cite each claim with its document id"),
}


def _p1p() -> dict:
    out = {}
    for st, (cu, moi) in DOI_P1P.items():
        g = s3.GOC[st]
        assert g.count(cu) == 1, st
        out[st] = g.replace(cu, moi)
    return out


PROMPT_P1P = _p1p()

# ------------------------------------------------------------------ thứ tự cố định (V2-09 (d)), không xáo
HOSTED = ["MC-goc", "MC-P1p", "golden", "C1", "C2", "C3", "P1p"]
LOCAL_KHOI_A = ["golden", "C1", "C2", "C3", "P1p"]
LOCAL_D = ["D1", "D2", "D3"]
LOCAL_R1 = ["B1", "A1", "B2", "A2", "B3", "A3"]
LOCAL_MC = ["MC-goc", "MC-P1p"]


def plan() -> dict:
    return json.loads((P2_DIR / "runner" / "plan_p2.json").read_text(encoding="utf-8"))["mau"]


def oracle_qids() -> list[str]:
    return plan()["oracle_qids"]


def mc_qids() -> list[str]:
    """40 câu NGOÀI mẫu oracle: Random(20261114).sample(sorted(n2 − oracle), 40), sắp xếp."""
    p = plan()
    o = set(p["oracle_qids"])
    con = sorted(q for q in p["n2_qids"] if q not in o)
    assert len(con) == 160
    return sorted(random.Random(SEED_MC).sample(con, 40))


def bien_the(ten: str) -> s3.BienThe:
    if ten in ("MC-goc", "golden", "C1", "C2", "C3", "D1", "D2", "D3", "A1", "A2", "A3"):
        return s3.BienThe(ten, s3.GOC)
    if ten in ("MC-P1p", "P1p"):
        return s3.BienThe(ten, PROMPT_P1P)
    if ten in ("B1", "B2", "B3"):
        return s3.BienThe(ten, s3.GOC, runtime=s3.OLLAMA_B)
    raise ValueError(ten)


def qids_cho(ten: str) -> list[str]:
    return mc_qids() if ten.startswith("MC-") else oracle_qids()


def da_co() -> set[tuple[str, str]]:
    if not MANIFEST.exists():
        return set()
    out = set()
    for l in MANIFEST.read_text(encoding="utf-8").splitlines():
        m = json.loads(l)
        if m.get("trang_thai") == "ok":
            out.add((m["arm"], m["run"]))
    return out


def tien() -> float:
    if not MANIFEST.exists():
        return 0.0
    return sum(json.loads(l).get("usd", 0.0) or 0.0 for l in MANIFEST.read_text(encoding="utf-8").splitlines())


def sha_prompts(bt: s3.BienThe) -> dict:
    return {st: s3.sha(bt.prompt[st]) for st in bt.stages_chay}


__all__ = ["RESULT", "MANIFEST", "PROMPT_P1P", "HOSTED", "LOCAL_KHOI_A", "LOCAL_D", "LOCAL_R1", "LOCAL_MC",
           "mc_qids", "oracle_qids", "bien_the", "qids_cho", "da_co", "tien", "prompts"]
