r"""Oracle pipeline 2 (PREREG_V2 §5) — như M6 Microduck (A04.3), cho p2.

Mỗi lần chạy (task `p2_oracle`, mốc tuyệt đối 09:00/21:00; từ AMENDMENT V2-02: 00/06/12/18 giờ): gọi pipeline MỘT lần cho mỗi (câu × stage × nhánh),
ghi `obs` ra file; rồi chạy HAI bộ pytest trên cùng `obs`:
    tests_p2_decision/  : decision lần này == decision golden
    tests_p2_artefact/  : chuan_hoa(artefact) lần này == chuan_hoa(artefact golden)   (luật A04.3, dùng lại hàm M6)
Golden = obs của lần chạy hợp lệ ĐẦU TIÊN (không chọn tay). Lần golden không chạy suite.
Biến môi trường: P2_ORACLE_RUN, P2_ORACLE_GOLDEN — không đặt thì hai bộ tự skip (pytest thường không gọi API).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from . import P2_DIR
from .executors import chay_stage

ENV_RUN, ENV_GOLDEN = "P2_ORACLE_RUN", "P2_ORACLE_GOLDEN"
OBS_DIR = P2_DIR / "results" / "oracle"
# (stage, backend): live không vào oracle (quyết định 01-11); retrieve là nhánh BM25 ghim.
CAP = (("classify", "hosted"), ("classify", "local"), ("route", "hosted"), ("route", "local"),
       ("retrieve", "bm25"), ("generate", "hosted"), ("generate", "local"))


def doc_obs(p: str | Path) -> dict:
    return {it["key"]: it for it in json.loads(Path(p).read_text(encoding="utf-8"))["items"]}


def cac_obs() -> list[Path]:
    return sorted(OBS_DIR.glob("obs_lan*.json"))


class LoiCoUsage(RuntimeError):
    def __init__(self, msg: str, usage: dict) -> None:
        super().__init__(msg)
        self.usage = usage


def _cong(u: dict, x: dict | None) -> None:
    for k, v in (x or {}).items():
        u[k] = u.get(k, 0) + (v or 0)


def _junit(xml: Path) -> dict:
    ok, fail = [], []
    for tc in ET.parse(xml).getroot().iter("testcase"):
        ten = tc.get("name", "")
        key = ten[ten.find("[") + 1:-1] if "[" in ten else ten
        (fail if tc.find("failure") is not None or tc.find("error") is not None else ok).append(key)
    return {"n": len(ok) + len(fail), "passed": len(ok), "failed": sorted(fail)}


def chay_suite(ten: str, run: Path, golden: Path) -> dict:
    xml = run.with_name(run.stem + f".{ten}.xml")
    env = {**os.environ, ENV_RUN: str(run), ENV_GOLDEN: str(golden), "PYTHONIOENCODING": "utf-8"}
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(P2_DIR / f"tests_p2_{ten}"),
                        f"--junitxml={xml}"], cwd=str(P2_DIR), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900, **kw)
    if r.returncode not in (0, 1) or not xml.exists():
        raise RuntimeError(f"pytest {ten} rc={r.returncode}: {r.stdout[-300:]} {r.stderr[-300:]}")
    return {**_junit(xml), "rc": r.returncode}


class P2OracleRun:
    kind = "p2_oracle"

    def ready(self, t: dict) -> bool:
        return True

    def manifest(self, t: dict) -> dict:
        from .executors import mo_ta_model
        return {"kind": self.kind, "n_qid": len(t["params"]["qids"]), "cap": [list(c) for c in CAP],
                "models": {f"{s}|{b}": mo_ta_model({"backend": "local" if b == "local" else "hosted"}, s)
                           for s, b in CAP}}

    def run(self, t: dict) -> dict:
        p = t["params"]
        OBS_DIR.mkdir(parents=True, exist_ok=True)
        usage: dict = {}
        items = []
        try:
            for qid in p["qids"]:
                for stage, be in CAP:
                    r = chay_stage(stage, {"qid": qid, "backend": "local" if be == "local" else "hosted",
                                           "temperature": 0.0})
                    _cong(usage, r.get("usage"))
                    items.append({"key": f"{stage}|{be}|{qid}", "stage": stage, "backend": be, "qid": qid,
                                  "decision": r["decision"], "artefact": r["artefact"]})
        except Exception as e:
            raise LoiCoUsage(f"{type(e).__name__}: {e}", usage) from e
        run = OBS_DIR / f"obs_lan{int(p['lan']):02d}.json"
        b = json.dumps({"lan": p["lan"], "task_id": t["id"], "items": items}, ensure_ascii=False, indent=0).encode("utf-8")
        run.write_bytes(b)
        truoc = [x for x in cac_obs() if x != run and x.name < run.name]
        ra = {"lan": p["lan"], "obs": run.name, "obs_sha256": hashlib.sha256(b).hexdigest(), "n_items": len(items),
              "usage": usage or None}
        if not truoc:
            ra["golden"] = True
            return ra
        golden = truoc[0]
        ra.update(golden_obs=golden.name, decision=chay_suite("decision", run, golden),
                  artefact=chay_suite("artefact", run, golden))
        return ra
