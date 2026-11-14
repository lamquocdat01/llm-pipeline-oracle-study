r"""Đợt đo bù V2-09 → out/numbers_v3b.json (tất định: khoá sắp xếp, 6 chữ số).

    python study\analysis_v3b\run_v3b.py                         # dữ liệu thật
    python study\analysis_v3b\run_v3b.py --data <dir giả> --cau-json <f> --v3 <f> --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import av3b  # noqa: E402

av3 = av3b.av3
DATA_THAT = REPO / "study" / "pipeline2" / "results"
V3_THAT = REPO / "study" / "analysis_v3" / "out" / "numbers_v3.json"
TEN = "S3B_20261113_v1"


def cau_that(qids: set[str]) -> dict:
    sys.path.insert(0, str(REPO / "study" / "pipeline2"))
    from p2 import corpus
    _, cau = corpus.nap()
    return {c.qid: c for c in cau if c.qid in qids}


def v208_ctl(v3: Path) -> dict:
    """Số test decision đỏ ở generate của C1–C3 (V2-08), mỗi nhánh — chỉ đọc numbers_v3.json đã khoá."""
    if not v3.exists():
        return {}
    N = json.loads(v3.read_text(encoding="utf-8"))
    return {arm: [A["runs"][c]["stages"]["generate"]["dec_do"] for c in ("C1", "C2", "C3")]
            for arm, A in N["arms"].items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA_THAT)
    ap.add_argument("--out", type=Path, default=HERE / "out")
    ap.add_argument("--cau-json", type=Path)
    ap.add_argument("--v3", type=Path, default=V3_THAT)
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
    N = av3b.phan_tich(runs, cau, v208_ctl(a.v3))
    N["_schema"] = "numbers_v3b/1"
    N["inputs"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (res, man)}
    N["manifest"] = [{k: m.get(k) for k in ("arm", "run", "bien_the", "ts", "ts_end", "trang_thai", "n_loi", "model",
                                            "api_version", "cli_version", "usd", "qids")} for m in manifest]
    N["tham_so"] = {"B": av3.B, "seeds": list(av3.SEEDS), "k_mc": av3b.K_MC}
    N = av3.lam_tron(N)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "numbers_v3b.json").write_text(json.dumps(N, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                            encoding="utf-8", newline="\n")
    print(f"xong: {a.out / 'numbers_v3b.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
