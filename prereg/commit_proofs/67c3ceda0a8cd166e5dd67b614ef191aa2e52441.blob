"""Nạp bản ghi theo `task_id` (chỉ status ok), tách id, và hai hàm thuần mượn từ mã đã đăng ký.

Mượn bằng cách nạp FILE (không import gói, để không kéo runner): `mrunner/oracle.py::chuan_hoa` (luật A04.3),
`p2/runtime_doan.py` (đoạn A/B/D, `chon_k`, `lan_oracle_local` — V2-07).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime
from pathlib import Path

AV2 = Path(__file__).resolve().parents[1]          # study/analysis_v2
REPO = AV2.parents[1]                               # Microduck
DATA_THAT = REPO / "study" / "pipeline2" / "results"


def _nap_file(ten: str, p: Path):
    spec = importlib.util.spec_from_file_location(ten, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_oracle_md = _nap_file("av2_mrunner_oracle", REPO / "desktop" / "mrunner" / "oracle.py")
chuan_hoa = _oracle_md.chuan_hoa
rd = _nap_file("av2_runtime_doan", REPO / "study" / "pipeline2" / "p2" / "runtime_doan.py")

FILES = {"P2": "P2_20261102_v1.jsonl", "P2O": "P2O_20261102_v1.jsonl", "P3": "P3_20261102_v1.jsonl",
         "MD3": "MD3_20261102_v1.jsonl", "MD3R": "MD3R_20261102_v1.jsonl", "P3H": "P3H_20261102_v1.jsonl"}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def doc_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def ok_theo_id(recs: list[dict]) -> dict[str, dict]:
    ra: dict[str, dict] = {}
    for r in recs:
        if r.get("status") != "ok":
            continue
        if r["task_id"] in ra:
            raise ValueError(f"hai bản ghi ok cho một task: {r['task_id']}")
        ra[r["task_id"]] = r
    return ra


def tach_id(tid: str) -> dict:
    """P2|stage|be|qid|rNN · P2|stage|be|qid@tag|probe · MD3|M2|item|model|t0 · MD3|M2|item|model@tag|probe."""
    p = tid.split("|")
    m = p[0]
    if m in ("P2", "P3", "P3H"):
        q, tag = (p[3].split("@", 1) + [None])[:2]
        if p[4] == "probe":
            return {"m": m, "stage": p[1], "be": p[2], "q": q, "probe": tag, "run": None}
        return {"m": m, "stage": p[1], "be": p[2], "q": q, "probe": None, "run": int(p[4][1:])}
    if m in ("MD3", "MD3R"):
        model, tag = (p[3].split("@", 1) + [None])[:2]
        return {"m": m, "stage": p[1], "be": "local", "q": p[2], "probe": tag,
                "run": None if p[4] == "probe" else p[4]}
    if m == "P2O":
        return {"m": m, "lan": int(p[1][3:])}
    raise ValueError(tid)


def nap(data: Path) -> dict:
    """{m: {task_id: rec ok}}, cộng sha256 + số dòng từng file đã đọc (khoá vào numbers_v2.json)."""
    ra, vao = {}, {}
    for m, ten in FILES.items():
        p = data / ten
        if not p.exists():
            ra[m] = {}
            continue
        recs = doc_jsonl(p)
        ra[m] = ok_theo_id(recs)
        vao[ten] = {"sha256": sha256(p), "dong": len(recs), "ok": len(ra[m]),
                    "status": dict(sorted(_dem(r.get("status") for r in recs).items()))}
    ra["_inputs"] = vao
    return ra


def _dem(xs) -> dict:
    d: dict = {}
    for x in xs:
        d[x] = d.get(x, 0) + 1
    return d


def gio(a: str, b: str) -> float:
    return (datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 3600.0
