r"""P6 B1 — tách drift, biến thiên chập chờn và false alarm trên study 2 (addendum mục (b)).

    desktop\.venv\Scripts\python.exe study\analysis_p6\run_b1.py   →  out/numbers_p6_b1.json
"""
from __future__ import annotations

import json
from itertools import combinations

from common import NHAN, RES, av3, ghi_json, HERE  # noqa: F401
from av2 import load as av2load  # noqa: E402
from av2 import oracle_an  # noqa: E402

CAP = oracle_an.CAP


def lop(seq: list) -> str:
    diem = [i for i in range(1, len(seq)) if seq[i] != seq[i - 1]]
    if not diem:
        return "on_dinh"
    if len(diem) >= 2:
        return "chap_chon"
    j = diem[0]
    if j == len(seq) - 1:
        return "chua_phan_loai"
    return "golden_lech" if j == 1 else "drift"


def main() -> int:
    p2o_all = av2load.doc_jsonl(RES / "P2O_20261102_v1.jsonl")
    orc = oracle_an.phan_tich(av2load.ok_theo_id(p2o_all), p2o_all, RES)
    by_id = {r["task_id"]: r for r in p2o_all if r.get("status") == "ok"}

    def obs(tid):
        return {it["key"]: it for it in json.loads((RES / "oracle" / by_id[tid]["payload"]["obs"]).read_text(encoding="utf-8"))["items"]}

    O = {tid: obs(tid) for tid in set(orc["lan_hosted"]) | set(orc["lan_local"])}
    out = {"_nhan": NHAN + " — B1", "golden": orc["golden"], "o": {}}
    for st, be in CAP:
        ds = orc["lan_local"] if be == "local" else orc["lan_hosted"]
        doan = [av2load.rd.doan(by_id[t]["ts"]) for t in ds]
        keys = sorted(k for k in O[ds[0]] if k.startswith(f"{st}|{be}|"))
        R = {}
        for muc, fn in (("decision", lambda it: it["decision"] if it else None),
                        ("artefact", lambda it: av3.chuan_hoa(it["artefact"]) if it else None)):
            dem = {"on_dinh": 0, "drift": 0, "golden_lech": 0, "chap_chon": 0, "chua_phan_loai": 0}
            luot = dict.fromkeys(dem, 0)
            luot_tong = 0
            doi_qua_B = 0
            seqs = {}
            for k in keys:
                s = [fn(O[t].get(k)) for t in ds]
                seqs[k] = s
                c = lop(s)
                dem[c] += 1
                n_do = sum(1 for v in s[1:] if v != s[0])
                luot[c] += n_do
                luot_tong += n_do
                if c in ("drift", "golden_lech"):
                    j = next(i for i in range(1, len(s)) if s[i] != s[i - 1])
                    doi_qua_B += int(doan[j - 1] != doan[j])
            n, m = len(keys), len(ds)
            xoay = []
            for g in range(m):
                xoay.append(sum(sum(1 for k in keys if seqs[k][r] != seqs[k][g]) for r in range(m) if r != g) / (n * (m - 1)))
            cap = [sum(1 for k in keys if seqs[k][i] != seqs[k][j]) / n for i, j in combinations(range(m), 2)]
            R[muc] = {"n_test": n, "so_lan": m, "lop": dem,
                      "luot_do": luot_tong, "luot_do_theo_lop": luot,
                      "ty_le_luot_do_drift": (luot["drift"] + luot["golden_lech"]) / luot_tong if luot_tong else None,
                      "drift_chiem_da_so": (luot["drift"] + luot["golden_lech"]) * 2 >= luot_tong if luot_tong else None,
                      "do_moi_lan_golden_dang_ky": xoay[0], "xoay_golden_tb": sum(xoay) / m,
                      "xoay_golden_min": min(xoay), "xoay_golden_max": max(xoay),
                      "moi_cap_lech_tb": sum(cap) / len(cap), "so_cap": len(cap),
                      "drift_diem_doi_trung_chuyen_doan": doi_qua_B}
        out["o"][f"{st}|{be}"] = R
    ghi_json(HERE / "out" / "numbers_p6_b1.json", out)
    print("B1 xong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
