r"""POST HOC trên dữ liệu nghiên cứu 3 đã khoá (P3D, 13-11-2026; viết SAU khi biết kết quả NC3 và đọc phản biện vòng 2).
Không đổi verdict S1/S2/S3 đã đăng ký. Chỉ đọc: results/S3_20261112_v1.*, results/oracle/obs_lan*.json (NC2),
study/analysis_v3/out/numbers_v3.json, study/analysis_v2*/out/*.json.

    python study\analysis_v3_posthoc\run_v3_posthoc.py   →  out/numbers_v3_posthoc.json

N1  classify: test chỉ artefact đỏ — JSON hợp lệ? trường language đổi? khác gì còn lại.
N2  local generate: số biến thể rời mỗi test qua golden, C1–C3, R1-A2 (NC3) và các lần cùng runtime A/D của NC2;
    lần nào trùng lần nào; thứ tự + thời lượng mỗi lần.
N3  chuẩn ngoài mở rộng: thêm dòng C1–C3; tách trả lời được / không; đúng→sai / sai→đúng; Wilson.
N6  PARSE_FAIL trong decision đổi của R1-B, P1, M1 (route local); R1-B so với lan03/lan04 của NC2.
KIEM kiểm lại số của phản biện vòng 2 (8/17; naive trên cặp đăng ký; 48/67; Wilson 10/58).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
P2 = REPO / "study" / "pipeline2"
sys.path[:0] = [str(REPO / "study" / "analysis_v3"), str(REPO / "study" / "analysis_v3b"), str(P2)]
import av3  # noqa: E402
import av3b  # noqa: E402
from p2 import corpus  # noqa: E402
from p2.runtime_doan import doan  # noqa: E402

RES = P2 / "results"
CTL = ("C1", "C2", "C3")


def nap_json(s: str):
    t = (s or "").strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except Exception:
        return None


def n1(runs) -> dict:
    out = {}
    for (arm, run), R in sorted(runs.items()):
        if run == "golden":
            continue
        g = runs[(arm, "golden")]
        d = av3.do(g, R, "classify")
        dem = {"chi_art_do": 0, "json_hop_le_doi": 0, "language_doi": 0, "cung_json_chi_dinh_dang": 0, "khac": 0,
               "vi_du": []}
        for q, (rd, ra) in sorted(d.items()):
            if not ra or rd:
                continue
            dem["chi_art_do"] += 1
            jg, jr = nap_json(g[("classify", q)]["artefact"]), nap_json(R[("classify", q)]["artefact"])
            if (jg is None) != (jr is None):
                dem["json_hop_le_doi"] += 1
                loai = "json_hop_le_doi"
            elif isinstance(jg, dict) and isinstance(jr, dict) and jg.get("language") != jr.get("language"):
                dem["language_doi"] += 1
                loai = "language_doi"
            elif jg == jr:
                dem["cung_json_chi_dinh_dang"] += 1
                loai = "cung_json_chi_dinh_dang"
            else:
                dem["khac"] += 1
                loai = "khac"
            if len(dem["vi_du"]) < 3:
                dem["vi_du"].append({"qid": q, "loai": loai, "golden": g[("classify", q)]["artefact"][:160],
                                     "run": R[("classify", q)]["artefact"][:160]})
        dem["decision_bo_qua"] = dem["json_hop_le_doi"] + dem["language_doi"]
        out[f"{arm}|{run}"] = dem
    tong = {}
    for nhom, loc in (("thay_doi", lambda k: k.split("|")[1] not in CTL), ("doi_chung", lambda k: k.split("|")[1] in CTL)):
        t = {}
        for k, v in out.items():
            if loc(k):
                for kk, vv in v.items():
                    if kk != "vi_du":
                        t[kk] = t.get(kk, 0) + vv
        tong[nhom] = t
    return {"theo_lan": out, "tong": tong}


def nc2_local_generate() -> dict[str, dict[str, str]]:
    """lan -> {qid: artefact} cho generate|local các lần oracle NC2 ở đoạn A hoặc D (cùng runtime 0.30.10)."""
    man = {}
    for l in (RES / "P2O_20261102_v1.jsonl").read_text(encoding="utf-8").splitlines():
        x = json.loads(l)
        if x.get("status") == "ok":
            man[x["payload"]["obs"]] = x["ts"]
    out = {}
    for f in sorted((RES / "oracle").glob("obs_lan*.json")):
        if f.name not in man or doan(man[f.name]) not in ("A", "D"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        out[f"NC2-{f.stem[4:]}-{doan(man[f.name])}"] = {it["qid"]: it["artefact"] for it in d["items"]
                                                         if it["stage"] == "generate" and it["backend"] == "local"}
    return out


def n2(runs, manifest) -> dict:
    lan = {f"NC3-{t}": {q: it["artefact"] for (st, q), it in runs[("local", t)].items() if st == "generate" and it.get("ok")}
           for t in ("golden", "C1", "C2", "C3", "R1-A2") if ("local", t) in runs}
    lan.update(nc2_local_generate())
    qs = sorted(set.intersection(*(set(v) for v in lan.values())))
    bien = {q: len({av3.chuan_hoa(v[q]) for v in lan.values()}) for q in qs}
    # nhóm các lần trùng nhau trên cả 40 test (sau chuẩn hoá)
    vec = {k: tuple(av3.chuan_hoa(v[q]) for q in qs) for k, v in lan.items()}
    nhom: dict = {}
    for k, v in vec.items():
        nhom.setdefault(v, []).append(k)
    cap_doi = {k: sum(1 for i in range(len(qs)) if vec[k][i] != vec["NC3-golden"][i]) for k in vec if k != "NC3-golden"}
    thu_tu = [{"run": m["run"], "ts": m["ts"], "ts_end": m["ts_end"],
               "phut": round((datetime.fromisoformat(m["ts_end"]) - datetime.fromisoformat(m["ts"])).total_seconds() / 60, 1),
               "model": m.get("model"), "api_version": m.get("api_version")}
              for m in manifest if m["arm"] == "local" and m.get("ts") and m.get("ts_end")]
    return {"n_test": len(qs), "lan": sorted(lan), "bien_the_moi_test": dict(sorted(
        {k: sum(1 for v in bien.values() if v == k) for k in set(bien.values())}.items())),
            "nhom_trung_nhau": sorted(sorted(v) for v in nhom.values()), "khac_golden_nc3": cap_doi,
            "thu_tu_local": thu_tu}


def n3(runs, cau) -> dict:
    out = {}
    for (arm, run), R in sorted(runs.items()):
        if run == "golden":
            continue
        g = runs[(arm, "golden")]
        out[f"{arm}|{run}"] = {st: av3b.s3_mo_rong(g, R, st, cau) for st in ("classify", "generate")
                               if any(k[0] == st for k in R)}
    tong = {}
    for nhom, loc in (("thay_doi", lambda r: r not in CTL), ("doi_chung", lambda r: r in CTL)):
        for arm in ("hosted", "local", "ca_hai"):
            for st in ("classify", "generate"):
                t = {}
                for k, v in out.items():
                    a, r = k.split("|")
                    if not loc(r) or (arm != "ca_hai" and a != arm) or st not in v:
                        continue
                    for kk, vv in v[st].items():
                        if kk != "wilson":
                            t[kk] = t.get(kk, 0) + vv
                if t:
                    t["wilson_bo_sot"] = list(av3.wilson(t["bo_sot"], t["doi_that"]))
                    t["wilson_bo_sot_tra_loi_duoc"] = list(av3.wilson(t["bo_sot_tra_loi_duoc"], t["that_tra_loi_duoc"]))
                    t["wilson_dec_bat"] = list(av3.wilson(t["dec_bat"], t["doi_that"]))
                    t["wilson_art_chinh_xac"] = list(av3.wilson(t["art_do_that"], t["art_do"]))
                    t["wilson_dec_chinh_xac"] = list(av3.wilson(t["dec_do_that"], t["dec_do"]))
                tong[f"{nhom}|{arm}|{st}"] = t
    # sót theo chiều (generate, các lần thay đổi): đúng→sai (hồi quy) và sai→đúng
    chieu = {}
    for nhom, loc in (("thay_doi", lambda r: r not in CTL), ("doi_chung", lambda r: r in CTL)):
        t = {"that_dung_sang_sai": 0, "sot_dung_sang_sai": 0, "that_sai_sang_dung": 0, "sot_sai_sang_dung": 0}
        for (arm, run), R in runs.items():
            if run == "golden" or not loc(run):
                continue
            g = runs[(arm, "golden")]
            for (st, q), it in R.items():
                if st != "generate" or not it.get("ok") or not g.get((st, q), {}).get("ok"):
                    continue
                a0, a1 = av3.dung(st, g[(st, q)], cau[q]), av3.dung(st, it, cau[q])
                if a0 is None or a1 is None or a0 == a1:
                    continue
                k = "dung_sang_sai" if a0 else "sai_sang_dung"
                t["that_" + k] += 1
                ra = av3.chuan_hoa(it["artefact"]) != av3.chuan_hoa(g[(st, q)]["artefact"])
                t["sot_" + k] += int(ra and it["decision"] == g[(st, q)]["decision"])
        t["wilson_sot_dung_sang_sai"] = list(av3.wilson(t["sot_dung_sang_sai"], t["that_dung_sang_sai"]))
        t["wilson_sot_sai_sang_dung"] = list(av3.wilson(t["sot_sai_sang_dung"], t["that_sai_sang_dung"]))
        chieu[nhom] = t
    n_khong = sum(1 for q in {k[1] for k in runs[("hosted", "golden")]} if cau[q].impossible)
    return {"theo_lan": out, "tong": tong, "generate_sot_theo_chieu": chieu, "oracle_khong_tra_loi_duoc": n_khong,
            "oracle_n": len({k[1] for k in runs[("hosted", "golden")]})}


def n6(runs) -> dict:
    out = {}
    for arm in ("local", "hosted"):
        for run in ("R1-B", "R1-A2", "P1", "M1", "P2", "T1"):
            if (arm, run) not in runs:
                continue
            g, R = runs[(arm, "golden")], runs[(arm, run)]
            for st in ("route", "classify", "generate"):
                x = av3b.dem_do(g, R, st)
                out[f"{arm}|{run}|{st}"] = {k: x[k] for k in ("n", "dec_do", "art_do", "dec_do_parse_fail")}
    v2 = json.loads((REPO / "study" / "analysis_v2" / "out" / "numbers_v2.json").read_text(encoding="utf-8"))
    nc2 = [r for r in v2["oracle"]["silent_runtime_update"]]
    return {"dem": out, "nc2_doan_B": nc2}


def vi_du(runs, cau) -> dict:
    """N8: ứng viên ví dụ (generate): (i) decision sót — tính đúng đổi, decision không đổi, artefact đổi;
    (ii) artefact đỏ mà tính đúng và decision không đổi. Chỉ chọn câu và đầu ra không có số đứng riêng (cổng số)."""
    so = re.compile(r"(?<![\w.])\d")
    out = {"sot": [], "art_do_khong_doi": []}
    for (arm, run), R in sorted(runs.items()):
        if run in ("golden",) + CTL:
            continue
        g = runs[(arm, "golden")]
        for (st, q), it in sorted(R.items()):
            if st != "generate" or not it.get("ok") or not g.get((st, q), {}).get("ok"):
                continue
            gi, c = g[(st, q)], cau[q]
            a0, a1 = av3.dung(st, gi, c), av3.dung(st, it, c)
            rd = it["decision"] != gi["decision"]
            ra = av3.chuan_hoa(it["artefact"]) != av3.chuan_hoa(gi["artefact"])
            txt = c.question + gi["artefact"] + it["artefact"] + " ".join(c.answers)
            if so.search(txt) or len(gi["artefact"]) > 400 or len(it["artefact"]) > 400:
                continue
            rec = {"arm": arm, "run": run, "qid": q, "question": c.question, "gold": list(c.answers)[:2],
                   "dec_golden": gi["decision"], "dec_run": it["decision"], "golden": gi["artefact"], "run_out": it["artefact"],
                   "dung_golden": a0, "dung_run": a1}
            if a0 != a1 and ra and not rd and len(out["sot"]) < 4:
                out["sot"].append(rec)
            if a0 == a1 and ra and not rd and len(out["art_do_khong_doi"]) < 4:
                out["art_do_khong_doi"].append(rec)
    return out


def n2b() -> dict:
    """POST HOC trên dữ liệu V2-09 (đọc sau phân tích đăng ký, 14-11): nhóm các lần pinned generate (V2-08 + V2-09)
    có câu trả lời chuẩn hoá trùng nhau trên cả 40 câu; ghi lần nào là lần ĐẦU sau khi khởi động server."""
    f = RES / "S3B_20261113_v1.jsonl"
    if not f.exists():
        return {}
    b, man_b = av3.doc(f, RES / "S3B_20261113_v1.manifest.jsonl")
    a, _ = av3.doc(RES / "S3_20261112_v1.jsonl", RES / "S3_20261112_v1.manifest.jsonl")
    lan = {}
    for t in ("golden", "C1", "C2", "C3", "R1-B", "R1-A2"):
        lan[f"V2-08 {t}"] = a[("local", t)]
    for t in ("golden", "C1", "C2", "C3", "D1", "D2", "D3", "B1", "A1", "B2", "A2", "B3", "A3"):
        lan[f"V2-09 {t}"] = b[("local", t)]
    dau = {"V2-08 R1-B", "V2-08 R1-A2", "V2-09 golden", "V2-09 B1", "V2-09 A1", "V2-09 B2", "V2-09 A2",
           "V2-09 B3", "V2-09 A3"}
    qs = sorted(q for (s, q) in lan["V2-09 golden"] if s == "generate")
    nhom: dict = {}
    for k, R in lan.items():
        v = tuple(av3.chuan_hoa(R[("generate", q)]["artefact"]) for q in qs)
        nhom.setdefault(v, []).append(k)
    ds = [{"lan": sorted(g), "server": "0.40.16" if any("B" in x.split()[1] for x in g) else "0.30.10",
           "dau_sau_khoi_dong": sorted(x for x in g if x in dau)} for g in nhom.values()]
    ds.sort(key=lambda x: -len(x["lan"]))
    return {"_nhan": "post hoc", "nhom": ds, "n_lan": len(lan), "lan_dau_sau_khoi_dong": sorted(dau),
            "nhom_lan_dau_A": next(len(x["lan"]) for x in ds if "V2-09 golden" in x["lan"]),
            "nhom_lan_dau_B": next(len(x["lan"]) for x in ds if "V2-09 B1" in x["lan"])}


def wilson_tieu_chuan(k, n):
    """luật A04.4 cho dự đoán 'stable': đúng khi ≤ 5 % và cận trên Wilson ≤ 10 %; sai khi ≥ 20 % hoặc > 12,5 %."""
    p = k / n
    hi = av3.wilson(k, n)[1]
    if p <= 0.05 and hi <= 0.10:
        return "đúng"
    if p >= 0.20 or p > 0.125:
        return "sai"
    return "không phân định"


def kiem() -> dict:
    ph = json.loads((REPO / "study" / "analysis_v2_posthoc" / "out" / "numbers_v2_posthoc.json").read_text(encoding="utf-8"))
    v3 = json.loads((REPO / "study" / "analysis_v3" / "out" / "numbers_v3.json").read_text(encoding="utf-8"))
    dv = ph["don_vi"]
    out = {"registered_MD3_goc_dung": dv["cap_dang_ky_1to5_MD3_goc"]["17"], "registered_MD3R_dung": dv["cap_dang_ky_1to5"]["17"]}
    for key in ("cap_dang_ky_1to5", "cap_dang_ky_1to5_MD3_goc", "chinh_V2-07_cung_runtime"):
        o = dv[key]["o"]
        v = {u: wilson_tieu_chuan(x["k"], x["n"]) for u, x in o.items() if u not in ("26", "27", "28", "29")}
        out[f"naive_{key}"] = {"đúng": sum(1 for x in v.values() if x == "đúng"), "sai": sum(1 for x in v.values() if x == "sai"),
                               "không phân định": sum(1 for x in v.values() if x == "không phân định"), "n": len(v)}
    art_do = art_that = 0
    for A in v3["arms"].values():
        for r, R in A["runs"].items():
            if r in CTL:
                continue
            S = R["stages"].get("classify")
            if S and "S3" in S:
                art_do += S["S3"]["art_do"]
                art_that += S["S3"]["art_do_doi_that"]
    out["classify_art_chinh_xac"] = [art_that, art_do]
    out["wilson_10_58"] = list(av3.wilson(10, 58))
    return out


def main() -> int:
    runs, manifest = av3.doc(RES / "S3_20261112_v1.jsonl", RES / "S3_20261112_v1.manifest.jsonl")
    _, cau_ds = corpus.nap()
    cau = {c.qid: c for c in cau_ds}
    N = {"_nhan": "post hoc — viết 13-11-2026 sau khi biết kết quả NC3 và đọc phản biện vòng 2; không đổi verdict đăng ký",
         "N1": n1(runs), "N2": n2(runs, manifest), "N3": n3(runs, cau), "N6": n6(runs), "KIEM": kiem(), "VI_DU": vi_du(runs, cau), "N2B": n2b()}
    N = av3.lam_tron(N)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "numbers_v3_posthoc.json").write_text(json.dumps(N, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                                         encoding="utf-8", newline="\n")
    print("xong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
