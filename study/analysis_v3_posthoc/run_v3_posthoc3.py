r"""POST HOC lần 3 (P3F, 14-11-2026; sau phản biện nội bộ vòng 4). Kế hoạch: PLAN_POSTHOC3.md (commit 6091f5a, trước lần
chạy đầu). Chỉ đọc đầu ra đã lưu; không gọi model; không đổi verdict đăng ký nào.

    python study\analysis_v3_posthoc\run_v3_posthoc3.py   →  out/numbers_v3_posthoc3.json
"""
from __future__ import annotations

import json
import math
import random
import re
import string
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
P2 = REPO / "study" / "pipeline2"
sys.path[:0] = [str(REPO / "study" / "analysis_v3"), str(REPO / "study" / "analysis_v2"), str(P2)]
import av3  # noqa: E402
from av2 import load as av2load  # noqa: E402
from av2 import oracle_an  # noqa: E402
from p2 import corpus  # noqa: E402

RES = P2 / "results"
CTL = ("C1", "C2", "C3")
TAU = (0.8, 0.5)                      # cố định trong PLAN_POSTHOC3.md trước khi chạy
B = av3.B
SEEDS = av3.SEEDS


# ---------------------------------------------------------------- tiện ích
def cluster_ratio(groups: list[tuple[float, float]]) -> dict:
    """groups = [(tử, mẫu)] mỗi cụm; ước lượng Σtử/Σmẫu; bootstrap cụm, khoảng rộng nhất qua 5 seed."""
    n = len(groups)
    num, den = sum(g[0] for g in groups), sum(g[1] for g in groups)
    est = num / den if den else float("nan")
    lo, hi = math.inf, -math.inf
    for s in SEEDS:
        rng = random.Random(s)
        bs = []
        for _ in range(B):
            a = b = 0.0
            for _ in range(n):
                g = groups[rng.randrange(n)]
                a += g[0]
                b += g[1]
            bs.append(a / b if b else 0.0)
        bs.sort()
        lo, hi = min(lo, bs[int(0.025 * B)]), max(hi, bs[int(0.975 * B) - 1])
    return {"k": num, "n": den, "ty_le": est, "lo": lo, "hi": hi, "so_cum": n}


def fisher_2x2(a: int, b: int, c: int, d: int) -> float:
    """p hai phía (tổng xác suất các bảng có xác suất ≤ bảng quan sát), lề cố định."""
    r1, c1, n = a + b, a + c, a + b + c + d

    def p(x):
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)
    p0 = p(a)
    return min(1.0, sum(p(x) for x in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if p(x) <= p0 * (1 + 1e-9)))


_ART = re.compile(r"\b(a|an|the)\b")


def norm_squad(s: str) -> list[str]:
    s = (s or "").lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = _ART.sub(" ", s)
    return s.split()


def f1(a: str, b: str) -> float:
    x, y = norm_squad(a), norm_squad(b)
    if not x and not y:
        return 1.0
    if not x or not y:
        return 0.0
    common = sum((Counter(x) & Counter(y)).values())
    if common == 0:
        return 0.0
    p, r = common / len(x), common / len(y)
    return 2 * p * r / (p + r)


def route_field(s: str) -> str:
    for line in (s or "").splitlines():
        t = av3.chuan_hoa(line)
        if t.startswith("route"):
            return t
    return av3.chuan_hoa(s)


