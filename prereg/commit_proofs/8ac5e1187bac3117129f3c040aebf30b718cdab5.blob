r"""Corpus SQuAD 2.0 dev: đọc qua THS_DATASETS, kiểm SHA-256, chọn câu hỏi bằng seed.

Đường dẫn dataset KHÔNG ghi cứng (CLAUDE.md gốc): `$THS_DATASETS\pipeline2_corpus\dev-v2.0.json`,
mặc định `D:\Datasets`. SHA-256 lệch ⇒ từ chối (đo trên file khác là đo một thí nghiệm khác).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path

SHA256 = "80a5225e94905956a6446d296ca1093975c4d3b3260f1d6c8f68bc2ab77182d8"
SEED = 20261101
N_CAU = 200           # stage pinned/local + hosted không grounding (quyết định anh Đạt 01-11)
N_LIVE = 50           # live grounding: 50 câu đầu của mẫu 200


def duong_dan() -> Path:
    return Path(os.environ.get("THS_DATASETS", r"D:\Datasets")) / "pipeline2_corpus" / "dev-v2.0.json"


@dataclass(frozen=True)
class Cau:
    qid: str
    question: str
    gold_doc: str            # doc id của đoạn chứa câu hỏi
    impossible: bool
    answers: tuple[str, ...]
    title: str


def nap(p: Path | None = None) -> tuple[list[dict], list[Cau]]:
    """(docs, mọi câu hỏi). Doc id = `d<chỉ số đoạn toàn cục, 4 chữ số>` theo thứ tự file — ổn định."""
    p = p or duong_dan()
    b = p.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    if h != SHA256:
        raise RuntimeError(f"{p}: SHA-256 {h} khác bản ghim {SHA256}")
    d = json.loads(b.decode("utf-8"))
    docs, cau = [], []
    for a in d["data"]:
        for para in a["paragraphs"]:
            did = f"d{len(docs):04d}"
            docs.append({"id": did, "title": a["title"], "text": para["context"]})
            for q in para["qas"]:
                cau.append(Cau(q["id"], q["question"].strip(), did, bool(q.get("is_impossible")),
                               tuple(x["text"] for x in q.get("answers", [])), a["title"]))
    return docs, cau


def mau(cau: list[Cau], n: int = N_CAU, seed: int = SEED) -> list[Cau]:
    """Mẫu ngẫu nhiên có seed, không phân tầng. Với SEED mặc định: 20 câu đầu là câu SMOKE (N1)."""
    return random.Random(seed).sample(cau, n)


N_SMOKE = 20
SEED_N2 = 20261102
N_ORACLE = 40
SEED_ORACLE = 20261103


def smoke_ids(cau: list[Cau]) -> set[str]:
    return {c.qid for c in mau(cau)[:N_SMOKE]}


def mau_n2(cau: list[Cau]) -> list[Cau]:
    """200 câu đo N2 (PREREG_V2 §2): seed 20261102 trên dev TRỪ 20 id smoke; live = 50 câu đầu."""
    bo = smoke_ids(cau)
    return random.Random(SEED_N2).sample([c for c in cau if c.qid not in bo], N_CAU)


def mau_oracle(cau: list[Cau]) -> list[Cau]:
    """40 câu oracle: tập con của mẫu N2, seed 20261103."""
    return random.Random(SEED_ORACLE).sample(mau_n2(cau), N_ORACLE)
