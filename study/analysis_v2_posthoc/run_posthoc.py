r"""POST HOC trên dữ liệu nghiên cứu 2 đã khoá (P3C Việc 4; R2 mục 9 việc 7, 10, 12). Viết 12-11-2026, SAU khi đã biết
mọi kết quả nghiên cứu 2 và đọc phản biện R2. KHÔNG thay kết luận H nào đã đăng ký. Mọi khối mang nhãn "post hoc".

    desktop\.venv\Scripts\python.exe study\analysis_v2_posthoc\run_posthoc.py

Dùng lại (chỉ đọc) các hàm của `study/analysis_v2/av2` (đã đóng băng). Xuất `out/numbers_v2_posthoc.json` tất định.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "study" / "analysis_v2"))
import numpy as np  # noqa: E402

from av2 import logit, oracle_an  # noqa: E402
from av2.cells import BY_O, DV_N3, DV_P2, DV_P3H, H1_O, cap_o, chi_muc, gia_tri  # noqa: E402
from av2.load import DATA_THAT, FILES, chuan_hoa, doc_jsonl, nap, rd  # noqa: E402
from av2.stats import ON, phan_quyet, wilson  # noqa: E402

NHAN = "post hoc — viết 12-11-2026 sau khi biết kết quả N4 và đọc R2; không thay kết luận H đã đăng ký"
SEEDS = [20261112, 20261113, 20261114, 20261115, 20261116]
B = 2000
Z = 1.959963984540054


def newcombe_cap(a: int, b: int, c: int, d: int) -> dict:
    """Hiệu hai tỉ lệ GHÉP CẶP (p1 − p2), Newcombe 1998 phương pháp 10. a: cả hai, b: chỉ 1, c: chỉ 2, d: không."""
    n = a + b + c + d
    p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n)
    l2, u2 = wilson(a + c, n)
    den = (a + b) * (c + d) * (a + c) * (b + d)
    phi = (a * d - b * c) / math.sqrt(den) if den > 0 else 0.0
    D = p1 - p2
    lo = D - math.sqrt(max(0.0, (p1 - l1) ** 2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2) ** 2))
    hi = D + math.sqrt(max(0.0, (u1 - p1) ** 2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2) ** 2))
    return {"a": a, "b": b, "c": c, "d": d, "n": n, "delta": D, "lo": lo, "hi": hi}


def tom(verdicts: list[str]) -> dict:
    return {v: sum(x == v for x in verdicts) for v in ("đúng", "sai", "không phân định")}


def don_vi_theo(chuoi, os_, luat_local: str | None, md3_goc: bool = False) -> dict:
    ra = {}
    for o in os_:
        c = BY_O[o]
        if c.nguon == "MD3R" and md3_goc:
            ps = cap_o(chuoi, c, "md3r", nguon="MD3")
        elif c.cap == "cung_runtime" and luat_local:
            ps = cap_o(chuoi, c, luat_local)
        else:
            ps = cap_o(chuoi, c)
        k, n = sum(p["doi"] for p in ps), len(ps)
        ra[o] = {**phan_quyet(c.du_doan, k, n), "du_doan": c.du_doan}
    return ra


def dem_don_vi(chuoi) -> dict:
    out = {"nhan": NHAN}
    bien = {"chinh_V2-07_cung_runtime": (None, False), "cap_dang_ky_1to5": ("1to5", False),
            "cap_dang_ky_1to5_MD3_goc": ("1to5", True)}
    for ten, (luat, md3) in bien.items():
        dv = don_vi_theo(chuoi, DV_P2 + DV_N3 + DV_P3H, luat, md3)
        v17 = [dv[o]["phan_quyet"] for o in DV_P2 + DV_N3]
        vp2 = [dv[o]["phan_quyet"] for o in DV_P2]
        dp = sum(x != "không phân định" for x in vp2)
        out[ten] = {"17": tom(v17), "p3h_4": tom([dv[o]["phan_quyet"] for o in DV_P3H]),
                    "h3_du_doan": {"dung": vp2.count("đúng"), "phan_dinh": dp, "can": math.ceil(2 * dp / 3)},
                    "o": {str(o): {k: dv[o][k] for k in ("k", "n", "phan_quyet")} for o in DV_P2 + DV_N3 + DV_P3H}}
    # luật ngây thơ "mọi thứ ổn định" trên cặp chính
    dv = don_vi_theo(chuoi, DV_P2 + DV_N3 + DV_P3H, None)
    ng = {o: phan_quyet(ON, dv[o]["k"], dv[o]["n"])["phan_quyet"] for o in DV_P2 + DV_N3 + DV_P3H}
    out["ngay_tho_moi_thu_on_dinh"] = {"17": tom([ng[o] for o in DV_P2 + DV_N3]),
                                       "p3h_4": tom([ng[o] for o in DV_P3H]),
                                       "o": {str(o): ng[o] for o in DV_P2 + DV_N3 + DV_P3H}}
    sat = [o for o in DV_P2 + DV_N3 + DV_P3H if dv[o]["k"] == 10 and dv[o]["n"] == 200]
    out["sat_nguong_10_200"] = sat
    return out


def oracle_ghep(N2: dict) -> dict:
    """Khoảng ghép cặp cho bảng oracle: decision đỏ ⊂ artefact đỏ (0 trường hợp ngược) ⇒ hiệu = tỉ lệ chỉ-artefact."""
    ra = {"nhan": NHAN}
    for k, o in N2["oracle"]["o"].items():
        a, b, c = o["ghep_ca_hai_do"], o["ghep_art_do_dec_khong"], o["ghep_dec_do_art_khong"]
        d = o["n_tests"] - a - b - c
        ra[k] = {**newcombe_cap(a, b, c, d), "newcombe_doc_lap_da_dang_ky": [o["margin_margin"], o["margin_lo"],
                                                                          o["margin_hi"]],
                 "wilson_ty_le_chi_artefact_do": list(wilson(b, o["n_tests"])) if c == 0 else None,
                 "p_dec_do_khi_art_do": (a / (a + b)) if a + b else None}
    return ra


def margin_ghep(chuoi) -> dict:
    """Margin M-protocol (decision vs artefact, cùng câu) với khoảng ghép cặp."""
    from av2.cells import CAP_MARGIN
    ra = {"nhan": NHAN}
    for ten, (od, oa) in CAP_MARGIN.items():
        pd = {p["q"]: p["doi"] for p in cap_o(chuoi, BY_O[od])}
        pa = {p["q"]: p["doi"] for p in cap_o(chuoi, BY_O[oa])}
        qs = sorted(set(pd) & set(pa))
        if not qs:
            continue
        a = sum(pa[q] and pd[q] for q in qs)
        b = sum(pa[q] and not pd[q] for q in qs)
        c = sum(pd[q] and not pa[q] for q in qs)
        ra[ten] = newcombe_cap(a, b, c, len(qs) - a - b - c)
    return ra


def doi_chung_ghep(chuoi) -> dict:
    """V2-06 với khoảng ghép cặp: artefact đổi ở P3H (hosted Llama) so với P3 local, cùng câu."""
    ra = {"nhan": NHAN}
    for st, (oh, ol) in (("route", (27, 19)), ("generate", (29, 21))):
        ph = {p["q"]: p["doi"] for p in cap_o(chuoi, BY_O[oh])}
        pl = {p["q"]: p["doi"] for p in cap_o(chuoi, BY_O[ol])}
        qs = sorted(set(ph) & set(pl))
        a = sum(ph[q] and pl[q] for q in qs)
        b = sum(ph[q] and not pl[q] for q in qs)
        c = sum(pl[q] and not ph[q] for q in qs)
        ra[st] = newcombe_cap(a, b, c, len(qs) - a - b - c)
    return ra


def _hang(cap_fn, os_):
    X, y, cl_q, cl_o = [], [], [], []
    for o in os_:
        c = BY_O[o]
        for p in cap_fn(c):
            X.append([1.0, c.do_sau, 1.0 if c.pin == "pinnable" else 0.0, 1.0 if c.obs == "art" else 0.0])
            y.append(0.0 if p["doi"] else 1.0)
            cl_q.append("Q:" + p["q"])
            cl_o.append(f"O:{o}")
    return np.array(X), np.array(y), np.array(cl_q), np.array(cl_o)


def h1_bien_the(chuoi) -> dict:
    ten = ["const", "depth", "pinnable", "artefact"]
    ra = {"nhan": NHAN}
    X, y, clq, clo = _hang(lambda c: cap_o(chuoi, c), H1_O)
    ra["cluster_theo_o_15"] = logit.mo_hinh(X, y, clo, ten, B, SEEDS)
    Xc = np.column_stack([X[:, 0], X[:, 2], X[:, 3]] + [(X[:, 1] == d).astype(float) for d in (2, 3, 4)])
    ra["depth_phan_loai_ML_cluster_cau"] = logit.mo_hinh(Xc, y, clq, ["const", "pinnable", "artefact", "depth2",
                                                                       "depth3", "depth4"], B, SEEDS)
    Xr, yr, clqr, _ = _hang(lambda c: cap_o(chuoi, c, "1to5") if c.cap == "cung_runtime" else cap_o(chuoi, c), H1_O)
    ra["cap_dang_ky_1to5"] = logit.mo_hinh(Xr, yr, clqr, ten, B, SEEDS)
    # bỏ live web (ô 11, 12, 13 — depth 3 hosted) để xem hệ số depth còn lại
    os_ = [o for o in H1_O if o not in (11, 12, 13)]
    Xl, yl, clql, _ = _hang(lambda c: cap_o(chuoi, c), os_)
    ra["bo_live_web"] = logit.mo_hinh(Xl, yl, clql, ten, B, SEEDS)
    # tỉ lệ thô theo depth × pinnability × observable (bảng cho số "mỗi bậc")
    bang = {}
    for o in H1_O:
        c = BY_O[o]
        ps = cap_o(chuoi, c)
        bang[str(o)] = {"depth": c.do_sau, "pin": c.pin, "obs": c.obs, "stage": c.stage,
                        "k": sum(p["doi"] for p in ps), "n": len(ps)}
    ra["ty_le_tho_theo_o"] = bang
    return ra


def parse_fail_flip(chuoi, data_dir: Path, N2: dict) -> dict:
    """Bao nhiêu lần 'lật' decision ở route local qwen là chuyển PARSE_FAIL ↔ nhãn (A→B M-protocol; oracle lan03/04)."""
    ra = {"nhan": NHAN}
    runs_q = {k[3]: v for k, v in chuoi.items() if k[0] == "P2" and k[1] == "route" and k[2] == "local"}
    n = flip = pf = 0
    for q in sorted(runs_q):
        runs = runs_q[q]
        if 1 not in runs or rd.doan(runs[1]["ts"]) != "A":
            continue
        js = [j for j in sorted(x for x in runs if isinstance(x, int)) if j >= 2 and rd.doan(runs[j]["ts"]) == "B"]
        if not js:
            continue
        a, b = gia_tri(runs[1], "dec"), gia_tri(runs[js[0]], "dec")
        n += 1
        if a != b:
            flip += 1
            pf += "PARSE_FAIL" in (a, b)
    ra["mprotocol_qwen_route_A_B"] = {"n": n, "flip": flip, "flip_co_parse_fail": pf}
    obs_dir = data_dir / "oracle"
    G = oracle_an.doc_obs(obs_dir / "obs_lan01.json")
    for lan in ("lan03", "lan04"):
        O = oracle_an.doc_obs(obs_dir / f"obs_{lan}.json")
        ks = [k for k in G if k.startswith("route|local|")]
        fl = [k for k in ks if O[k]["decision"] != G[k]["decision"]]
        ra[f"oracle_{lan}_route_local"] = {"n": len(ks), "flip": len(fl),
                                           "flip_co_parse_fail": sum("PARSE_FAIL" in (O[k]["decision"], G[k]["decision"])
                                                                     for k in fl)}
    return ra


def oracle_muc_suite(N2: dict) -> dict:
    """Mỗi lần chạy lại được đọc: suite decision có ≥ 1 test đỏ không (trên các ô được đọc ở lần đó)."""
    ra = {"nhan": NHAN}
    orc = N2["oracle"]
    host = set(t for t in orc["lan_hosted"])
    loc = set(t for t in orc["lan_local"])
    caps_h = ["classify|hosted", "route|hosted", "generate|hosted", "retrieve|bm25"]
    caps_l = ["classify|local", "route|local", "generate|local"]
    hang = []
    for r in orc["bang_lan"]:
        tid = r["task_id"]
        if not r.get("hop_le") or tid == orc["golden"]:
            continue
        doc_h, doc_l = tid in host, tid in loc
        if not (doc_h or doc_l):
            continue
        caps = (caps_h if doc_h else []) + (caps_l if doc_l else [])
        hang.append({"lan": r["lan"], "doan": r["doan"], "gio_tu_golden": r["cach_golden_h"], "doc_hosted": doc_h,
                     "doc_local": doc_l, "dec_do": sum(r.get(f"dec_do|{c}", 0) for c in caps),
                     "art_do": sum(r.get(f"art_do|{c}", 0) for c in caps),
                     "dec_do_hosted": sum(r.get(f"dec_do|{c}", 0) for c in caps_h) if doc_h else None,
                     "dec_do_local": sum(r.get(f"dec_do|{c}", 0) for c in caps_l) if doc_l else None})
    hh = [h for h in hang if h["doc_hosted"]]
    hl = [h for h in hang if h["doc_local"]]
    ra["hang"] = hang
    ra["hosted"] = {"lan_lai": len(hh), "co_dec_do": sum(h["dec_do_hosted"] > 0 for h in hh)}
    ra["local"] = {"lan_lai": len(hl), "co_dec_do": sum(h["dec_do_local"] > 0 for h in hl)}
    ra["moc"] = {"tong": len(orc["bang_lan"]), "missed": orc["missed"], "hop_le": orc["so_hop_le"]}
    ra["gio_tu_golden_hosted"] = [h["gio_tu_golden"] for h in hh]
    ra["gio_tu_golden_local"] = [h["gio_tu_golden"] for h in hl]
    return ra


def lam_tron(x):
    if isinstance(x, bool) or x is None or isinstance(x, (int, str)):
        return x
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else round(x, 6) + 0.0
    if hasattr(x, "item"):
        return lam_tron(x.item())
    if isinstance(x, dict):
        return {str(k): lam_tron(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [lam_tron(v) for v in x]
    raise TypeError(type(x))


def main() -> int:
    data = nap(DATA_THAT)
    chuoi, _ = chi_muc(data)
    N2p = REPO / "study" / "analysis_v2" / "out" / "numbers_v2.json"
    N2 = json.loads(N2p.read_text(encoding="utf-8"))
    out = {"_schema": "numbers_v2_posthoc/1", "nhan": NHAN,
           "nguon": {"numbers_v2.json": hashlib.sha256(N2p.read_bytes()).hexdigest(), "inputs": data["_inputs"]},
           "don_vi": dem_don_vi(chuoi), "oracle_ghep_cap": oracle_ghep(N2), "margin_ghep_cap": margin_ghep(chuoi),
           "doi_chung_ghep_cap": doi_chung_ghep(chuoi), "h1": h1_bien_the(chuoi),
           "parse_fail_trong_flip": parse_fail_flip(chuoi, DATA_THAT, N2), "oracle_muc_suite": oracle_muc_suite(N2),
           "da_co_trong_numbers_v2": {"d4_nhom_depth": "d4_depth", "d5_phep_so_phu": "h2.iii.phu_mprotocol",
                                      "d9_ho": "d9_ho", "khoang_cach_cap": "don_vi[*].gap"},
           "tham_so": {"B": B, "seeds": SEEDS}}
    out = lam_tron(out)
    o = HERE / "out"
    o.mkdir(exist_ok=True)
    (o / "numbers_v2_posthoc.json").write_text(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                               encoding="utf-8", newline="\n")
    print("xong", o / "numbers_v2_posthoc.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
