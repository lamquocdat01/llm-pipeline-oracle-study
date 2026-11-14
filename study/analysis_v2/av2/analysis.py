"""N4: ráp toàn bộ phân tích theo PREREG_V2 §6–§9 + V2-05 (D1–D10) + V2-06 + V2-07. Trả một dict thuần.

Nhãn: mỗi khối có trường "nhan" = "chính" (đọc kết luận H từ đó) hoặc "khám phá" (in ra, không kết luận H).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from . import hau_kiem, logit, oracle_an, v11
from .cells import (BY_O, CAP_MARGIN, DV_N3, DV_P2, DV_P3H, H1_O, H2_I, H2_II, O_ALL, cap_o, chi_muc, gia_tri)
from .load import FILES, doc_jsonl, nap, rd
from .stats import chua_0, margin, median, newcombe, phan_quyet, wilson

SEEDS = [20261112, 20261113, 20261114, 20261115, 20261116]

LUAT = {
    "s6": ("Luật (A04.4, nguyên văn): dự đoán ổn định đúng ⇔ k/n ≤ 5 % và cận trên Wilson ≤ 10 %; sai ⇔ k/n ≥ 20 %. "
           "Dự đoán không ổn định đúng ⇔ k/n ≥ 20 %; sai ⇔ k/n ≤ 5 %. Vùng giữa: không phân định, nhưng tính sai nếu "
           "ước lượng điểm ở nửa ngược chiều (ranh 12,5 %). Kiểm lực: … đơn vị n < 35 mang nhãn thiếu lực cho dự đoán "
           "ổn định (vẫn có thể sai)."),
    "h1": ("§7(b): H1 được ủng hộ khi CI hệ số pinnable > 0 và CI hệ số depth chứa 0. (V2-05 D3: cluster theo câu; "
           "tách hoàn toàn ⇒ Firth + bootstrap cluster B = 2 000, 5 seed, báo khoảng rộng nhất.)"),
    "h2": ("§8: H2 ủng hộ khi: (i) ở mọi stage delegated của P2 (classify, route, generate; live A/B so với SOURCES) cận "
           "dưới Newcombe > 0; (ii) ở stage pinnable (qwen P2, llama P3, llama MD3) |margin| ≤ 0,05 hoặc khoảng chứa 0; "
           "(iii) dấu và bậc độ lớn (cùng thập phân bậc, tỉ ≤ 10) của margin delegated trùng giữa Microduck v1.1 (M6 "
           "routing 0,750) và P2 route. Bất kỳ phần nào ngược ⇒ in như kết quả. (V2-05 D5: chính = margin oracle P2O "
           "route hosted; cùng bậc = tỉ số trong [0,1; 10] và cùng dấu, trên ước lượng điểm.)"),
    "h3": ("§9: H3 ủng hộ khi ở ô oracle delegated (classify, route, generate hosted) cận dưới Newcombe của margin > 0, "
           "và ở ô pinnable (qwen, BM25) khoảng chứa 0. Cùng với phần dự đoán ô (§6): ≥ 2/3 đơn vị pipeline 2 đã phân "
           "định là đúng, tức ≥ ⌈2/3 × số đã phân định⌉; báo cả đúng/13."),
    "v206": ("V2-06: cận dưới Δ > 0 ở cả hai stage ⇒ trong cùng họ, nhánh delegated đổi artefact nhiều hơn: hệ số "
             "pinnable không chỉ là hiệu ứng họ. Khoảng chứa 0 hoặc cận trên Δ < 0 ⇒ báo nguyên văn rằng đối chứng "
             "không ủng hộ: khác biệt ở P2 có thể do họ model. Hai stage trái nhau ⇒ báo riêng từng stage."),
}


def _kn(pairs: list[dict]) -> tuple[int, int]:
    return sum(p["doi"] for p in pairs), len(pairs)


def _gap(pairs: list[dict]) -> dict:
    g = [p["gap_h"] for p in pairs]
    return {"median_h": median(g), "min_h": min(g) if g else None, "max_h": max(g) if g else None}


def don_vi(chuoi: dict) -> tuple[dict, dict]:
    ra, cap = {}, {}
    for c in O_ALL:
        ps = cap_o(chuoi, c)
        cap[c.o] = ps
        k, n = _kn(ps)
        pq = phan_quyet(c.du_doan, k, n)
        d = {"o": c.o, "nguon": c.nguon, "stage": c.stage, "be": c.be, "do_sau": c.do_sau, "obs": c.obs,
             "quan_sat": c.quan_sat, "pin": c.pin, "ho": c.ho, "du_doan": c.du_doan, "n_dang_ky": c.n_dk,
             "tinh_diem": c.tinh_diem, "suy_tu": c.suy_tu, "luat_cap": c.cap, **pq,
             "k_lan_dung": sorted({str(p["k"]) for p in ps}), "gap": _gap(ps),
             "doan": {s: sum(p["doan"] == s for p in ps) for s in sorted({p["doan"] for p in ps})}}
        if not c.tinh_diem:
            d["phan_quyet"] = f"không tính điểm — suy từ ô {c.suy_tu} (A06.1); quan sát: {pq['phan_quyet']}"
        if c.cap == "cung_runtime":           # V2-07(b): cặp 1→5 đã đăng ký in cạnh
            p5 = cap_o(chuoi, c, "1to5")
            k5, n5 = _kn(p5)
            d["cap_1to5_dang_ky"] = {**phan_quyet(c.du_doan, k5, n5), "gap": _gap(p5),
                                     "doan": {s: sum(p["doan"] == s for p in p5) for s in sorted({p["doan"] for p in p5})}}
        p72 = [p for p in ps if p["gap_h"] <= 72]          # D8 khám phá
        k72, n72 = _kn(p72)
        d["kham_pha_cap_le_72h"] = {"k": k72, "n": n72, "ty_le": k72 / n72 if n72 else None,
                                    "wilson": list(wilson(k72, n72))}
        ra[c.o] = d
    return ra, cap


def margins(dv: dict, cap: dict) -> dict:
    ra = {}
    for ten, (od, oa) in CAP_MARGIN.items():
        d, a = dv[od], dv[oa]
        mg = margin(a["k"], a["n"], d["k"], d["n"])
        qa = {p["q"]: p["doi"] for p in cap[oa]}
        qd = {p["q"]: p["doi"] for p in cap[od]}
        chung = sorted(set(qa) & set(qd))
        ra[ten] = {**mg, "o_dec": od, "o_art": oa, "pin": BY_O[oa].pin, "ho": BY_O[oa].ho,
                   "nguon": BY_O[oa].nguon, "stage": BY_O[oa].stage,
                   "margin_theo_chu_s8_dec_tru_art": -mg["margin"] if not math.isnan(mg["margin"]) else None,
                   "ghep_dec_doi_art_khong": sum(1 for q in chung if qd[q] and not qa[q]),
                   "ghep_ca_hai_doi": sum(1 for q in chung if qd[q] and qa[q]),
                   "ghep_art_doi_dec_khong": sum(1 for q in chung if qa[q] and not qd[q]),
                   "ghep_n": len(chung)}
        if "cap_1to5_dang_ky" in a:
            a5, d5 = a["cap_1to5_dang_ky"], d["cap_1to5_dang_ky"]
            ra[ten]["cap_1to5_dang_ky"] = margin(a5["k"], a5["n"], d5["k"], d5["n"])
    return ra


def h2(mg: dict, orc: dict) -> dict:
    i = {t: {"lo": mg[t]["lo"], "dat": mg[t]["lo"] > 0} for t in H2_I}
    ii = {t: {"margin": mg[t]["margin"], "lo": mg[t]["lo"], "hi": mg[t]["hi"],
              "dat": abs(mg[t]["margin"]) <= 0.05 or chua_0(mg[t]["lo"], mg[t]["hi"])} for t in H2_II}
    rh = orc["o"]["route|hosted"]
    ti = rh["margin_margin"] / v11.M6_ROUTING_HOSTED["margin"]
    iii = {"p2o_route_hosted": rh["margin_margin"], "p2o_lo": rh["margin_lo"], "p2o_hi": rh["margin_hi"],
           "v11_m6": v11.M6_ROUTING_HOSTED["margin"], "ti_so": ti,
           "dat": (0.1 <= ti <= 10) and (rh["margin_margin"] > 0)}
    m2 = mg["P2 route hosted"]
    phu = {}
    for nhan, v in (("v11_t0", v11.M2_T0), ("v11_t08", v11.M2_T08)):
        mv = margin(v["art_k"], v["n"], v["dec_k"], v["n"])
        t = (m2["margin"] / mv["margin"]) if mv["margin"] else None
        phu[nhan] = {"v11": mv, "p2_1to5": m2["margin"], "ti_so": t,
                     "cung_bac_cung_dau": bool(t is not None and 0.1 <= t <= 10 and m2["margin"] > 0)}
    iii["phu_mprotocol"] = phu
    dat = {"i": all(x["dat"] for x in i.values()), "ii": all(x["dat"] for x in ii.values()), "iii": iii["dat"]}
    kl = "ủng hộ" if all(dat.values()) else "bác ở phần " + ", ".join(k for k, v in dat.items() if not v)
    return {"nhan": "chính", "luat": LUAT["h2"], "i": i, "ii": ii, "iii": iii, "dat": dat, "ket_luan": kl,
            "ghi_chu_dau": ("§8 viết 'margin = R^dec − R^art' nhưng (i) đòi cận dưới > 0 và (iii) so với M6 0,750 = "
                            "art − dec; theo cấu trúc R^dec ≤ R^art (A06.1) nên đọc nguyên chữ thì (i) luôn bác. "
                            "Phân tích dùng R^art − R^dec (như §5, V2-06, M6); in kèm dấu nguyên chữ.")}


def h3(dv: dict, orc: dict) -> dict:
    xs = [dv[o] for o in DV_P2]
    phan_dinh = [x for x in xs if x["phan_quyet"] in ("đúng", "sai") and x["vao_mau_so"]]
    dung = sum(x["phan_quyet"] == "đúng" for x in phan_dinh)
    can = math.ceil(2 / 3 * len(phan_dinh)) if phan_dinh else None
    du_doan = {"dung": dung, "sai": sum(x["phan_quyet"] == "sai" for x in phan_dinh), "phan_dinh": len(phan_dinh),
               "khong_phan_dinh": sum(x["phan_quyet"] == "không phân định" for x in xs),
               "thieu_luc_khong_tinh": sum(1 for x in xs if not x["vao_mau_so"]),
               "can": can, "dung_tren_13": f"{dung}/13", "dat": bool(phan_dinh) and dung >= can}
    o = orc["o"]
    oracle = {}
    for key in ("classify|hosted", "route|hosted", "generate|hosted"):
        oracle[key] = {"margin": o[key]["margin_margin"], "lo": o[key]["margin_lo"], "hi": o[key]["margin_hi"],
                       "dat": o[key]["margin_lo"] > 0}
    for key in ("classify|local", "route|local", "generate|local", "retrieve|bm25"):
        oracle[key] = {"margin": o[key]["margin_margin"], "lo": o[key]["margin_lo"], "hi": o[key]["margin_hi"],
                       "dat": o[key]["khoang_chua_0"]}
    dat_o = all(v["dat"] for v in oracle.values())
    kl = "ủng hộ" if (dat_o and du_doan["dat"]) else (
        "bác ở phần " + ", ".join(t for t, v in (("oracle", dat_o), ("dự đoán ô", du_doan["dat"])) if not v))
    return {"nhan": "chính", "luat": LUAT["h3"], "du_doan_o": du_doan, "oracle": oracle, "dat_oracle": dat_o,
            "ket_luan": kl}


def _hang_h1(cap: dict, os_: list[int], them_pipeline: bool = False):
    X, y, cl = [], [], []
    for o in os_:
        c = BY_O[o]
        for p in cap[o]:
            row = [1.0, c.do_sau, 1.0 if c.pin == "pinnable" else 0.0, 1.0 if c.obs == "art" else 0.0]
            if them_pipeline:
                row.append(1.0 if c.nguon == "MD3R" else 0.0)
            X.append(row)
            y.append(0.0 if p["doi"] else 1.0)
            cl.append(("MD:" if c.nguon == "MD3R" else "Q:") + p["q"])
    return np.array(X), np.array(y), np.array(cl)


def h1(cap: dict, B: int, seeds: list[int]) -> dict:
    ten = ["const", "depth", "pinnable", "artefact"]
    X, y, cl = _hang_h1(cap, H1_O)
    m = logit.mo_hinh(X, y, cl, ten, B, seeds)
    j_pin, j_dep = ten.index("pinnable"), ten.index("depth")
    pin_lo, pin_hi = m["ci_lo"][j_pin], m["ci_hi"][j_pin]
    dep_lo, dep_hi = m["ci_lo"][j_dep], m["ci_hi"][j_dep]
    if pin_lo > 0 and dep_lo <= 0 <= dep_hi:
        kl = "ủng hộ"
    elif not (dep_lo <= 0 <= dep_hi) or pin_hi < 0:
        kl = "bác"
    else:
        kl = "không kết luận được"
    chinh = {"nhan": "chính", "luat": LUAT["h1"], "mo_hinh": m, "pinnable_ci": [pin_lo, pin_hi],
             "depth_ci": [dep_lo, dep_hi], "ket_luan": kl, "xs_du_doan": logit.du_doan_xs(m["beta"], ten),
             "ty_le_tho_theo_o": {str(o): {"k": sum(p["doi"] for p in cap[o]), "n": len(cap[o])} for o in H1_O}}
    # khám phá (V2-05 D3)
    kp = {"nhan": "khám phá"}
    Xi = np.column_stack([X, X[:, 1] * X[:, 2]])
    kp["depth_x_pinnable"] = logit.mo_hinh(Xi, y, cl, ten + ["depth:pinnable"], B, seeds, firth_luon=True)
    Xc = np.column_stack([X[:, 0], X[:, 2], X[:, 3]] + [(X[:, 1] == d).astype(float) for d in (2, 3, 4)])
    kp["depth_phan_loai"] = logit.mo_hinh(Xc, y, cl, ["const", "pinnable", "artefact", "depth2", "depth3", "depth4"],
                                          B, seeds, firth_luon=True)
    Xm, ym, clm = _hang_h1(cap, H1_O + [23, 25], them_pipeline=True)
    hv = []
    for (o, ng, dep, pin, art, k, n) in v11.V11_HANG:      # v1.1: không có id câu ⇒ mỗi đơn vị một cluster
        for i in range(n):
            hv.append(([1.0, dep, pin, art, 1.0], 0.0 if i < k else 1.0, f"V11:{o}:{ng}"))
    Xm = np.vstack([Xm, np.array([h[0] for h in hv])])
    ym = np.concatenate([ym, np.array([h[1] for h in hv])])
    clm = np.concatenate([clm, np.array([h[2] for h in hv])])
    kp["them_md3_v11_pipeline_fe"] = logit.mo_hinh(Xm, ym, clm, ten + ["pipeline_microduck"], B, seeds, firth_luon=True)
    kp["them_md3_v11_pipeline_fe"]["ghi_chu"] = ("pipeline_microduck = 1 cho MD3R và v1.1; v1.1 dựng lại từ k/n "
                                                 "từng đơn vị (§11c), mỗi đơn vị một cluster")
    return {"chinh": chinh, "kham_pha": kp}


NHOM_D4 = [("delegated × decision", [1, 5, 11, 14]), ("delegated × artefact", [2, 6, 12, 13, 15]),
           ("pinnable × artefact", [4, 8, 17, 19, 21])]


def _nhom_depth(dv: dict, os_: list[int]) -> dict:
    xep = []
    for o in os_:
        d = dv[o]
        if not d["n"]:
            continue
        p = d["k"] / d["n"]
        loai = "ổn định" if p <= 0.05 else "không ổn định" if p >= 0.20 else None
        if loai:
            xep.append({"o": o, "do_sau": d["do_sau"], "loai": loai, "k": d["k"], "n": d["n"]})
    loais = {x["loai"] for x in xep}
    if len(xep) < 2:
        kq = "không phân định"
    elif len(loais) == 1:
        kq = "hỗ trợ"
    elif any(a["loai"] != b["loai"] and a["do_sau"] != b["do_sau"] for a in xep for b in xep):
        kq = "bác"
    else:
        kq = "không phân định"
    return {"o": os_, "don_vi_xep": xep, "ket_qua": kq}


def d4(dv: dict) -> dict:
    ra = {ten: _nhom_depth(dv, os_) for ten, os_ in NHOM_D4}
    ra["pinnable × artefact + 23, 25 (dòng in riêng, D4)"] = _nhom_depth(dv, [4, 8, 17, 19, 21, 23, 25])
    return {"nhan": "chính (3 nhóm §7(a)); dòng +23,25 in riêng", "nhom": ra,
            "ghi_chu": "pinnable × decision chỉ ô 9 — không so (§7(a))"}


def d7(chuoi: dict) -> dict:
    """Khám phá: tách cặp ô local theo đoạn runtime; 'silent runtime update' (V2-07(e))."""
    rows = []
    for nguon, stage, ho in (("P2", "classify", "qwen"), ("P2", "route", "qwen"), ("P2", "generate", "qwen"),
                             ("P3", "route", "llama"), ("P3", "generate", "llama")):
        runs_q = {k[3]: v for k, v in chuoi.items() if k[0] == nguon and k[1] == stage and k[2] == "local"}
        for loai in ("A→B (silent runtime update)", "A→cùng runtime kế tiếp"):
            kd = ka = n = 0
            for q in sorted(runs_q):
                runs = runs_q[q]
                if 1 not in runs or rd.doan(runs[1]["ts"]) != "A":
                    continue
                cands = [j for j in sorted(x for x in runs if isinstance(x, int)) if j >= 2]
                if loai.startswith("A→B"):
                    js = [j for j in cands if rd.doan(runs[j]["ts"]) == "B"]
                else:
                    js = [j for j in cands if rd.doan(runs[j]["ts"]) in ("A", "D")]
                if not js:
                    continue
                b = runs[js[0]]
                n += 1
                kd += gia_tri(runs[1], "dec") != gia_tri(b, "dec")
                ka += gia_tri(runs[1], "art") != gia_tri(b, "art")
            rows.append({"nguon": nguon, "stage": stage, "ho": ho, "cap": loai, "n": n, "dec_doi": kd,
                         "art_doi": ka, "dec_wilson": list(wilson(kd, n)), "art_wilson": list(wilson(ka, n))})
        for luat in ("1to5", "cung_runtime"):        # theo tổ hợp đoạn của cặp
            od = [c for c in O_ALL if c.nguon == nguon and c.stage == stage and c.be == "local"]
            cd = next(c for c in od if c.obs == "dec")
            ca = next(c for c in od if c.obs == "art")
            pd, pa = cap_o(chuoi, cd, luat), cap_o(chuoi, ca, luat)
            for s in sorted({p["doan"] for p in pa}):
                xs_a = [p for p in pa if p["doan"] == s]
                xs_d = [p for p in pd if p["doan"] == s]
                ka, n = _kn(xs_a)
                kd, _ = _kn(xs_d)
                rows.append({"nguon": nguon, "stage": stage, "ho": ho, "cap": f"{luat} đoạn {s}", "n": n,
                             "dec_doi": kd, "art_doi": ka, "dec_wilson": list(wilson(kd, n)),
                             "art_wilson": list(wilson(ka, n))})
    for sub, ld, la in (("M2", "md_lookup", "md_raw"), ("M4", "md_lang", "md_reply")):     # MD3 cũ, bắc cầu
        runs_q = {k[3]: v for k, v in chuoi.items() if k[0] == "MD3" and k[1] == sub}
        for a_, b_ in (("t0", "t24h"), ("t0", "t0p")):
            grp: dict = {}
            for q in sorted(runs_q):
                r = runs_q[q]
                if a_ in r and b_ in r:
                    s = rd.doan(r[a_]["ts"]) + rd.doan(r[b_]["ts"])
                    g = grp.setdefault(s, [0, 0, 0])
                    g[0] += 1
                    g[1] += gia_tri(r[a_], ld) != gia_tri(r[b_], ld)
                    g[2] += gia_tri(r[a_], la) != gia_tri(r[b_], la)
            for s, (n, kd, ka) in sorted(grp.items()):
                rows.append({"nguon": "MD3 (cũ)", "stage": sub, "ho": "llama", "cap": f"{a_}→{b_} đoạn {s}", "n": n,
                             "dec_doi": kd, "art_doi": ka, "dec_wilson": list(wilson(kd, n)),
                             "art_wilson": list(wilson(ka, n))})
    return {"nhan": "khám phá", "hang": rows,
            "ghi_chu": "mẫu con không ngẫu nhiên (thứ tự chạy theo plan) — chỉ mô tả, không kiểm định (V2-05 D7, V2-07(e))"}


def d9(mg: dict, dv: dict) -> dict:
    ra = {"nhan": "khám phá"}
    for stage, (oq, ol) in (("route", (8, 19)), ("generate", (17, 21))):
        q, l = dv[oq], dv[ol]
        d, lo, hi = newcombe(l["k"], l["n"], q["k"], q["n"])
        ra[stage] = {"qwen_margin": mg[f"P2 {stage} qwen"], "llama_margin": mg[f"P3 {stage} llama"],
                     "r_art_llama_tru_qwen": {"d": d, "lo": lo, "hi": hi}}
    return ra


def d10(chuoi: dict, probe: dict, data: dict) -> dict:
    rows = []
    spec = [("P2", s, "hosted", "t08") for s in ("classify", "route", "generate", "live")] + \
           [("P2", s, "local", t) for s in ("classify", "route", "generate") for t in ("t08", "seed1")] + \
           [("P3", s, "local", t) for s in ("route", "generate") for t in ("t08", "seed1")] + \
           [("MD3", s, "local", t) for s in ("M2", "M4") for t in ("t08", "seed1")]
    for m, st, be, tag in spec:
        ld, la = {"M2": ("md_lookup", "md_raw"), "M4": ("md_lang", "md_reply")}.get(st, ("dec", "art"))
        goc, sau = ("t0", "t0p") if m == "MD3" else (1, 2)
        qs = sorted(k[3] for k, v in probe.items() if k[:3] == (m, st, be) and tag in v)
        n = pa = pd = ca = cd = 0
        for q in qs:
            runs = chuoi.get((m, st, be, q), {})
            if goc not in runs or sau not in runs:
                continue
            pr = probe[(m, st, be, q)][tag]
            n += 1
            pa += gia_tri(pr, la) != gia_tri(runs[goc], la)
            pd += gia_tri(pr, ld) != gia_tri(runs[goc], ld)
            ca += gia_tri(runs[sau], la) != gia_tri(runs[goc], la)
            cd += gia_tri(runs[sau], ld) != gia_tri(runs[goc], ld)
        rows.append({"nguon": m, "stage": st, "be": be, "probe": tag, "n": n, "probe_art_doi": pa,
                     "probe_dec_doi": pd, "cap_1_2_art_doi": ca, "cap_1_2_dec_doi": cd,
                     "doc": ("probe đổi nhiều hơn cặp 1→2" if pa > ca else "không xác nhận được (C2)")})
    pf = []
    for m in ("P2", "P3", "P3H"):
        grp: dict = {}
        for tid, r in sorted(data.get(m, {}).items()):
            p = tid.split("|")
            if p[-1] == "probe" or p[1] in ("retrieve", "live"):
                continue
            g = grp.setdefault((p[1], p[2]), [0, 0])
            g[0] += 1
            g[1] += r["payload"]["decision"] == "PARSE_FAIL"
        for (st, be), (n, k) in sorted(grp.items()):
            pf.append({"nguon": m, "stage": st, "be": be, "n_ban_ghi": n, "parse_fail": k, "ty_le": k / n,
                       "wilson": list(wilson(k, n))})
    return {"nhan": "khám phá (mô tả, không kiểm định — D10)", "probe": rows, "parse_fail": pf}


def v206(dv: dict, mg: dict) -> dict:
    if not dv[27]["n"]:
        return {"nhan": "chính", "co_du_lieu": False}
    ra = {"nhan": "chính", "co_du_lieu": True, "luat": LUAT["v206"]}
    los = {}
    for stage, (oh, ol, th, tl) in (("route", (27, 19, "P3H route llama", "P3 route llama")),
                                    ("generate", (29, 21, "P3H generate llama", "P3 generate llama"))):
        h, l = dv[oh], dv[ol]
        d, lo, hi = newcombe(h["k"], h["n"], l["k"], l["n"])
        los[stage] = (lo, hi)
        ra[stage] = {"p3h": {"r_dec": mg[th]["r_dec"], "r_art": mg[th]["r_art"], "n": h["n"],
                             "dec_wilson": dv[oh - 1]["wilson"], "art_wilson": h["wilson"],
                             "margin": mg[th]["margin"], "lo": mg[th]["lo"], "hi": mg[th]["hi"]},
                     "p3_local_cung_runtime": {"r_dec": mg[tl]["r_dec"], "r_art": mg[tl]["r_art"], "n": l["n"],
                                               "dec_wilson": dv[ol - 1]["wilson"], "art_wilson": l["wilson"],
                                               "margin": mg[tl]["margin"], "lo": mg[tl]["lo"], "hi": mg[tl]["hi"]},
                     "delta_r_art": {"d": d, "lo": lo, "hi": hi}}
    dat = {s: lo > 0 for s, (lo, hi) in los.items()}
    if all(dat.values()):
        kl = "ủng hộ: trong cùng họ, nhánh delegated đổi artefact nhiều hơn (cận dưới Δ > 0 ở cả hai stage)"
    elif not any(dat.values()):
        kl = "đối chứng không ủng hộ: khác biệt ở P2 có thể do họ model (khoảng Δ chứa 0 hoặc cận trên < 0)"
    else:
        kl = "hai stage trái nhau — báo riêng: " + "; ".join(
            f"{s}: {'cận dưới Δ > 0' if v else 'không ủng hộ'}" for s, v in dat.items())
    ra["ket_luan"] = kl
    return ra


def sai_o(dv: dict) -> list[dict]:
    ra = []
    for o in DV_P2 + DV_N3 + DV_P3H:
        d = dv[o]
        if d["phan_quyet"] == "sai":
            ra.append({"o": o, "nguon": d["nguon"], "stage": d["stage"], "quan_sat": d["quan_sat"], "pin": d["pin"],
                       "du_doan": d["du_doan"], "k": d["k"], "n": d["n"], "ty_le": d["ty_le"], "wilson": d["wilson"],
                       "v11_tuong_tu": v11.TUONG_TU_V11.get(o)})
    return ra


def chay(data_dir: Path, B: int = 2000, seeds: list[int] = SEEDS) -> dict:
    data = nap(data_dir)
    p2o_all = doc_jsonl(data_dir / FILES["P2O"])
    chuoi, probe = chi_muc(data)
    dv, cap = don_vi(chuoi)
    mg = margins(dv, cap)
    orc = oracle_an.phan_tich(data["P2O"], p2o_all, data_dir)
    co_p3h = bool(dv[27]["n"])
    dem = {"pipeline2": len(DV_P2), "n3": len(DV_N3), "p3h_k": len(DV_P3H) if co_p3h else 0}
    dem["tong"] = dem["pipeline2"] + dem["n3"] + dem["p3h_k"]

    def tom(os_):
        xs = [dv[o] for o in os_]
        return {v: sum(x["phan_quyet"] == v for x in xs) for v in ("đúng", "sai", "không phân định")} | {
            "thieu_luc": sum(x["thieu_luc"] for x in xs), "khong_co_cap": sum(x["n"] == 0 for x in xs)}

    return {
        "_schema": "numbers_v2/1",
        "inputs": data["_inputs"],
        "tham_so": {"B": B, "seeds": seeds},
        "luat_s6": LUAT["s6"],
        "dem_don_vi": dem,
        "tom_tat_don_vi": {"pipeline2_13": tom(DV_P2), "n3_4": tom(DV_N3), "p3h_4": tom(DV_P3H) if co_p3h else None,
                           "v11_15_bao_rieng": v11.V11_TOM_TAT},
        "don_vi": {str(k): v for k, v in dv.items()},
        "margin": mg,
        "oracle": orc,
        "h1": h1(cap, B, seeds),
        "h2": h2(mg, orc),
        "h3": h3(dv, orc),
        "d4_depth": d4(dv),
        "d7_runtime": d7(chuoi),
        "d9_ho": d9(mg, dv),
        "d10": d10(chuoi, probe, data),
        "v206_p3h": v206(dv, mg),
        "sai_o": sai_o(dv),
        "hau_kiem": hau_kiem.chay(orc, data_dir, data["P2O"], chuoi),
        "v11": {"m6_routing_hosted": v11.M6_ROUTING_HOSTED, "m2_t0": v11.M2_T0, "m2_t08": v11.M2_T08,
                "sai": v11.V11_SAI},
    }
