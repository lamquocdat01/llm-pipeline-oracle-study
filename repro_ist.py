r"""Tái lập mọi file số của bản IST từ dữ liệu phát hành và so KEY-BY-KEY với file đã phát hành (P3E Việc 6).

    THS_DATASETS=datasets python repro_ist.py     (chạy ở gốc bản phát hành hoặc gốc repo)

Mỗi phân tích chạy lại vào thư mục tạm; JSON mới so với `out/` gốc theo từng khoá lá. rc 0 ⇔ khớp hết.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = [  # (script, đối số out, tên file kết quả, thư mục out gốc)
    ("study/analysis_v2/run_analysis.py", "--out", "numbers_v2.json", "study/analysis_v2/out", ["--no-fig"]),
    ("study/analysis_v3/run_v3.py", "--out", "numbers_v3.json", "study/analysis_v3/out", []),
    ("study/analysis_v3b/run_v3b.py", "--out", "numbers_v3b.json", "study/analysis_v3b/out", []),
]
INPLACE = [  # script ghi thẳng vào out/ của nó: chạy trên bản sao rồi so
    ("study/analysis_v2_posthoc/run_posthoc.py", "numbers_v2_posthoc.json", "study/analysis_v2_posthoc/out"),
    ("study/analysis_v3_posthoc/run_v3_posthoc.py", "numbers_v3_posthoc.json", "study/analysis_v3_posthoc/out"),
    ("study/analysis_v3_posthoc/run_v3_posthoc2.py", "numbers_v3_posthoc2.json", "study/analysis_v3_posthoc/out"),
    ("study/analysis_v3_posthoc/run_v3_posthoc3.py", "numbers_v3_posthoc3.json", "study/analysis_v3_posthoc/out"),
    ("study/analysis_v3_posthoc/run_v3_posthoc4.py", "numbers_v3_posthoc4.json", "study/analysis_v3_posthoc/out"),
]


def la(x, p=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from la(v, f"{p}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from la(v, f"{p}[{i}]")
    else:
        yield p, x


def so(a: Path, b: Path) -> list[str]:
    A, B = dict(la(json.loads(a.read_text(encoding="utf-8")))), dict(la(json.loads(b.read_text(encoding="utf-8"))))
    return [k for k in sorted(set(A) | set(B)) if A.get(k, "<thiếu>") != B.get(k, "<thiếu>")]


def main() -> int:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    env["THS_DATASETS"] = str(ROOT / "datasets")   # luôn dùng corpus đi kèm bản phát hành
    loi = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for script, flag, ten, goc, them in JOBS:
            out = td / Path(script).parent.name
            r = subprocess.run([sys.executable, str(ROOT / script), flag, str(out)] + them, env=env, capture_output=True, text=True)
            lech = so(out / ten, ROOT / goc / ten) if r.returncode == 0 else ["rc=%d %s" % (r.returncode, r.stderr[-300:])]
            print(f"{ten}: {'KHỚP' if not lech else 'LỆCH ' + str(lech[:5])}")
            loi += bool(lech)
        bk = td / "goc"
        for script, ten, goc in INPLACE:
            bk.mkdir(exist_ok=True)
            shutil.copy2(ROOT / goc / ten, bk / ten)
            r = subprocess.run([sys.executable, str(ROOT / script)], env=env, capture_output=True, text=True)
            lech = so(ROOT / goc / ten, bk / ten) if r.returncode == 0 else ["rc=%d %s" % (r.returncode, r.stderr[-300:])]
            shutil.copy2(bk / ten, ROOT / goc / ten)          # trả file gốc
            print(f"{ten}: {'KHỚP' if not lech else 'LỆCH ' + str(lech[:5])}")
            loi += bool(lech)
    print("ĐẠT" if not loi else f"CHƯA ĐẠT: {loi} file lệch")
    return 1 if loi else 0


if __name__ == "__main__":
    raise SystemExit(main())
