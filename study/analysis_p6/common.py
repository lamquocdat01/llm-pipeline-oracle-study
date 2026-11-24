r"""Hàm dùng chung của phân tích P6 (kế hoạch `P6/PREREG_ADDENDUM_MD_20261121.md`). Chỉ đọc dữ liệu đã lưu.

Dùng lại (chỉ đọc) `av3` (chuẩn hoá, chuẩn ngoài, Wilson), `run_v3_posthoc3.f1`, `cluster_ratio`, `route_field`.
"""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
P2 = REPO / "study" / "pipeline2"
RES = P2 / "results"
sys.path[:0] = [str(REPO / "study" / "analysis_v3_posthoc"), str(REPO / "study" / "analysis_v3"),
                str(REPO / "study" / "analysis_v2"), str(P2)]
import av3  # noqa: E402
from run_v3_posthoc3 import cluster_ratio, f1, route_field  # noqa: E402,F401

NHAN = "P6 addendum (kế hoạch P6/PREREG_ADDENDUM_MD_20261121.md; viết sau khi biết kết quả cũ và đọc R2)"
TAU_F1 = tuple(round(0.05 * i, 2) for i in range(1, 21))          # 0,05 … 1,00
TAU_EMB = tuple(round(0.80 + 0.01 * i, 2) for i in range(21))     # 0,80 … 1,00
EMB_MODEL = "intfloat/multilingual-e5-small"
EMB_REV = "614241f622f53c4eeff9890bdc4f31cfecc418b3"


@lru_cache(maxsize=1)
def cau() -> dict:
    from p2 import corpus
    return {c.qid: c for c in corpus.nap()[1]}


def dung_sf1(item: dict | None, c) -> bool | None:
    """Chuẩn ngoài thay thế S-F1 (addendum B2.4)."""
    if not item or not item.get("ok"):
        return None
    if c.impossible:
        return item["decision"] == "abstain"
    return item["decision"] != "abstain" and max((f1(item["artefact"], a) for a in c.answers), default=0.0) >= 0.5


_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


def json_field(s: str | None):
    try:
        d = json.loads(_FENCE.sub("", s or "").strip())
        return (d.get("answerable"), d.get("language"))
    except Exception:
        return "PARSE_FAIL"


class Emb:
    """Embedding cục bộ; cache theo văn bản."""

    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.m = SentenceTransformer(EMB_MODEL, revision=EMB_REV, device="cpu", local_files_only=True)
        self.c: dict = {}

    def vec(self, texts: list[str]):
        moi = sorted({t for t in texts if t not in self.c})
        if moi:
            vs = self.m.encode(["query: " + t for t in moi], normalize_embeddings=True, batch_size=32,
                               show_progress_bar=False)
            for t, v in zip(moi, vs):
                self.c[t] = v
        return [self.c[t] for t in texts]

    def cos(self, a: str, b: str) -> float:
        va, vb = self.vec([a or "", b or ""])
        return float((va * vb).sum())


def oracle_reds(st: str, g: dict, it: dict, emb: Emb | None) -> dict:
    """Mọi oracle cho một test (golden g, lần it): 1 = đỏ."""
    r = {"dec": int(it["decision"] != g["decision"]),
         "art": int(av3.chuan_hoa(it["artefact"]) != av3.chuan_hoa(g["artefact"]))}
    if st == "generate":
        v = f1(it["artefact"], g["artefact"])
        r.update({f"f1<{t}": int(v < t) for t in TAU_F1})
        if emb is not None:
            c = emb.cos(it["artefact"], g["artefact"])
            r.update({f"emb<{t}": int(c < t - 1e-12) for t in TAU_EMB})
    if st == "classify":
        r["json"] = int(json_field(it["artefact"]) != json_field(g["artefact"]))
    if st == "route":
        r["route_field"] = int(route_field(it["artefact"]) != route_field(g["artefact"]))
    return r


def ghi_json(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(av3.lam_tron(d), ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8",
                   newline="\n")
    tmp.replace(p)
