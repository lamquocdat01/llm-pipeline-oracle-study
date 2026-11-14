r"""Nghiên cứu 3 → out/numbers_v3.json + out/s3_runs.csv (tất định: khoá sắp xếp, 6 chữ số).

    python study\analysis_v3\run_v3.py                    # dữ liệu thật
    python study\analysis_v3\run_v3.py --data <dir giả> --out <dir>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import av3  # noqa: E402

DATA_THAT = REPO / "study" / "pipeline2" / "results"
TEN = "S3_20261112_v1"


def cau_that(qids: set[str]) -> dict:
    sys.path.insert(0, str(REPO / "study" / "pipeline2"))
    from p2 import corpus
    _, cau = corpus.nap()
    return {c.qid: c for c in cau if c.qid in qids}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA_THAT)
    ap.add_argument("--out", type=Path, default=HERE / "out")
    ap.add_argument("--cau-json", type=Path, help="dữ liệu giả: qid -> {impossible, answers}")
    a = ap.parse_args(argv)
    res, man = a.data / f"{TEN}.jsonl", a.data / f"{TEN}.manifest.jsonl"
    runs, manifest = av3.doc(res, man)
    qids = {q for r in runs.values() for (_, q) in r}
    if a.cau_json:
        from types import SimpleNamespace
        d = json.loads(a.cau_json.read_text(encoding="utf-8"))
        cau = {q: SimpleNamespace(impossible=v["impossible"], answers=tuple(v["answers"])) for q, v in d.items()}
    else:
        cau = cau_that(qids)
    N = av3.phan_tich(runs, cau)
    N["_schema"] = "numbers_v3/1"
    N["inputs"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (res, man)}
    N["manifest"] = [{k: m.get(k) for k in ("arm", "run", "bien_the", "ts", "ts_end", "trang_thai", "n_loi", "model",
                                            "api_version", "cli_version", "usd")} for m in manifest]
    N["tham_so"] = {"B": av3.B, "seeds": list(av3.SEEDS)}
    N = av3.lam_tron(N)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "numbers_v3.json").write_text(json.dumps(N, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                           encoding="utf-8", newline="\n")
    rows = []
    for arm, A in N["arms"].items():
        for run, R in A["runs"].items():
            for st, S in R["stages"].items():
                r = {"arm": arm, "run": run, "ky_vong": R["ky_vong"], "stage": st, "n": S["n"], "dec_do": S["dec_do"],
                     "art_do": S["art_do"]}
                for k in ("delta_dec", "delta_art"):
                    if k in S:
                        r.update({f"{k}": S[k]["delta"], f"{k}_lo": S[k]["lo"], f"{k}_hi": S[k]["hi"]})
                if "S3" in S:
                    r.update({f"S3_{k}": v for k, v in S["S3"].items() if not isinstance(v, list)})
                rows.append(r)
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with (a.out / "s3_runs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"xong: {a.out / 'numbers_v3.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
