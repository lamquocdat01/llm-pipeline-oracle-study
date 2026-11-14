r"""Dựng index BM25 từ SQuAD 2.0 dev và ghi ghim (một lần, lúc N1). Dựng lại phải ra CÙNG SHA-256.

    cd study\pipeline2 && ..\..\desktop\.venv\Scripts\python.exe scripts\build_index.py [--kiem]

`--kiem`: dựng vào bộ nhớ và so SHA-256 với `data/index_pin.json` (tái lập), không ghi.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p2 import P2_DIR, bm25, corpus  # noqa: E402

DATA = P2_DIR / "data"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kiem", action="store_true")
    a = ap.parse_args()
    docs, cau = corpus.nap()
    idx = bm25.build(docs)
    b = json.dumps(idx, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    h = hashlib.sha256(b).hexdigest()
    pin_p = DATA / "index_pin.json"
    if a.kiem:
        pin = json.loads(pin_p.read_text(encoding="utf-8"))
        ok = pin["sha256"] == h
        print(f"dựng lại: {h}  ghim: {pin['sha256']}  -> {'KHỚP' if ok else 'LỆCH'}")
        return 0 if ok else 1
    DATA.mkdir(exist_ok=True)
    (DATA / "bm25_index.json").write_bytes(b)
    pin = {"sha256": h, "corpus_sha256": corpus.SHA256, "n_docs": len(docs), "n_questions": len(cau),
           "k1": bm25.K1, "b": bm25.B, "tokenizer": "lower, [a-z0-9]+, stoplist p2.bm25.STOP"}
    pin_p.write_text(json.dumps(pin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(pin, ensure_ascii=False), f"{len(b)} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
