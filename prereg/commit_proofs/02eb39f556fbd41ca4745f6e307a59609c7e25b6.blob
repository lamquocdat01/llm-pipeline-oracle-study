"""Dữ liệu GIẢ cùng schema với study/pipeline2/results (V2-05 D2: chạy thử script trước khi đọc dữ liệu thật).

Sinh từ schema (task_id, ts, payload) với seed cố định; dạng thời gian mô phỏng ba đoạn runtime A/B/D của V2-07
và các mốc P2O lỡ. Xác suất đổi là tham số tuỳ ý, KHÔNG lấy từ dữ liệu thật.
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from av2.load import chuan_hoa  # noqa: E402

TZ = "+07:00"
T0 = datetime.fromisoformat("2026-11-02T00:00:00" + TZ)
B0 = datetime.fromisoformat("2026-11-03T21:00:00" + TZ)
D0 = datetime.fromisoformat("2026-11-07T12:00:00" + TZ)
H = timedelta(hours=1)
QIDS = [f"{0xa000 + i:024x}" for i in range(200)]
ORACLE_Q = QIDS[5:45]
LABELS = {"classify": ["answerable", "unanswerable"], "route": ["RETRIEVE", "ANSWER", "REFUSE"],
          "generate": ["gold", "other", "nocite", "abstain"], "live": ["SOURCES", "NO_SOURCES"]}


def iso(t: datetime) -> str:
    return t.isoformat(timespec="milliseconds")


def rec(tid: str, ts: datetime, payload: dict, status: str = "ok", **kw) -> dict:
    return {"task_id": tid, "m": tid.split("|")[0], "ts": iso(ts), "due": kw.get("due"), "late_by_s": kw.get("late"),
            "manifest_ref": "fake", "hf_offline": True, "status": status, "ts_end": iso(ts + timedelta(seconds=3)),
            "usage": None, "payload": payload}


class Chuoi:
    """Giá trị một (câu × stage × nhánh) qua các lần: mỗi lần, xác suất p_art đổi artefact; trong đó p_dec đổi cả decision."""

    def __init__(self, rng: random.Random, stage: str, p_art: float, p_dec: float):
        self.rng, self.stage, self.p_art, self.p_dec = rng, stage, p_art, p_dec
        labs = LABELS.get(stage, ["x"])
        self.dec0 = rng.choice(labs) if rng.random() > 0.03 else "PARSE_FAIL"
        self.labs = labs

    def mot(self, boost: float = 0.0) -> tuple[str, str]:
        r = self.rng
        if r.random() < min(1.0, self.p_art + boost):
            d = r.choice(self.labs + ["PARSE_FAIL"]) if r.random() < self.p_dec else self.dec0
            return d, f"{d} -- text variant {r.randint(1, 10 ** 6)}"
        if r.random() < 0.3:                                 # chỉ đổi hoa/thường + dấu câu: chuan_hoa coi là bằng
            return self.dec0, f"{self.dec0.upper()} -- TEXT, VARIANT 0!"
        return self.dec0, f"{self.dec0} -- text variant 0"


def make(out: Path, seed: int = 20261111) -> Path:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    (out / "oracle").mkdir(exist_ok=True)
    p2, p3, p3h, md3, md3r = [], [], [], [], []

    def ts_run(kind: str, k: int, qi: int) -> datetime:
        off = timedelta(seconds=qi * 7)
        if kind in ("hosted", "bm25"):
            return T0 + (k - 1) * 7 * H + off
        if kind == "local":                                  # r01 A (trừ qi % 10 == 0: B), r02–r03 B, r04+ D
            if k == 1:
                return (B0 if qi % 10 == 0 else T0 + H) + off
            if k <= 3:
                return B0 + (k - 1) * 4 * H + off
            return D0 + (k - 4) * 7 * H + off
        if kind == "p3h":
            return datetime.fromisoformat("2026-11-08T00:00:00" + TZ) + (k - 1) * 7 * H + off
        raise ValueError(kind)

    def payload(stage: str, d: str, a: str) -> dict:
        if stage == "retrieve":
            return {"decision": d, "artefact": a, "gold_in_topk": True, "scores": [1.0]}
        if stage == "live":
            doms = "" if d == "NO_SOURCES" else ",".join(sorted({f"s{rng.randint(1, 3)}.org", "wiki.org"}))
            return {"decision": "SOURCES" if doms else "NO_SOURCES", "artefact": a, "artefact_domains": doms}
        return {"decision": d, "artefact": a}

    for qi, q in enumerate(QIDS):
        for stage in ("classify", "route", "generate", "retrieve", "live"):
            for be in (("hosted", "local") if stage in ("classify", "route", "generate") else
                       ("bm25",) if stage == "retrieve" else ("hosted",)):
                if stage == "live" and qi >= 50:
                    continue
                pa = {"hosted": 0.35, "local": 0.03, "bm25": 0.0}[be]
                c = Chuoi(rng, stage, pa, 0.15)
                for k in range(1, 11):
                    seg_b = be == "local" and 2 <= k <= 3
                    d, a = c.mot(0.4 if seg_b else 0.0)
                    p2.append(rec(f"P2|{stage}|{be}|{q}|r{k:02d}", ts_run("hosted" if be == "bm25" else be, k, qi),
                                  payload(stage, d, a)))
                if qi < 20 and stage != "retrieve":
                    for tag in (("t08",) if be == "hosted" else ("t08", "seed1")):
                        d, a = c.mot(0.6)
                        p2.append(rec(f"P2|{stage}|{be}|{q}@{tag}|probe", T0 + 2 * H, payload(stage, d, a)))
        for stage in ("route", "generate"):
            c = Chuoi(rng, stage, 0.04, 0.2)
            for k in range(1, 11):
                d, a = c.mot(0.4 if 2 <= k <= 3 else 0.0)
                p3.append(rec(f"P3|{stage}|local|{q}|r{k:02d}", ts_run("local", k, qi), {"decision": d, "artefact": a}))
            if qi < 20:
                for tag in ("t08", "seed1"):
                    d, a = c.mot(0.6)
                    p3.append(rec(f"P3|{stage}|local|{q}@{tag}|probe", T0 + 3 * H, {"decision": d, "artefact": a}))
            c = Chuoi(rng, stage, 0.3, 0.1)
            for k in range(1, 6):
                d, a = c.mot()
                p3h.append(rec(f"P3H|{stage}|openrouter|{q}|r{k:02d}", ts_run("p3h", k, qi),
                               {"decision": d, "artefact": a}))
    # MD3 (cũ, bắc cầu) + MD3R
    for sub, n in (("M2", 100), ("M4", 50)):
        for i in range(n):
            item = f"{sub.lower()}-{i:03d}"
            c = Chuoi(rng, "x", 0.05, 0.3)

            def pl(boost=0.0):
                d, a = c.mot(boost)
                return ({"lookup": d.endswith("1"), "premise": False, "raw_text": a} if sub == "M2" else
                        {"lang_label": "vi" if len(d) % 2 else "en", "reply_text": a})
            t0 = (B0 if i % 2 else T0) + timedelta(seconds=i * 11)
            base = f"MD3|{sub}|{item}|llama3.1:8b"
            md3 += [rec(f"{base}|t0", t0, pl()), rec(f"{base}|t0p", t0 + timedelta(minutes=1), pl()),
                    rec(f"{base}|t24h", t0 + 25 * H, pl(0.3 if i % 2 else 0.0))]
            md3 += [rec(f"{base}@{tag}|probe", t0 + timedelta(minutes=2), pl(0.6)) for tag in ("seed1", "t08")]
            t0r = datetime.fromisoformat("2026-11-08T00:30:00" + TZ) + timedelta(seconds=i * 11)
            br = f"MD3R|{sub}|{item}|llama3.1:8b"
            md3r += [rec(f"{br}|t0", t0r, pl()), rec(f"{br}|t24h", t0r + 25 * H, pl())]
    # P2O: lan01 golden (A), lan02 + lan05–16 missed, lan03–04 (B), lan17+ (D), lan20 + lan36 missed
    p2o = []
    chains = {(st, be, q): Chuoi(rng, st, {"hosted": 0.4, "local": 0.0, "bm25": 0.0}[be], 0.1)
              for st, be in (("classify", "hosted"), ("classify", "local"), ("route", "hosted"), ("route", "local"),
                             ("retrieve", "bm25"), ("generate", "hosted"), ("generate", "local")) for q in ORACLE_Q}
    golden = None
    for lan in range(1, 42):
        due = datetime.fromisoformat("2026-11-03T12:00:00" + TZ) + (lan - 1) * 6 * H
        if lan == 1:
            due = datetime.fromisoformat("2026-11-03T12:00:00" + TZ)
        if lan in (2, 20, 36) or 5 <= lan <= 16:
            p2o.append(rec(f"P2O|lan{lan:02d}", due + 3 * H, None, status="missed", due=iso(due), late=10800.0))
            continue
        seg_b = lan in (3, 4)
        items = []
        for (st, be, q), c in chains.items():
            d, a = c.mot(0.5 if (seg_b and be == "local") else 0.0)
            items.append({"key": f"{st}|{be}|{q}", "stage": st, "backend": be, "qid": q, "decision": d, "artefact": a})
        name = f"obs_lan{lan:02d}.json"
        (out / "oracle" / name).write_text(json.dumps({"lan": lan, "task_id": f"P2O|lan{lan:02d}", "items": items},
                                                      ensure_ascii=False), encoding="utf-8")
        pl = {"lan": lan, "obs": name, "obs_sha256": "fake", "n_items": len(items)}
        if golden is None:
            golden = {it["key"]: it for it in items}
            pl["golden"] = True
        else:
            run = {it["key"]: it for it in items}
            fd = sorted(k for k in golden if run[k]["decision"] != golden[k]["decision"])
            fa = sorted(k for k in golden if chuan_hoa(run[k]["artefact"]) != chuan_hoa(golden[k]["artefact"]))
            pl["golden_obs"] = "obs_lan01.json"
            pl["decision"] = {"n": 280, "passed": 280 - len(fd), "failed": fd, "rc": int(bool(fd))}
            pl["artefact"] = {"n": 280, "passed": 280 - len(fa), "failed": fa, "rc": int(bool(fa))}
        p2o.append(rec(f"P2O|lan{lan:02d}", due + timedelta(seconds=30), pl, due=iso(due), late=30.0))
    for ten, rs in (("P2", p2), ("P3", p3), ("P3H", p3h), ("MD3", md3), ("MD3R", md3r), ("P2O", p2o)):
        (out / f"{ten}_20261102_v1.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs),
                                                      encoding="utf-8", newline="\n")
    return out
