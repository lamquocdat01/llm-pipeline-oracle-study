r"""Phân tích nghiên cứu 3 (AMENDMENT V2-08 (g)). Hàm thuần; đọc S3 jsonl + manifest, trả dict số.

Đóng băng TRƯỚC lần đọc dữ liệu thật đầu tiên (FROZEN.md). Không đổi luật sau khi thấy số.
"""
from __future__ import annotations

import json
import math
import random
import re
import unicodedata
from pathlib import Path

STAGES = ("classify", "route", "generate")
CONTROLS = ("C1", "C2", "C3")
KY_VONG = {"P1": "khong_doi", "P2": "doi", "M1": "doi", "K1": "doi", "T1": "artefact_doi_decision_khong_ro",
           "R1-B": "khong_ro", "R1-A2": "khong_ro"}
S1_RUNS = ("P2", "M1", "K1")
S2_RUNS = ("P1",)
B = 2000
SEEDS = (20261112, 20261113, 20261114, 20261115, 20261116)


def chuan_hoa(s: str | None) -> str:
    """= mrunner.oracle.chuan_hoa (luật A04.3), chép để script độc lập; test so khớp với bản gốc."""
    s = unicodedata.normalize("NFC", s or "").lower()
    s = "".join(" " if unicodedata.category(c).startswith("P") else c for c in s)
    return re.sub(r"\s+", " ", s).strip()


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def doc(results: Path, manifest: Path) -> tuple[dict, list[dict]]:
    """runs[(arm, run_name)] = {(stage, qid): item}; chọn bản ok (X trước, X_r nếu X hỏng)."""
    man = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = {(m["arm"], m["run"]) for m in man if m.get("trang_thai") == "ok"}
    raw: dict = {}
    for l in results.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        it = json.loads(l)
        if (it["arm"], it["run"]) not in ok:
            continue
        raw.setdefault((it["arm"], it["bien_the"], it["run"]), {})[(it["stage"], it["qid"])] = it
    runs = {}
    for (arm, bt, run), items in sorted(raw.items()):
        if (arm, bt) in runs and not run.endswith("_r"):
            continue
        if (arm, bt) not in runs or run == bt:
            runs[(arm, bt)] = items
    return runs, man


def do(golden: dict, run: dict, stage: str) -> dict[str, tuple[int, int]]:
    """qid -> (đỏ decision, đỏ artefact) trên test có đủ dữ liệu ở cả hai lần."""
    ra = {}
    for (st, qid), g in golden.items():
        if st != stage or not g.get("ok"):
            continue
        r = run.get((st, qid))
        if not r or not r.get("ok"):
            continue
        ra[qid] = (int(r["decision"] != g["decision"]), int(chuan_hoa(r["artefact"]) != chuan_hoa(g["artefact"])))
    return ra


def boot_delta(x: list[float], m: list[float]) -> dict:
    """Δ = mean(x − m), bootstrap ghép cặp theo test; khoảng rộng nhất qua 5 seed."""
    n = len(x)
    d = [a - b for a, b in zip(x, m)]
    est = sum(d) / n if n else float("nan")
    lo, hi = math.inf, -math.inf
    per = []
    for s in SEEDS:
        rng = random.Random(s)
        bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
        a, b = bs[int(0.025 * B)], bs[int(0.975 * B) - 1]
        per.append([a, b])
        lo, hi = min(lo, a), max(hi, b)
    return {"delta": est, "lo": lo, "hi": hi, "n": n, "per_seed": per}


def dung(stage: str, item: dict, cau) -> bool | None:
    """V2-08 (g): chuẩn ngoài. cau có .impossible, .answers."""
    if not item or not item.get("ok"):
        return None
    if stage == "classify":
        return item["decision"] == ("unanswerable" if cau.impossible else "answerable")
    if stage == "generate":
        if cau.impossible:
            return item["decision"] == "abstain"
        a = chuan_hoa(item["artefact"])
        return item["decision"] != "abstain" and any(chuan_hoa(x) and chuan_hoa(x) in a for x in cau.answers)
    return None


