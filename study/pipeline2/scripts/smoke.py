r"""Smoke test N1: 20 câu đầu của mẫu (seed 20261101) chạy NỐI TẦNG qua đủ 4 stage, cả hai nhánh.

    cd study\pipeline2 && ..\..\desktop\.venv\Scripts\python.exe scripts\smoke.py [--n 20] [--khong-live]

Mỗi câu: classify (hosted, local) → route (hosted, local) → retrieve BM25 → generate (hosted, local) trên
top-5 BM25 → live grounding (hosted). Ghi `results/smoke_<ngày>.jsonl` (một dòng mỗi lời gọi), in token,
USD, thời gian theo stage × nhánh. Trần cứng: dừng nếu USD smoke vượt 0,20 hoặc tổng sổ đợt 32 ≥ 4,50.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p2 import P2_DIR, bm25, corpus, stages  # noqa: E402
from mrunner.core import gia_usd  # noqa: E402

GIA = {"in_text": 0.30, "in_audio": 1.00, "out": 2.50}
TRAN_SMOKE = 0.20


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--khong-live", action="store_true")
    a = ap.parse_args()
    docs, cau = corpus.nap()
    by_id = {d["id"]: d for d in docs}
    pin = json.loads((P2_DIR / "data/index_pin.json").read_text(encoding="utf-8"))
    idx = bm25.nap(P2_DIR / "data/bm25_index.json", pin["sha256"])
    qs = corpus.mau(cau)[:a.n]
    out = P2_DIR / "results" / f"smoke_{date.today():%Y%m%d}.jsonl"
    out.parent.mkdir(exist_ok=True)
    usd = 0.0
    tk = defaultdict(lambda: {"n": 0, "in": 0, "out": 0, "ms": 0, "usd": 0.0, "parse_fail": 0})
    with out.open("w", encoding="utf-8") as f:
        for i, q in enumerate(qs):
            buoc = [("classify", "hosted", lambda q=q: stages.classify(q, "hosted")),
                    ("classify", "local", lambda q=q: stages.classify(q, "local")),
                    ("route", "hosted", lambda q=q: stages.route(q, "hosted")),
                    ("route", "local", lambda q=q: stages.route(q, "local")),
                    ("retrieve", "bm25", lambda q=q: stages.retrieve_bm25(q, idx, by_id))]
            for stage, nhanh, fn in buoc + [("generate", "hosted", None), ("generate", "local", None)] \
                    + ([] if a.khong_live else [("live", "hosted", lambda q=q: stages.retrieve_live(q))]):
                if usd >= TRAN_SMOKE:
                    print(f"DỪNG: smoke chạm {TRAN_SMOKE} USD"); return 2
                if stage == "generate":
                    top = [by_id[d] for d in rec_bm25["decision"].split(",")]
                    fn = (lambda q=q, top=top, nh=nhanh: stages.generate(q, top, nh))
                t0 = time.time()
                r = fn()
                ms = round((time.time() - t0) * 1000)
                if stage == "retrieve":
                    rec_bm25 = r
                u = gia_usd(r.get("usage"), GIA)
                usd += u
                k = tk[(stage, nhanh)]
                k["n"] += 1; k["ms"] += ms; k["usd"] += u
                k["parse_fail"] += r["decision"] == "PARSE_FAIL"
                if r.get("usage"):
                    k["in"] += r["usage"]["in_text"]; k["out"] += r["usage"]["out"]
                elif r.get("prompt_eval_count") is not None:
                    k["in"] += r["prompt_eval_count"] or 0; k["out"] += r.get("eval_count") or 0
                f.write(json.dumps({"i": i, "qid": q.qid, "impossible": q.impossible, "gold_doc": q.gold_doc,
                                    "stage": stage, "nhanh": nhanh, "ms": ms, "usd": u, "decision": r["decision"],
                                    "artefact": r["artefact"][:2000], "usage": r.get("usage"),
                                    "model_version": r.get("model_version"), "digest": r.get("digest"),
                                    "sources": r.get("sources"), "gold_in_topk": r.get("gold_in_topk")},
                                   ensure_ascii=False) + "\n")
                f.flush()
            print(f"câu {i + 1}/{len(qs)} xong, USD {usd:.4f}", flush=True)
    print(f"\n{'stage':9s} {'nhánh':7s} {'n':>3s} {'in/lượt':>8s} {'out/lượt':>8s} {'s/lượt':>7s} {'USD/lượt':>9s} parse_fail")
    for (s, nh), k in tk.items():
        n = k["n"]
        print(f"{s:9s} {nh:7s} {n:3d} {k['in'] / n:8.0f} {k['out'] / n:8.0f} {k['ms'] / n / 1000:7.1f} "
              f"{k['usd'] / n:9.6f} {k['parse_fail']}")
    print(f"TỔNG USD smoke: {usd:.5f} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
