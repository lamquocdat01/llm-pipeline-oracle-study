r"""P7 — phân tích POST HOC theo phản biện vòng 2 (R2B), chỉ trên dữ liệu đã lưu, không gọi model.
Viết 24-11-2026 SAU khi đã thấy mọi số S3C và sau phản biện R2B. Kết quả: out/numbers_p6_r2b.json;
diễn giải ở P6/POSTHOC_R2B_MD_20261124.md.

    desktop\.venv\Scripts\python.exe study\analysis_p6\run_posthoc_r2b.py

1. Lạnh/ấm (R2B-01): nhánh pinned, stage generate (và classify, route để đối chiếu) của study 3 (S3) và follow-up (S3B).
   Mỗi run được gắn nhãn LẠNH (lượt đầu qua các prompt này sau một lần khởi động server: golden; A* / R1-A2 sau khi quay
   về 0.30.10; B* / R1-B trên 0.40.16) hoặc ẤM (lặp lại prompt gốc trong cùng tiến trình server: C*, D*).
   Báo: ma trận số test khác nhau (decision, exact) giữa mọi cặp run 0.30.10 prompt gốc; số run ấm giống nhau từng byte;
   FA mỗi lần của mọi oracle khi golden là một run ấm (so với các run ấm còn lại); phân lớp chuỗi golden → các control
   theo thứ tự thời gian (Table 3: ổn định / drift / chập chờn).
2. Hai chuẩn ở S3C (R2B-02): ca bỏ sót theo substring và theo S-F1 (lần đầu mỗi thay đổi): giao nhau, câu hỏi, độ dài
   câu trả lời (token) golden → lần thay đổi; độ trùng của hai chuẩn về tính đúng trên 40 câu × (G + 6 thay đổi).
3. Đơn vị mẫu (R2B-04): số câu hỏi chứa ca truly changed / ca bỏ sót; tỉ lệ bỏ sót chỉ trên câu answerable; precision.
4. 7/40 ↔ 5/40 (R2B-06): so golden S3C với golden follow-up, và run 0.40.16 của S3C với của follow-up, ở generate.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations

from common import HERE, NHAN, RES, Emb, av3, cau, dung_sf1, ghi_json, oracle_reds, cluster_ratio
from run_b2 import keys_cho
from run_s3c import doc as doc_s3c

sys.path.insert(0, str(RES.parent))
from p2 import s3c  # noqa: E402

ST = ("classify", "route", "generate")


def raw(run: dict, st: str) -> dict:
    return {q: (i.get("decision"), i.get("artefact")) for (s, q), i in run.items() if s == st and i.get("ok")}


def khac(a: dict, b: dict) -> dict:
    qs = sorted(set(a) & set(b))
    return {"n": len(qs), "dec": sum(a[q][0] != b[q][0] for q in qs),
            "art": sum(av3.chuan_hoa(a[q][1]) != av3.chuan_hoa(b[q][1]) for q in qs),
            "byte": sum(a[q] != b[q] for q in qs)}


def phan_lop(chuoi: list) -> str:
    """Table 3 / B1: số điểm đổi trong chuỗi giá trị theo thời gian."""
    doi = [i for i in range(1, len(chuoi)) if chuoi[i] != chuoi[i - 1]]
    if not doi:
        return "on_dinh"
    if len(doi) == 1:
        return "golden_lech" if doi[0] == 1 else ("drift" if doi[0] <= len(chuoi) - 2 else "chua_phan_loai")
    return "chap_chon"


def lanh_am(ten_file: str, cac_run: list[tuple[str, str]], emb) -> dict:
    """cac_run: [(tên run, 'lanh'|'am')] theo thứ tự thời gian, cùng server 0.30.10, prompt gốc."""
    a, _ = av3.doc(RES / f"{ten_file}.jsonl", RES / f"{ten_file}.manifest.jsonl")
    out = {"run": [{"ten": t, "trang_thai": k} for t, k in cac_run], "stage": {}}
    for st in ST:
        R = {t: raw(a[("local", t)], st) for t, _ in cac_run}
        cap = {f"{x}|{y}": khac(R[x], R[y]) for x, y in combinations([t for t, _ in cac_run], 2)}
        am = [t for t, k in cac_run if k == "am"]
        lanh = [t for t, k in cac_run if k == "lanh"]
        S = {"cap": cap,
             "lanh_giong_nhau_byte": all(cap.get(f"{x}|{y}", cap.get(f"{y}|{x}"))["byte"] == 0 for x, y in combinations(lanh, 2)),
             "am_giong_nhau_byte_tung_cap": {f"{x}|{y}": cap.get(f"{x}|{y}", cap.get(f"{y}|{x}"))["byte"] for x, y in combinations(am, 2)}}
        # FA mỗi lần khi golden là một run ấm (trung bình trên các run ấm còn lại), mọi oracle
        if st == "generate" and len(am) >= 2:
            fa_am = {}
            for g in am:
                dem, n = {}, 0
                for c in am:
                    if c == g:
                        continue
                    for (s, q), gi in a[("local", g)].items():
                        if s != st or not gi.get("ok"):
                            continue
                        it = a[("local", c)].get((s, q))
                        if not it or not it.get("ok"):
                            continue
                        n += 1
                        for k, v in oracle_reds(st, gi, it, emb).items():
                            dem[k] = dem.get(k, 0) + v
                fa_am[g] = {k: v / n for k, v in dem.items()} if n else {}
            keys = keys_cho(st, emb is not None)
            S["fa_golden_am"] = {k: {"tb": sum(fa_am[g].get(k, 0) for g in am) / len(am),
                                     "max": max(fa_am[g].get(k, 0) for g in am)} for k in keys}
            # FA khi golden là golden lạnh (đối chiếu, trên đúng các run ấm)
            g0 = cac_run[0][0]
            dem, n = {}, 0
            for c in am:
                for (s, q), gi in a[("local", g0)].items():
                    if s != st or not gi.get("ok"):
                        continue
                    it = a[("local", c)].get((s, q))
                    if not it or not it.get("ok"):
                        continue
                    n += 1
                    for k, v in oracle_reds(st, gi, it, emb).items():
                        dem[k] = dem.get(k, 0) + v
            S["fa_golden_lanh_tren_am"] = {k: dem.get(k, 0) / n for k in keys} if n else {}
        # phân lớp chuỗi theo thời gian (decision và exact)
        tlist = [t for t, _ in cac_run]
        lop = {"dec": {}, "art": {}}
        for q in sorted(R[tlist[0]]):
            if not all(q in R[t] for t in tlist):
                continue
            for lv, f in (("dec", lambda v: v[0]), ("art", lambda v: av3.chuan_hoa(v[1]))):
                c = phan_lop([f(R[t][q]) for t in tlist])
                lop[lv][c] = lop[lv].get(c, 0) + 1
        S["phan_lop_chuoi"] = lop
        out["stage"][st] = S
    return out


def tok(s: str | None) -> int:
    return len(av3.chuan_hoa(s).split())


def hai_chuan_s3c() -> dict:
    runs = doc_s3c()
    C = cau()
    g = runs["G"]
    st = "generate"
    out = {"theo_thay_doi": {}, "ca_sot": {"chinh": [], "sf1": []}}
    dong_y = n_cap = 0
    for x in ("P1", "P2", "M1", "K1", "T1", "R1-B"):
        r = runs[f"{x}-1"]
        for (s, q), gi in sorted(g.items()):
            if s != st:
                continue
            it = r.get((s, q))
            c = C[q]
            a0, a1 = av3.dung(st, gi, c), av3.dung(st, it, c)
            b0, b1 = dung_sf1(gi, c), dung_sf1(it, c)
            dec_do = it["decision"] != gi["decision"]
            for std, (u0, u1) in (("chinh", (a0, a1)), ("sf1", (b0, b1))):
                if u0 is not None and u1 is not None and u0 != u1 and not dec_do:
                    out["ca_sot"][std].append({"thay_doi": x, "qid": q, "chieu": "dung_sang_sai" if u0 else "sai_sang_dung",
                                               "impossible": bool(c.impossible), "tok_golden": tok(gi["artefact"]),
                                               "tok_lan": tok(it["artefact"])})
    for (s, q), gi in sorted(g.items()):
        if s != st:
            continue
        for t in ["G"] + [f"{x}-1" for x in ("P1", "P2", "M1", "K1", "T1", "R1-B")]:
            it = runs[t].get((s, q))
            u, v = av3.dung(st, it, C[q]), dung_sf1(it, C[q])
            if u is not None and v is not None:
                n_cap += 1
                dong_y += int(bool(u) == bool(v))
    k = lambda e: (e["thay_doi"], e["qid"])  # noqa: E731
    A, B = {k(e) for e in out["ca_sot"]["chinh"]}, {k(e) for e in out["ca_sot"]["sf1"]}
    out["giao"] = {"chung": len(A & B), "chi_chinh": len(A - B), "chi_sf1": len(B - A),
                   "cau_hoi_chinh": len({q for _, q in A}), "cau_hoi_sf1": len({q for _, q in B}),
                   "cau_hoi_hop": len({q for _, q in A | B}), "cau_hoi_chung": len({q for _, q in A} & {q for _, q in B})}
    out["dong_y_hai_chuan"] = {"dong_y": dong_y, "n": n_cap, "ty_le": dong_y / n_cap}
    for std in ("chinh", "sf1"):
        L = out["ca_sot"][std]
        out[f"do_dai_{std}"] = {"tok_golden_tb": sum(e["tok_golden"] for e in L) / len(L),
                                "tok_lan_tb": sum(e["tok_lan"] for e in L) / len(L),
                                "dai_hon": sum(e["tok_lan"] > e["tok_golden"] for e in L),
                                "ngan_hon": sum(e["tok_lan"] < e["tok_golden"] for e in L), "n": len(L)}
    # đơn vị mẫu: truly changed theo câu hỏi, tỉ lệ chỉ trên câu answerable
    for std, f in (("chinh", av3.dung), ("sf1", dung_sf1)):
        that, sot, theo_cau = [], 0, {}
        for x in ("P1", "P2", "M1", "K1", "T1", "R1-B"):
            r = runs[f"{x}-1"]
            for (s, q), gi in g.items():
                if s != st:
                    continue
                it = r.get((s, q))
                u0, u1 = f(gi, C[q]) if std == "sf1" else f(st, gi, C[q]), f(it, C[q]) if std == "sf1" else f(st, it, C[q])
                if u0 is not None and u1 is not None and u0 != u1:
                    that.append((x, q, C[q].impossible))
                    miss = it["decision"] == gi["decision"]
                    sot += miss
                    v = theo_cau.setdefault(q, [0, 0])
                    v[0] += int(miss)
                    v[1] += 1
        tl = [t for t in that if not t[2]]
        sot_tl = len([1 for t in out["ca_sot"][std] if not t["impossible"]])
        out[f"don_vi_{std}"] = {"that": len(that), "sot": sot, "cau_hoi_that": len({q for _, q, _ in that}),
                                "cau_hoi_sot": len({e["qid"] for e in out["ca_sot"][std]}),
                                "that_answerable": len(tl), "sot_answerable": sot_tl,
                                "wilson_answerable": list(av3.wilson(sot_tl, len(tl))) if tl else None,
                                "cum_cau": cluster_ratio([tuple(v) for v in theo_cau.values()])}
    return out


def so_7_5() -> dict:
    a, _ = av3.doc(RES / "S3B_20261113_v1.jsonl", RES / "S3B_20261113_v1.manifest.jsonl")
    runs = doc_s3c()
    st = "generate"
    gB, gS = raw(a[("local", "golden")], st), raw(runs["G"], st)
    bB = [raw(a[("local", t)], st) for t in ("B1", "B2", "B3")]
    bS = raw(runs["R1-B-1"], st)
    return {"golden_s3c_vs_golden_followup": khac(gS, gB),
            "rb_s3c_vs_b1_followup": khac(bS, bB[0]),
            "b_followup_giong_nhau": [khac(bB[0], bB[i]) for i in (1, 2)],
            "b_followup_vs_golden_followup": khac(bB[0], gB),
            "rb_s3c_vs_golden_s3c": khac(bS, gS),
            "rb_s3c_vs_golden_followup": khac(bS, gB),
            "b1_followup_vs_golden_s3c": khac(bB[0], gS)}


def main() -> int:
    emb = Emb()
    out = {"_nhan": NHAN + " — POST HOC sau phản biện R2B (24-11-2026), dữ liệu đã lưu",
           "follow_up": lanh_am("S3B_20261113_v1", [("golden", "lanh"), ("C1", "am"), ("C2", "am"), ("C3", "am"),
                                                     ("D1", "am"), ("D2", "am"), ("D3", "am"),
                                                     ("A1", "lanh"), ("A2", "lanh"), ("A3", "lanh")], emb),
           "study3": lanh_am("S3_20261112_v1", [("golden", "lanh"), ("C2", "am"), ("C1", "am"), ("C3", "am"),
                                                 ("R1-A2", "lanh")], emb),
           "s3c_hai_chuan": hai_chuan_s3c(),
           "so_7_5": so_7_5()}
    ghi_json(HERE / "out" / "numbers_p6_r2b.json", out)
    print("R2B post hoc xong")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