def phan_tich(runs: dict, cau_by_qid: dict) -> dict:
    out: dict = {"arms": {}}
    for arm in sorted({a for a, _ in runs}):
        g = runs.get((arm, "golden"))
        if g is None:
            continue
        ctl = [runs[(arm, c)] for c in CONTROLS if (arm, c) in runs]
        A: dict = {"controls_co": [c for c in CONTROLS if (arm, c) in runs], "runs": {}}
        for (a2, name), run in sorted(runs.items()):
            if a2 != arm or name == "golden":
                continue
            R: dict = {"ky_vong": KY_VONG.get(name, "doi_chung" if name in CONTROLS else "?"), "stages": {}}
            for st in STAGES:
                if not any(k[0] == st for k in run):
                    continue
                dr = do(g, run, st)
                cds = [do(g, c, st) for c in ctl]
                q_ok = [q for q in dr if any(q in c for c in cds)]
                xd = [dr[q][0] for q in q_ok]
                xa = [dr[q][1] for q in q_ok]
                md = [sum(c[q][0] for c in cds if q in c) / sum(1 for c in cds if q in c) for q in q_ok]
                ma = [sum(c[q][1] for c in cds if q in c) / sum(1 for c in cds if q in c) for q in q_ok]
                S: dict = {"n": len(dr), "dec_do": sum(v[0] for v in dr.values()), "art_do": sum(v[1] for v in dr.values()),
                           "n_ghep_doi_chung": len(q_ok)}
                if name not in CONTROLS and q_ok:
                    S["delta_dec"] = boot_delta(xd, md)
                    S["delta_art"] = boot_delta(xa, ma)
                if name in S1_RUNS and "delta_dec" in S:
                    S["S1"] = {"dat": S["delta_dec"]["lo"] > 0}
                if name in S2_RUNS and "delta_dec" in S:
                    yen = S["delta_dec"]["lo"] <= 0 <= S["delta_dec"]["hi"]
                    art = S["delta_art"]["lo"] > 0
                    S["S2"] = {"decision_yen": yen, "artefact_do": art, "dat": yen and art}
                if st in ("classify", "generate"):
                    doi_that, bat_dec, bat_art, bo_sot = [], 0, 0, 0
                    do_dec_that, do_art_that, n_do_dec, n_do_art = 0, 0, 0, 0
                    for q, (rd, ra_) in dr.items():
                        c = cau_by_qid[q]
                        a0, a1 = dung(st, g[(st, q)], c), dung(st, run[(st, q)], c)
                        that = a0 is not None and a1 is not None and a0 != a1
                        if that:
                            doi_that.append(q)
                            bat_dec += rd
                            bat_art += ra_
                            bo_sot += int(ra_ and not rd)
                        n_do_dec += rd
                        n_do_art += ra_
                        do_dec_that += int(rd and that)
                        do_art_that += int(ra_ and that)
                    k = len(doi_that)
                    S["S3"] = {"doi_that": k, "dec_bat": bat_dec, "art_bat": bat_art,
                               "dec_bat_wilson": list(wilson(bat_dec, k)), "art_bat_wilson": list(wilson(bat_art, k)),
                               "dec_do": n_do_dec, "dec_do_doi_that": do_dec_that,
                               "art_do": n_do_art, "art_do_doi_that": do_art_that,
                               "bo_sot_dec_ma_art_bat": bo_sot}
                R["stages"][st] = S
            A["runs"][name] = R
        out["arms"][arm] = A
    return out


def lam_tron(x):
    if isinstance(x, bool) or x is None or isinstance(x, (int, str)):
        return x
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else round(x, 6) + 0.0
    if isinstance(x, dict):
        return {str(k): lam_tron(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [lam_tron(v) for v in x]
    raise TypeError(type(x))
