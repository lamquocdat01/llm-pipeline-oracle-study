r"""POST HOC lần 2 (P3E, 14-11-2026; viết SAU phản biện nội bộ vòng 3). Chỉ đọc dữ liệu đã khoá:
results/S3_20261112_v1.* (NC3), results/S3B_20261113_v1.* (V2-09), results/oracle/obs_lan*.json (NC2).
Không đổi verdict đăng ký nào.

    python study\analysis_v3_posthoc\run_v3_posthoc2.py   →  out/numbers_v3_posthoc2.json

P1  ca sót ở generate theo chiều, CHỈ trên câu trả lời được (nơi decision có thể sót); danh sách 10 ca sót.
P2  lần nào ở trạng thái golden (generate pinned) và lần đó có được ghi là chạy ngay sau khi khởi động server không.
P3  Δ ở pinned generate của các thay đổi NC3 so với đối chứng V2-09 C1′–C3′ (mức nền "chính" theo luật A3 của V2-09).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
P2 = REPO / "study" / "pipeline2"
sys.path[:0] = [str(REPO / "study" / "analysis_v3"), str(P2)]
import av3  # noqa: E402
from p2 import corpus  # noqa: E402
from p2.runtime_doan import doan  # noqa: E402

RES = P2 / "results"
CTL = ("C1", "C2", "C3")


def nap():
    a, man_a = av3.doc(RES / "S3_20261112_v1.jsonl", RES / "S3_20261112_v1.manifest.jsonl")
    b, man_b = av3.doc(RES / "S3B_20261113_v1.jsonl", RES / "S3B_20261113_v1.manifest.jsonl")
    cau = {c.qid: c for c in corpus.nap()[1]}
    return a, man_a, b, man_b, cau


def p1(a, cau) -> dict:
    t = {"tra_loi_duoc": {"dung_sang_sai": 0, "sot_dung_sang_sai": 0, "sai_sang_dung": 0, "sot_sai_sang_dung": 0},
         "khong_tra_loi_duoc": {"dung_sang_sai": 0, "sot_dung_sang_sai": 0, "sai_sang_dung": 0, "sot_sai_sang_dung": 0}}
    ds = []
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
            k = "dung_sang_sai" if a0 else "sai_sang_dung"
            nhom = "khong_tra_loi_duoc" if cau[q].impossible else "tra_loi_duoc"
            ra = av3.chuan_hoa(it["artefact"]) != av3.chuan_hoa(g[(st, q)]["artefact"])
            sot = int(ra and it["decision"] == g[(st, q)]["decision"])
            t[nhom][k] += 1
            t[nhom]["sot_" + k] += sot
            if sot:
                ds.append({"arm": arm, "run": run, "qid": q, "chieu": k, "decision": it["decision"],
                           "co_trich_dan_golden": "[" in g[(st, q)]["artefact"], "co_trich_dan_run": "[" in it["artefact"]})
    for nhom in t:
        x = t[nhom]
        x["wilson_sot_dung_sang_sai"] = list(av3.wilson(x["sot_dung_sang_sai"], x["dung_sang_sai"]))
        x["wilson_sot_sai_sang_dung"] = list(av3.wilson(x["sot_sai_sang_dung"], x["sai_sang_dung"]))
    return {"theo_nhom": t, "ca_sot": ds}


def vec(R) -> tuple:
    qs = sorted(q for (s, q) in R if s == "generate")
    return tuple(av3.chuan_hoa(R[("generate", q)]["artefact"]) for q in qs)


def p2(a, b, man_b) -> dict:
    """Lần nào trùng golden (generate pinned) + có bản ghi khởi động server ngay trước không."""
    gold = vec(a[("local", "golden")])
    ghi_khoi_dong_b = {"golden", "B1", "A1", "B2", "A2", "B3", "A3", "MC-goc"}   # run_s3b.py gọi khoi_dong() ngay trước
    rows = []
    for t in ("golden", "C1", "C2", "C3", "R1-B", "R1-A2"):
        rows.append({"lan": f"V2-08 {t}", "trung_golden": vec(a[("local", t)]) == gold,
                     "khoi_dong_ghi_nhan": {"golden": None, "R1-B": True, "R1-A2": True}.get(t, False)})
    for t in ("golden", "C1", "C2", "C3", "D1", "D2", "D3", "B1", "A1", "B2", "A2", "B3", "A3"):
        rows.append({"lan": f"V2-09 {t}", "trung_golden": vec(b[("local", t)]) == gold,
                     "khoi_dong_ghi_nhan": t in ghi_khoi_dong_b})
    # NC2: các lần oracle cùng runtime (đoạn A, D); không có bản ghi khởi động server (runner bật `ollama serve` không log)
    man = {}
    for l in (RES / "P2O_20261102_v1.jsonl").read_text(encoding="utf-8").splitlines():
        x = json.loads(l)
        if x.get("status") == "ok":
            man[x["payload"]["obs"]] = x["ts"]
    nc2 = []
    for f in sorted((RES / "oracle").glob("obs_lan*.json")):
        if f.name not in man or doan(man[f.name]) not in ("A", "D"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        its = {it["qid"]: it["artefact"] for it in d["items"] if it["stage"] == "generate" and it["backend"] == "local"}
        qs = sorted(its)
        nc2.append({"lan": f.stem[4:], "ts": man[f.name],
                    "trung_golden": tuple(av3.chuan_hoa(its[q]) for q in qs) == gold})
    # khoảng cách giữa các lần NC2 liên tiếp (giờ)
    ts = sorted(datetime.fromisoformat(x["ts"]) for x in nc2)
    gap = [round((y - x).total_seconds() / 3600, 1) for x, y in zip(ts, ts[1:])]
    return {"lan_nc3_v209": rows, "nc2": nc2, "nc2_khoang_cach_h_min": min(gap), "nc2_khoang_cach_h_max": max(gap),
            "dau_sau_khoi_dong_ghi_nhan_trung_golden": sum(1 for r in rows if r["khoi_dong_ghi_nhan"] is True and
                                                           r["trung_golden"] and "B" not in r["lan"].split()[1]),
            "trung_golden_tong_nc3_v209": sum(1 for r in rows if r["trung_golden"]),
            "khoi_dong_khong_ghi_nhan_trung_golden": [r["lan"] for r in rows if r["khoi_dong_ghi_nhan"] is None and r["trung_golden"]],
            "nc2_trung_golden": sum(1 for x in nc2 if x["trung_golden"]), "nc2_n": len(nc2)}


def p3(a, b) -> dict:
    """Δ = đỏ của lần thay đổi NC3 − tỉ lệ đỏ qua C1′–C3′ (V2-09), cả hai so với golden NC3 (trùng G′ ở generate)."""
    g = a[("local", "golden")]
    ctl = [b[("local", c)] for c in CTL]
    out = {}
    for run in ("P1", "P2", "M1", "T1", "K1", "R1-B"):
        dr = av3.do(g, a[("local", run)], "generate")
        cds = [av3.do(g, c, "generate") for c in ctl]
        qs = [q for q in dr if all(q in c for c in cds)]
        x = {}
        for j, ten in ((0, "dec"), (1, "art")):
            x[ten] = av3.boot_delta([dr[q][j] for q in qs], [sum(c[q][j] for c in cds) / 3 for q in qs])
        out[run] = x
    return out


def main() -> int:
    a, man_a, b, man_b, cau = nap()
    N = {"_nhan": "post hoc lần 2 — 14-11-2026, sau phản biện vòng 3; không đổi verdict đăng ký",
         "P1": p1(a, cau), "P2": p2(a, b, man_b), "P3": p3(a, b)}
    N = av3.lam_tron(N)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "numbers_v3_posthoc2.json").write_text(json.dumps(N, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                                          encoding="utf-8", newline="\n")
    print("xong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