# ---------------------------------------------------------------- Q
def phan_q(a: dict, cau: dict, b: dict) -> dict:
    by_q = defaultdict(lambda: [0, 0])            # qid → [thay đổi, sót]  (mọi câu)
    chéo = defaultdict(lambda: {"thay_doi": 0, "sot": 0})
    ca = []
    for (arm, run), R in sorted(a.items()):
        if run == "golden" or run in CTL:
            continue
        g = a[(arm, "golden")]
        for (st, q), it in sorted(R.items()):
            if st != "generate" or not it.get("ok") or not g.get((st, q), {}).get("ok"):
                continue
            a0, a1 = av3.dung(st, g[(st, q)], cau[q]), av3.dung(st, it, cau[q])
            if a0 is None or a1 is None or a0 == a1:
                continue
            chieu = "dung_sang_sai" if a0 else "sai_sang_dung"
            nhom = "khong_tra_loi_duoc" if cau[q].impossible else "tra_loi_duoc"
            ra = av3.chuan_hoa(it["artefact"]) != av3.chuan_hoa(g[(st, q)]["artefact"])
            sot = int(ra and it["decision"] == g[(st, q)]["decision"])
            by_q[(q, nhom)][0] += 1
            by_q[(q, nhom)][1] += sot
            k = f"{arm}|{chieu}|{nhom}"
            chéo[k]["thay_doi"] += 1
            chéo[k]["sot"] += sot
            if sot:
                ca.append({"arm": arm, "run": run, "qid": q, "chieu": chieu, "decision": it["decision"],
                           "golden": g[(st, q)]["artefact"][:160], "lan_chay": it["artefact"][:160]})
    tl = [(v[1], v[0]) for (q, nh), v in by_q.items() if nh == "tra_loi_duoc"]
    tat_ca = [(v[1], v[0]) for v in by_q.values()]
    q_sot = sorted({c["qid"] for c in ca})
    mo_ta = []
    for q in q_sot:
        c = cau[q]
        mo_ta.append({"qid": q, "cau_hoi": c.question, "dap_an_vang": list(dict.fromkeys(c.answers))[:3],
                      "ca": [{k: x[k] for k in ("arm", "run", "chieu", "decision", "golden", "lan_chay")} for x in ca if x["qid"] == q]})

    # mức nền: "truly changed" trên mỗi đối chứng
    def truly(g, R):
        t = 0
        for (st, q), it in R.items():
            if st != "generate" or not it.get("ok") or not g.get((st, q), {}).get("ok"):
                continue
            a0, a1 = av3.dung(st, g[(st, q)], cau[q]), av3.dung(st, it, cau[q])
            t += int(a0 is not None and a1 is not None and a0 != a1)
        return t
    nen = {}
    for arm in ("hosted", "local"):
        g = a[(arm, "golden")]
        doi = [r for (ar, r) in a if ar == arm and r not in CTL and r != "golden"]
        quan_sat = sum(truly(g, a[(arm, r)]) for r in doi)
        ctl3 = [truly(g, a[(arm, c)]) for c in CTL if (arm, c) in a]
        x = {"so_lan_thay_doi": len(doi), "truly_changed_quan_sat": quan_sat, "doi_chung_s3": ctl3,
             "ky_vong_s3": len(doi) * sum(ctl3) / len(ctl3), "vuot_s3": quan_sat - len(doi) * sum(ctl3) / len(ctl3)}
        if arm == "local":
            ctl9 = [truly(g, b[("local", c)]) for c in CTL]
            x.update(doi_chung_v209=ctl9, ky_vong_v209=len(doi) * sum(ctl9) / 3, vuot_v209=quan_sat - len(doi) * sum(ctl9) / 3)
        nen[arm] = x
    return {"cau_tra_loi_duoc_co_thay_doi": len(tl), "cau_co_thay_doi_tat_ca": len(tat_ca),
            "cau_co_ca_sot": len(q_sot), "cau_tra_loi_duoc_co_ca_sot": sum(1 for v in tl if v[0] > 0),
            "cluster_10_58": cluster_ratio(tat_ca), "cluster_10_28": cluster_ratio(tl),
            "bang_cheo": dict(sorted(chéo.items())),
            "chieu_trung_nhanh": all(v["thay_doi"] == 0 for k, v in chéo.items()
                                     if k.endswith("tra_loi_duoc") and not k.endswith("khong_tra_loi_duoc")
                                     and ((k.startswith("hosted") and "sai_sang_dung" in k)
                                          or (k.startswith("local") and "dung_sang_sai" in k))),
            "muc_nen": nen, "mo_ta_cau_sot": mo_ta}


