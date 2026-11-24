r"""P6 B2 — đường token-F1, oracle embedding, oracle trường JSON, chuẩn ngoài thay thế (addendum mục (c)).

    desktop\.venv\Scripts\python.exe study\analysis_p6\run_b2.py [--khong-emb]   →  out/numbers_p6_b2.json

Dữ liệu: study 3 (S3), control của V2-09 (S3B), study 2 (P2O, false alarm mỗi lần). Không gọi model sinh.
"""
from __future__ import annotations

import argparse
import json

from common import HERE, NHAN, RES, TAU_EMB, TAU_F1, EMB_MODEL, EMB_REV, Emb, av3, ghi_json, oracle_reds
from s3eval import cap_test, control_reds, thay_doi, tong
from av2 import load as av2load  # noqa: E402
from av2 import oracle_an  # noqa: E402

CTL = ("C1", "C2", "C3")


def keys_cho(st: str, emb: bool) -> list[str]:
    k = ["dec", "art"]
    if st == "generate":
        k += [f"f1<{t}" for t in TAU_F1] + ([f"emb<{t}" for t in TAU_EMB] if emb else [])
    if st == "classify":
        k += ["json"]
    return k


def study3(emb) -> dict:
    a, _ = av3.doc(RES / "S3_20261112_v1.jsonl", RES / "S3_20261112_v1.manifest.jsonl")
    out = {}
    for arm in ("hosted", "local"):
        g = a[(arm, "golden")]
        ctl = [a[(arm, c)] for c in CTL if (arm, c) in a]
        changes = sorted(r for (ar, r) in a if ar == arm and r != "golden" and r not in CTL)
        A = {"controls": {}, "changes": {}}
        for st in ("classify", "route", "generate"):
            A["controls"][st] = control_reds(g, ctl, st, emb)
        for chuan_ten in ("chinh", "sf1"):
            for st in ("classify", "generate"):
                if chuan_ten == "sf1" and st != "generate":
                    continue
                rows_all = []
                theo_run = {}
                for r in changes:
                    rows = thay_doi(g, a[(arm, r)], st, emb, chuan_ten)
                    if not rows:
                        continue
                    theo_run[r] = {"n": len(rows), "that": sum(x["that"] for x in rows),
                                   "dec_sot": sum(1 for x in rows if x["that"] and not x["dec"]),
                                   "that_qids": [x["qid"] for x in rows if x["that"]]}
                    rows_all += [{**x, "run": r} for x in rows]
                A["changes"][f"{st}|{chuan_ten}"] = {"theo_run": theo_run, "tong": tong(rows_all, keys_cho(st, emb is not None)),
                                                    "that": sum(x["that"] for x in rows_all), "n": len(rows_all),
                                                    "sot_theo_chieu": {ch: sum(1 for x in rows_all if x["that"] and not x["dec"] and x["chieu"] == ch)
                                                                       for ch in ("dung_sang_sai", "sai_sang_dung")}}
        # so hai chuẩn ở generate
        lech = cung_that = chi_chinh = chi_sf1 = 0
        from common import cau, dung_sf1
        C = cau()
        for r in changes + ["golden"]:
            for q, gi, it in cap_test(g, a[(arm, r)], "generate"):
                x, y = av3.dung("generate", it, C[q]), dung_sf1(it, C[q])
                lech += int(x != y)
        for r in changes:
            m = {x["qid"]: x["that"] for x in thay_doi(g, a[(arm, r)], "generate", None, "chinh")}
            s = {x["qid"]: x["that"] for x in thay_doi(g, a[(arm, r)], "generate", None, "sf1")}
            for q in m:
                cung_that += int(m[q] and s.get(q, 0))
                chi_chinh += int(m[q] and not s.get(q, 0))
                chi_sf1 += int(s.get(q, 0) and not m[q])
        A["hai_chuan_generate"] = {"test_bat_dong_ve_tinh_dung": lech, "that_ca_hai": cung_that,
                                   "that_chi_chinh": chi_chinh, "that_chi_sf1": chi_sf1}
        out[arm] = A
    return out


def v209(emb) -> dict:
    a, _ = av3.doc(RES / "S3B_20261113_v1.jsonl", RES / "S3B_20261113_v1.manifest.jsonl")
    out = {}
    for arm in ("hosted", "local"):
        if (arm, "golden") not in a:
            continue
        g = a[(arm, "golden")]
        ctl = [a[(arm, c)] for c in CTL if (arm, c) in a]
        out[arm] = {st: control_reds(g, ctl, st, emb) for st in ("classify", "route", "generate")}
    return out


def study2(emb) -> dict:
    p2o_all = av2load.doc_jsonl(RES / "P2O_20261102_v1.jsonl")
    orc = oracle_an.phan_tich(av2load.ok_theo_id(p2o_all), p2o_all, RES)
    by_id = {r["task_id"]: r for r in p2o_all if r.get("status") == "ok"}

    def obs(tid):
        return {it["key"]: it for it in json.loads((RES / "oracle" / by_id[tid]["payload"]["obs"]).read_text(encoding="utf-8"))["items"]}
    out = {}
    for st in ("classify", "route", "generate"):
        for be in ("hosted", "local"):
            ds = orc["lan_local"] if be == "local" else orc["lan_hosted"]
            G = obs(ds[0])
            tong_do, n = {}, 0
            for tid in ds[1:]:
                Ob = obs(tid)
                for k, gi in G.items():
                    if not k.startswith(f"{st}|{be}|"):
                        continue
                    it = Ob.get(k)
                    if it is None:
                        continue
                    n += 1
                    for kk, v in oracle_reds(st, gi, it, emb).items():
                        tong_do[kk] = tong_do.get(kk, 0) + v
            out[f"{st}|{be}"] = {"n_test_lan": n, "ty_le_do_moi_lan": {k: v / n for k, v in tong_do.items()}}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--khong-emb", action="store_true")
    a = ap.parse_args()
    emb = None if a.khong_emb else Emb()
    N = {"_nhan": NHAN + " — B2", "tau_f1": list(TAU_F1), "tau_emb": list(TAU_EMB),
         "emb_model": EMB_MODEL if emb else None, "emb_rev": EMB_REV if emb else None,
         "study3": study3(emb), "v209_controls": v209(emb), "study2": study2(emb)}
    ghi_json(HERE / "out" / "numbers_p6_b2.json", N)
    print("B2 xong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
