r"""P6 (a) — phân tích đo bù S3C (addendum mục (a), luật I1–I5). Chạy SAU khi đủ 22 lần.

    desktop\.venv\Scripts\python.exe study\analysis_p6\run_s3c.py [--khong-emb] [--cho-phep-thieu]  →  out/numbers_p6_s3c.json
"""
from __future__ import annotations

import argparse
import json
import sys

from common import HERE, NHAN, RES, Emb, av3, cluster_ratio, ghi_json
from s3eval import control_reds, thay_doi, tong
from run_b2 import keys_cho

sys.path.insert(0, str(RES.parent))
from p2 import s3c  # noqa: E402

THAY_DOI = ("P1", "P2", "M1", "T1", "K1", "R1-B")


def doc() -> dict:
    """runs[ô kế hoạch] = {(stage, qid): item}; dùng bản ok (X, X_r, X_i, X_i_r — sửa đổi 1 (b));
    bỏ lượt vô hiệu do hạ tầng `s3c.VO_HIEU` (sửa đổi 1 (a))."""
    man = [json.loads(l) for l in s3c.MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = {m["run"] for m in man if m.get("trang_thai") == "ok"} - set(s3c.VO_HIEU)
    runs: dict = {}
    for l in s3c.RESULT.read_text(encoding="utf-8").splitlines():
        it = json.loads(l)
        if it["run"] not in ok:
            continue
        runs.setdefault(s3c.o_ke_hoach(it["run"]), {})[(it["stage"], it["qid"])] = it
    return runs


def ty_le(rows_theo_cau: dict) -> dict:
    """rows_theo_cau[qid] = (sót, truly changed) cộng qua các lần → Wilson + bootstrap cụm theo câu."""
    k = sum(v[0] for v in rows_theo_cau.values())
    n = sum(v[1] for v in rows_theo_cau.values())
    w = av3.wilson(k, n) if n else (None, None)
    cl = cluster_ratio([v for v in rows_theo_cau.values() if v[1] > 0]) if n else None
    return {"sot": k, "that": n, "ty_le": k / n if n else None, "wilson": list(w), "cum_cau": cl}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--khong-emb", action="store_true")
    ap.add_argument("--cho-phep-thieu", action="store_true")
    a = ap.parse_args()
    runs = doc()
    can = s3c.thu_tu()
    thieu = [t for t in can if t not in runs]
    if thieu and not a.cho_phep_thieu:
        print(f"chưa đủ: thiếu {thieu}")
        return 2
    emb = None if a.khong_emb else Emb()
    g = runs["G"]
    ten_ctl = [t for t in can if s3c.goc(t) == "C" and t in runs]
    ctl = [runs[t] for t in ten_ctl]
    st = "generate"
    nen = control_reds(g, ctl, st, emb)
    sach = all(v == 0 for v in nen["do"].get("dec", [1])) and all(v == 0 for v in nen["do"].get("art", [1]))
    out = {"_nhan": NHAN + " — (a) S3C", "thieu": thieu, "n_control": len(ctl), "ten_control": ten_ctl, "nen": nen,
           "I1_nen_sach": sach, "thay_doi": {},
           # mục 5: số cũ của study 3 (1 lần mỗi thay đổi, nền không sạch) để đối chiếu
           "doi_chieu_study3": {"sot": 10, "that": 58, "chuan": "chinh (substring)"},
           # sửa đổi 2 (e): ô kế hoạch thiếu theo biến thể
           "thieu_theo_bien_the": {x: [t for t in thieu if s3c.goc(t) == x] for x in ("G", "C") + THAY_DOI}}
    cau_do_ctl = set(nen["cau_do"].get("dec", [])) | set(nen["cau_do"].get("art", []))
    gop = {"chinh": {}, "chinh_loai_cau_do_ctl": {}, "sf1": {}}
    hd = {"chinh": {}, "sf1": {}}          # I4: chỉ lần đầu của mỗi thay đổi (n hiệu dụng = 40 câu)
    rows_gop = {"chinh": [], "sf1": []}

    def raw(d):
        return {q: (i.get("decision"), i.get("artefact")) for (s_, q), i in d.items() if s_ == st}
    out["I4_byte"] = {"control_giong_G": {t: sum(raw(runs[t]).get(q) == v for q, v in raw(g).items()) for t in ten_ctl}}
    for x in THAY_DOI:
        lan = [t for t in can if s3c.goc(t) == x and t in runs]
        X = {"lan": lan, "theo_lan": {}}
        for chuan_ten in ("chinh", "sf1"):
            rows_all, theo_cau, theo_cau_loai = [], {}, {}
            for t in lan:
                rows = thay_doi(g, runs[t], st, emb, chuan_ten)
                X["theo_lan"].setdefault(t, {})[chuan_ten] = {
                    "n": len(rows), "that": sum(r["that"] for r in rows),
                    "dec_sot": sum(1 for r in rows if r["that"] and not r["dec"]),
                    "art_sot": sum(1 for r in rows if r["that"] and not r["art"]),
                    "sot_theo_chieu": {ch: sum(1 for r in rows if r["that"] and not r["dec"] and r["chieu"] == ch)
                                       for ch in ("dung_sang_sai", "sai_sang_dung")},
                    "dec_do": sum(r["dec"] for r in rows), "art_do": sum(r["art"] for r in rows)}
                if t == lan[0]:
                    rows_gop[chuan_ten] += rows
                    for r in rows:
                        w = hd[chuan_ten].setdefault(r["qid"], [0, 0])
                        w[0] += int(r["that"] and not r["dec"])
                        w[1] += r["that"]
                for r in rows:
                    v = theo_cau.setdefault(r["qid"], [0, 0])
                    v[0] += int(r["that"] and not r["dec"])
                    v[1] += r["that"]
                    if chuan_ten == "chinh" and r["qid"] not in cau_do_ctl:
                        w = theo_cau_loai.setdefault(r["qid"], [0, 0])
                        w[0] += int(r["that"] and not r["dec"])
                        w[1] += r["that"]
                rows_all += rows
            X[chuan_ten] = {"ty_le_sot_dec": ty_le(theo_cau), "nham_lan": tong(rows_all, keys_cho(st, emb is not None))}
            for q, v in theo_cau.items():
                gg = gop[chuan_ten].setdefault(q, [0, 0])
                gg[0] += v[0]
                gg[1] += v[1]
            if chuan_ten == "chinh":
                X["chinh_loai_cau_do_ctl"] = {"ty_le_sot_dec": ty_le(theo_cau_loai)}
                for q, v in theo_cau_loai.items():
                    gg = gop["chinh_loai_cau_do_ctl"].setdefault(q, [0, 0])
                    gg[0] += v[0]
                    gg[1] += v[1]
        # I4: độ lặp giữa các lần
        same_dec = same_art = 0
        for (s_, q), gi in g.items():
            if s_ != st:
                continue
            its = [runs[t].get((st, q)) for t in lan]
            if all(i and i.get("ok") for i in its) and len(its) > 1:
                same_dec += int(len({i["decision"] for i in its}) == 1)
                same_art += int(len({av3.chuan_hoa(i["artefact"]) for i in its}) == 1)
        X["I4_lap"] = {"cau_dec_giong_moi_lan": same_dec, "cau_art_giong_moi_lan": same_art, "so_lan": len(lan)}
        rs = [raw(runs[t]) for t in lan]
        X["I4_lap"]["cau_giong_tung_byte"] = sum(all(r.get(q) == rs[0].get(q) for r in rs) for q in raw(g))
        # I2: Δ tỉ lệ đỏ theo decision (thay đổi − control), ghép cặp theo câu, av3.boot_delta
        qs = sorted(q for (s_, q) in g if s_ == st)
        def ty_le_do(ds):
            v = {}
            for q in qs:
                gi = g.get((st, q))
                its = [d.get((st, q)) for d in ds]
                its = [i for i in its if i and i.get("ok")]
                if gi and gi.get("ok") and its:
                    v[q] = sum(int(i["decision"] != gi["decision"]) for i in its) / len(its)
            return v
        vx, vc = ty_le_do([runs[t] for t in lan]), ty_le_do(ctl)
        chung = [q for q in qs if q in vx and q in vc]
        X["I2_delta_dec"] = av3.boot_delta([vx[q] for q in chung], [vc[q] for q in chung]) if chung and ctl else None
        out["thay_doi"][x] = X
    out["gop"] = {k: ty_le(v) for k, v in gop.items()}
    # I4: nếu mọi thay đổi lặp giống hệt từng byte ⇒ báo theo lần đầu (40 câu mỗi thay đổi), không coi 3 lần là 3 mẫu
    out["I4_moi_thay_doi_giong_byte"] = all(X["I4_lap"]["cau_giong_tung_byte"] == len(raw(g)) for X in out["thay_doi"].values())
    out["hieu_dung"] = {k: ty_le(v) for k, v in hd.items()}
    out["nham_lan_gop_lan_dau"] = {k: tong(v, keys_cho(st, emb is not None)) for k, v in rows_gop.items()}
    out["nham_lan_gop_lan_dau_chieu"] = {k: {ch: sum(1 for r in v if r["that"] and not r["dec"] and r["chieu"] == ch)
                                             for ch in ("dung_sang_sai", "sai_sang_dung")} for k, v in rows_gop.items()}
    ghi_json(HERE / "out" / "numbers_p6_s3c.json", out)
    print("S3C xong" + (f" (THIẾU {thieu})" if thieu else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