# ---------------------------------------------------------------- O
def do_test(stage: str, g: dict, it: dict | None, c) -> dict | None:
    """Mọi oracle cho một test; None nếu thiếu dữ liệu."""
    if it is None or not g:
        return None
    r = {"D": int(it["decision"] != g["decision"]),
         "A": int(av3.chuan_hoa(it["artefact"]) != av3.chuan_hoa(g["artefact"]))}
    if stage == "route":
        r["A_route"] = int(route_field(it["artefact"]) != route_field(g["artefact"]))
    if stage == "generate":
        v = f1(it["artefact"], g["artefact"])
        r["F1"] = v
        for t in TAU:
            r[f"F1<{t}"] = int(v < t)
    if stage in ("classify", "generate") and c is not None:
        a0 = av3.dung(stage, {"ok": True, **g}, c)
        a1 = av3.dung(stage, {"ok": True, **it}, c)
        r["E"] = None if (a0 is None or a1 is None) else int(a0 != a1)
    return r


def tong_hop(per_run: list[dict[str, dict]]) -> dict:
    """per_run: [ {qid: kết quả do_test} ] theo lần chạy (không kể golden)."""
    qs = sorted(set().union(*[set(x) for x in per_run]))
    keys = sorted({k for x in per_run for v in x.values() if v for k in v if k != "F1"})
    out = {"so_lan": len(per_run), "so_test": len(qs)}
    for k in keys:
        groups, theo_lan, luy_ke = [], [], 0
        for q in qs:
            vals = [x[q][k] for x in per_run if q in x and x[q] and x[q].get(k) is not None]
            groups.append((sum(vals), len(vals)))
            luy_ke += int(any(vals))
        for x in per_run:
            vals = [v[k] for v in x.values() if v and v.get(k) is not None]
            theo_lan.append(sum(vals) / len(vals) if vals else float("nan"))
        cr = cluster_ratio([g for g in groups if g[1]])
        out[k] = {"moi_lan_tb": cr["ty_le"], "moi_lan_lo": cr["lo"], "moi_lan_hi": cr["hi"],
                  "moi_lan_min": min(theo_lan), "moi_lan_max": max(theo_lan),
                  "do_it_nhat_mot_lan": luy_ke, "n_test": sum(1 for g in groups if g[1])}
    out["D_do_ma_A_khong"] = sum(1 for x in per_run for v in x.values() if v and v["D"] and not v["A"])
    return out


def phan_o(a: dict, cau: dict) -> dict:
    p2o_all = av2load.doc_jsonl(RES / "P2O_20261102_v1.jsonl")
    orc = oracle_an.phan_tich(av2load.ok_theo_id(p2o_all), p2o_all, RES)
    by_id = {r["task_id"]: r for r in p2o_all if r.get("status") == "ok"}

    def obs(tid):
        return {it["key"]: it for it in json.loads((RES / "oracle" / by_id[tid]["payload"]["obs"]).read_text(encoding="utf-8"))["items"]}
    G = obs(orc["golden"])
    nc2 = {}
    for st in ("classify", "route", "generate"):
        for be in ("hosted", "local"):
            ds = orc["lan_local"] if be == "local" else orc["lan_hosted"]
            runs = []
            for tid in ds[1:]:
                O = obs(tid)
                x = {}
                for key, g in G.items():
                    if not key.startswith(f"{st}|{be}|"):
                        continue
                    q = key.split("|")[2]
                    x[q] = do_test(st, g, O.get(key), cau.get(q))
                runs.append(x)
            nc2[f"{st}|{be}"] = tong_hop(runs)
    s3 = {}
    for arm in ("hosted", "local"):
        g = a[(arm, "golden")]
        for st in ("classify", "route", "generate"):
            runs = []
            for c in CTL:
                if (arm, c) not in a:
                    continue
                R = a[(arm, c)]
                x = {}
                for (s, q), gi in g.items():
                    if s != st or not gi.get("ok"):
                        continue
                    it = R.get((s, q))
                    x[q] = do_test(st, gi, it if it and it.get("ok") else None, cau[q])
                runs.append(x)
            if runs:
                s3[f"{st}|{arm}"] = tong_hop(runs)
    return {"nc2": nc2, "nc2_so_lan_hosted": len(orc["lan_hosted"]) - 1, "nc2_so_lan_local": len(orc["lan_local"]) - 1,
            "s3_doi_chung": s3, "tau": list(TAU)}


