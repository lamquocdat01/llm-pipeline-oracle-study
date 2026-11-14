r"""Okapi BM25 tất định, index ghi ra JSON và ghim bằng SHA-256 (stage retrieve, nhánh caller-pinnable).

Tự viết (~40 dòng) thay vì thêm thư viện vào venv desktop: toàn bộ thứ quyết định top-k (tokenizer,
k1, b, idf, thứ tự phá hoà) nằm trong file này + file index, nên "pinnable" kiểm được bằng hash.
Phá hoà theo doc id tăng dần — không phụ thuộc thứ tự dict/hash của Python.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

K1, B = 1.2, 0.75
_TOK = re.compile(r"[a-z0-9]+")
STOP = frozenset("a an the of in on at to for by with from and or is are was were be been what which who whom "
                 "when where why how did does do that this these those as it its into than".split())


def tok(s: str) -> list[str]:
    return [t for t in _TOK.findall(s.lower()) if t not in STOP]


def build(docs: list[dict]) -> dict:
    tf = [Counter(tok(d["text"])) for d in docs]
    df = Counter(t for c in tf for t in c)
    n = len(docs)
    return {"k1": K1, "b": B, "ids": [d["id"] for d in docs], "len": [sum(c.values()) for c in tf],
            "avgdl": sum(sum(c.values()) for c in tf) / n,
            "idf": {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in sorted(df.items())},
            "tf": [dict(sorted(c.items())) for c in tf]}


def luu(idx: dict, p: Path) -> str:
    b = json.dumps(idx, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    p.write_bytes(b)
    return hashlib.sha256(b).hexdigest()


def nap(p: Path, sha: str) -> dict:
    b = p.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    if h != sha:
        raise RuntimeError(f"BM25 index {p.name}: SHA-256 {h} khác bản ghim {sha}")
    return json.loads(b)


def search(idx: dict, q: str, k: int = 5) -> list[tuple[str, float]]:
    qt = tok(q)
    k1, b, avg = idx["k1"], idx["b"], idx["avgdl"]
    diem = []
    for i, tf in enumerate(idx["tf"]):
        s = 0.0
        for t in qt:
            f = tf.get(t)
            if f:
                s += idx["idf"][t] * f * (k1 + 1) / (f + k1 * (1 - b + b * idx["len"][i] / avg))
        if s > 0:
            diem.append((-round(s, 9), idx["ids"][i]))
    diem.sort()
    return [(d, -s) for s, d in diem[:k]]
