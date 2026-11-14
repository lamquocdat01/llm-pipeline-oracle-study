r"""POST HOC lần 4 (P3G, 14-11-2026; sau kiểm đóng lỗi vòng 4). Kế hoạch: PLAN_POSTHOC4.md (commit e287aaf, trước lần chạy
đầu). Chỉ đọc đầu ra đã lưu; không gọi model; không thêm ngưỡng mới.

    python study\analysis_v3_posthoc\run_v3_posthoc4.py   →  out/numbers_v3_posthoc4.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
P2 = REPO / "study" / "pipeline2"
sys.path[:0] = [str(HERE), str(REPO / "study" / "analysis_v3"), str(REPO / "study" / "analysis_v2"), str(P2)]
import av3  # noqa: E402
from av2.cells import DV_P2  # noqa: E402
from av2.stats import phan_quyet  # noqa: E402
from p2 import corpus  # noqa: E402
from run_v3_posthoc3 import TAU, f1  # noqa: E402

RES = P2 / "results"
CTL = ("C1", "C2", "C3")


def phan_n() -> dict:
    N = json.loads((REPO / "study" / "analysis_v2" / "out" / "numbers_v2.json").read_text(encoding="utf-8"))
    out = {}
    for bo in ("cung_runtime", "dang_ky"):
        ds = {"matrix": {}, "naive": {}}
        for o in DV_P2:
            d = N["don_vi"][str(o)]
            r = d.get("cap_1to5_dang_ky") if bo == "dang_ky" else None
            k, n, v = (r["k"], r["n"], r["phan_quyet"]) if r else (d["k"], d["n"], d["phan_quyet"])
            ds["matrix"][o] = v
            ds["naive"][o] = phan_quyet("ổn định", k, n)["phan_quyet"]
        x = {}
        for luat, vs in ds.items():
            dung = [o for o, v in vs.items() if v == "đúng"]
            sai = [o for o, v in vs.items() if v == "sai"]
            khac = [o for o, v in vs.items() if v not in ("đúng", "sai")]
            pd = len(dung) + len(sai)
            x[luat] = {"dung": len(dung), "sai": len(sai), "khong_phan_dinh": len(khac), "phan_dinh": pd,
                       "dat_2_3": 3 * len(dung) >= 2 * pd, "o_dung": dung, "o_sai": sai, "o_khong_phan_dinh": khac}
        out[bo] = x
    return out


def phan_fq(a: dict, cau: dict) -> dict:
    tap, theo_cau = [], defaultdict(lambda: {"dung_sang_sai": 0, "sai_sang_dung": 0, "sot": 0})
    for (arm, run), R in sorted(a.items()):
        if run == "golden" or run in CTL:
            continue
        g = a[(arm, "golden")]
        for (st, q), it in sorted(R.items()):
            if st != "generate" or not it.get("ok") or not g.get((st, q), {}).get("ok"):
                continue
            gi = g[(st, q)]
            a0, a1 = av3.dung(st, gi, cau[q]), av3.dung(st, it, cau[q])
            if a0 is None or a1 is None or a0 == a1:
                continue
            chieu = "dung_sang_sai" if a0 else "sai_sang_dung"
            dec = int(it["decision"] != gi["decision"])
            art = int(av3.chuan_hoa(it["artefact"]) != av3.chuan_hoa(gi["artefact"]))
            v = f1(it["artefact"], gi["artefact"])
            tap.append({"arm": arm, "run": run, "qid": q, "chieu": chieu, "dec": dec, "art": art, "sot": int(art and not dec),
                        **{f"F1<{t}": int(v < t) for t in TAU}})
            c = theo_cau[q]
            c["tra_loi_duoc"] = not cau[q].impossible
            c[chieu] += 1
            c["sot"] += int(art and not dec)

    def dem(xs):
        r = {"n": len(xs)}
        for k in ("dec", "art") + tuple(f"F1<{t}" for t in TAU):
            r[k] = sum(x[k] for x in xs)
            for ch in ("dung_sang_sai", "sai_sang_dung"):
                r[f"{k}|{ch}"] = sum(x[k] for x in xs if x["chieu"] == ch)
        for ch in ("dung_sang_sai", "sai_sang_dung"):
            r[f"n|{ch}"] = sum(1 for x in xs if x["chieu"] == ch)
        return r
    return {"truly_changed": dem(tap), "ca_sot": dem([x for x in tap if x["sot"]]),
            "route_field": "không có chuẩn ngoài ở route, nên không có phía phát hiện",
            "theo_cau": dict(sorted(theo_cau.items()))}


def main() -> int:
    a, _ = av3.doc(RES / "S3_20261112_v1.jsonl", RES / "S3_20261112_v1.manifest.jsonl")
    cau = {c.qid: c for c in corpus.nap()[1]}
    N = {"_nhan": "post hoc lần 4 — 14-11-2026, sau kiểm đóng lỗi vòng 4; kế hoạch PLAN_POSTHOC4.md (commit e287aaf)",
         "N": phan_n(), "F": phan_fq(a, cau)}
    N = av3.lam_tron(N)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "numbers_v3_posthoc4.json").write_text(json.dumps(N, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                                          encoding="utf-8", newline="\n")
    print("xong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