# ---------------------------------------------------------------- S
def phan_s(a: dict) -> dict:
    out = {}
    for f in ("P2_20261102_v1.jsonl", "P3_20261102_v1.jsonl"):
        d = defaultdict(set)
        n = 0
        for l in (RES / f).read_text(encoding="utf-8").splitlines():
            x = json.loads(l)
            p = x.get("payload") or {}
            if x.get("status") != "ok" or p.get("prompt_eval_count") is None:
                continue
            t = x["task_id"].split("|")
            d[(p.get("model_alias"), t[1], t[3])].add(p["prompt_eval_count"])
            n += 1
        out[f] = {"so_loi_goi": n, "so_prompt": len(d), "prompt_co_nhieu_gia_tri": sum(len(v) > 1 for v in d.values())}
    p2o = {json.loads(l)["payload"]["obs"]: json.loads(l) for l in (RES / "P2O_20261102_v1.jsonl").read_text(encoding="utf-8").splitlines()
           if json.loads(l).get("status") == "ok"}
    p2o_all = av2load.doc_jsonl(RES / "P2O_20261102_v1.jsonl")
    orc = oracle_an.phan_tich(av2load.ok_theo_id(p2o_all), p2o_all, RES)
    by_id = {r["task_id"]: r for r in p2o_all if r.get("status") == "ok"}
    gold = None
    rows = []
    for tid in orc["lan_local"]:
        r = by_id[tid]
        d = json.loads((RES / "oracle" / r["payload"]["obs"]).read_text(encoding="utf-8"))
        its = {it["qid"]: it["artefact"] for it in d["items"] if it["stage"] == "generate" and it["backend"] == "local"}
        v = tuple(av3.chuan_hoa(its[q]) for q in sorted(its))
        if gold is None:
            gold = v
        ts = datetime.fromisoformat(r["ts"])
        rows.append({"lan": r["payload"]["lan"], "ts": r["ts"], "gio_moc": ts.hour, "dem": ts.hour < 8,
                     "phut": round((datetime.fromisoformat(r["ts_end"]) - ts).total_seconds() / 60, 1),
                     "trung_golden": v == gold, "golden": tid == orc["golden"]})
    for i, x in enumerate(rows):
        x["cach_lan_truoc_h"] = None if i == 0 else round(
            (datetime.fromisoformat(x["ts"]) - datetime.fromisoformat(rows[i - 1]["ts"])).total_seconds() / 3600, 1)
    sau = [x for x in rows if not x["golden"]]
    a_, b_ = sum(1 for x in sau if x["dem"] and not x["trung_golden"]), sum(1 for x in sau if x["dem"] and x["trung_golden"])
    c_, d_ = sum(1 for x in sau if not x["dem"] and not x["trung_golden"]), sum(1 for x in sau if not x["dem"] and x["trung_golden"])
    out["nc2_local_generate"] = {"lan": rows, "dem_lech": a_, "dem_trung": b_, "ngay_lech": c_, "ngay_trung": d_,
                                 "fisher_p": fisher_2x2(a_, b_, c_, d_),
                                 "phut_trung_tb": sum(x["phut"] for x in sau if x["trung_golden"]) / max(1, b_ + d_),
                                 "phut_lech_tb": sum(x["phut"] for x in sau if not x["trung_golden"]) / max(1, a_ + c_)}
    return out


def main() -> int:
    a, _ = av3.doc(RES / "S3_20261112_v1.jsonl", RES / "S3_20261112_v1.manifest.jsonl")
    b, _ = av3.doc(RES / "S3B_20261113_v1.jsonl", RES / "S3B_20261113_v1.manifest.jsonl")
    cau = {c.qid: c for c in corpus.nap()[1]}
    N = {"_nhan": "post hoc lần 3 — 14-11-2026, sau phản biện vòng 4; kế hoạch PLAN_POSTHOC3.md (commit 6091f5a)",
         "Q": phan_q(a, cau, b), "O": phan_o(a, cau), "S": phan_s(a)}
    N = av3.lam_tron(N)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "numbers_v3_posthoc3.json").write_text(json.dumps(N, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                                          encoding="utf-8", newline="\n")
    print("xong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
