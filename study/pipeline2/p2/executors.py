r"""Executor pipeline 2 cho `mrunner.core.Runner` — cùng giao diện M1–M4: `ready(t)`, `manifest(t)`, `run(t)`.

Task (sinh bởi `scripts/run_m_all_p2.py plan`): `{"id", "m", "kind": "p2_<stage>", "hosted", "heavy",
"params": {"qid", "backend", "temperature", "model"?, "seed"?}, "after"?}`. Executor tra câu hỏi theo `qid`
trong corpus đã kiểm SHA-256 — plan không mang văn bản câu hỏi (một nguồn sự thật).
Đầu vào cố định theo câu: classify nhận đoạn vàng; generate nhận top-5 BM25 của index ghim.
"""
from __future__ import annotations

import json
import time
from datetime import datetime

from . import P2_DIR, backends, bm25, corpus, prompts, stages
from .pin import PIN

_CACHE: dict = {}


def du_lieu() -> dict:
    if not _CACHE:
        docs, cau = corpus.nap()
        pin = json.loads((P2_DIR / "data/index_pin.json").read_text(encoding="utf-8"))
        _CACHE.update(by_id={d["id"]: d for d in docs}, q={c.qid: c for c in cau}, pin=pin,
                      idx=bm25.nap(P2_DIR / "data/bm25_index.json", pin["sha256"]))
    return _CACHE


KEEP = ("decision", "artefact", "artefact_domains", "usage", "model_alias", "model_version", "digest", "tham_so",
        "sources", "queries", "cited", "lang", "gold_in_topk", "scores", "finish_reason", "eval_count",
        "prompt_eval_count", "provider", "native_finish_reason", "gen_id", "system_fingerprint", "openrouter_metadata")


def chay_stage(stage: str, p: dict) -> dict:
    """Một lần gọi stage theo params của task (dùng chung cho executor M-protocol và oracle)."""
    c = du_lieu()
    q = c["q"][p["qid"]]
    temp = float(p.get("temperature", 0.0))
    kw = {"model": p.get("model"), "seed": int(p.get("seed", 0))}
    if stage == "classify":
        r = stages.classify(q, c["by_id"][q.gold_doc]["text"], p["backend"], temp, **kw)
    elif stage == "route":
        r = stages.route(q, p["backend"], temp, **kw)
    elif stage == "retrieve":
        r = stages.retrieve_bm25(q, c["idx"], c["by_id"])
    elif stage == "live":
        r = stages.retrieve_live(q, temp)
    elif stage == "generate":
        top = [c["by_id"][d] for d, _ in bm25.search(c["idx"], q.question, stages.K)]
        r = stages.generate(q, top, p["backend"], temp, **kw)
    else:
        raise ValueError(stage)
    return {k: r[k] for k in KEEP if k in r}


def mo_ta_model(p: dict, stage: str) -> dict | None:
    if stage == "retrieve":
        return None
    if p.get("backend") == "local":
        m = p.get("model") or backends.LOCAL_MODEL
        return {m: PIN[m]}
    if p.get("backend") == "openrouter":
        return {"alias": backends.HOSTED_LLAMA_MODEL, "slug": backends.HOSTED_LLAMA_SLUG, "allow_fallbacks": False,
                "require_parameters": True, "max_tokens": backends.MAX_OUT}
    return {"alias": backends.HOSTED_MODEL, "thinking_budget": 0, "max_output_tokens": backends.MAX_OUT,
            "google_search": stage == "live"}


class P2Exec:
    def __init__(self, stage: str) -> None:
        assert stage in ("classify", "route", "retrieve", "generate", "live")
        self.stage = stage
        self.kind = f"p2_{stage}"

    def ready(self, t: dict) -> bool:
        return True

    def manifest(self, t: dict) -> dict:
        p = t["params"]
        du_lieu()
        return {"kind": self.kind, "backend": p.get("backend"), "temperature": p.get("temperature"),
                "seed": p.get("seed", 0) if p.get("backend") in ("local", "openrouter") else None,
                "corpus_sha256": corpus.SHA256, "index_sha256": _CACHE["pin"]["sha256"],
                "prompt_sha256": prompts.sha(self.stage) if self.stage != "retrieve" else None,
                "model": mo_ta_model(p, self.stage)}

    def run(self, t: dict) -> dict:
        return chay_stage(self.stage, t["params"])


def executors() -> dict[str, P2Exec]:
    return {f"p2_{s}": P2Exec(s) for s in ("classify", "route", "retrieve", "generate", "live")}


P3H_HAN_KEY = "2026-11-13T12:00+07:00"      # V2-06: tới hạn này chưa có key thì không khởi động nhánh


class P3HExec(P2Exec):
    """Nhánh P3H: cùng stage, cùng prompt với P3. `ready` False khi thiếu key: core bỏ qua task, không lỗi, không missed.
    Smoke không khởi động sau hạn; r01 có `after` là smoke cuối nên cũng không khởi động theo."""

    def __init__(self, stage: str, clock=time.time) -> None:
        super().__init__(stage)
        self.kind = f"p3h_{stage}"
        self.clock = clock

    def ready(self, t: dict) -> bool:
        if t["m"] == "P3HS" and self.clock() >= datetime.fromisoformat(P3H_HAN_KEY).timestamp():
            return False
        return backends.key_openrouter() is not None


def executors_p3h() -> dict[str, P3HExec]:
    return {f"p3h_{s}": P3HExec(s) for s in ("route", "generate")}
