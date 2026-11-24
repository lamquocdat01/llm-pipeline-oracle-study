r"""Reproduce the three number files of the re-analysis addendum and the repeated measurement (P6) from the released data
and compare them KEY BY KEY with the shipped files in study/analysis_p6/out.

    THS_DATASETS=datasets python repro_p6.py          (run at the root of the release)

The scripts write into study/analysis_p6/out; this script backs the shipped files up, reruns run_b1.py, run_b2.py and
run_s3c.py, compares, and always restores the shipped files. B2 and S3C need sentence-transformers and the embedding
model intfloat/multilingual-e5-small at revision 614241f622f53c4eeff9890bdc4f31cfecc418b3 (downloaded on first use
unless HF_HUB_OFFLINE=1 and it is cached). rc 0 <=> every key matches.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from repro_ist import so  # key-by-key comparison of two JSON files

ROOT = Path(__file__).resolve().parent
P6 = ROOT / "study" / "analysis_p6"
JOBS = [("run_b1.py", "numbers_p6_b1.json"), ("run_b2.py", "numbers_p6_b2.json"), ("run_s3c.py", "numbers_p6_s3c.json"),
        ("run_posthoc_r2b.py", "numbers_p6_r2b.json")]   # v2.3: post hoc after the second review (server state, two standards)


def main() -> int:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "THS_DATASETS": str(ROOT / "datasets")}
    loi = 0
    with tempfile.TemporaryDirectory() as td:
        bk = Path(td) / "shipped"
        shutil.copytree(P6 / "out", bk)
        try:
            for script, ten in JOBS:
                r = subprocess.run([sys.executable, script], cwd=P6, env=env, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                lech = so(P6 / "out" / ten, bk / ten) if r.returncode == 0 else [f"rc={r.returncode} {r.stderr[-400:]}"]
                print(f"{ten}: {'MATCH' if not lech else 'DIFF ' + str(lech[:5])}")
                loi += bool(lech)
        finally:
            shutil.rmtree(P6 / "out")
            shutil.copytree(bk, P6 / "out")
    print("all match" if not loi else f"{loi} file(s) differ")
    return 1 if loi else 0


if __name__ == "__main__":
    raise SystemExit(main())
