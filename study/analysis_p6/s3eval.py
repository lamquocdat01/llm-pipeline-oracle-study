r"""Đánh giá oracle trên một bộ lần chạy kiểu study 3 (golden + control + lần thay đổi). Dùng cho B2 (study 3, V2-09)
và cho đo bù S3C (addendum (a)). Mỗi test = (stage, qid). Chuẩn ngoài: `av3.dung` (chính) và `dung_sf1` (thay thế, chỉ
generate)."""
from __future__ import annotations

from collections import defaultdict

from common import av3, cau, dung_sf1, oracle_reds


def chuan(ten: str, st: str, item, c):
    if ten == "sf1" and st == "generate":
        return dung_sf1(item, c)
    return av3.dung(st, item, c)


def cap_test(g: dict, run: dict, st: str):
    for (s, q), gi in sorted(g.items()):
        if s != st or not gi.get("ok"):
            continue
        it = run.get((s, q))
        if it and it.get("ok"):
            yield q, gi, it


def control_reds(g: dict, ctl: list[dict], st: str, emb) -> dict:
    """Mỗi oracle: danh sách số đỏ theo control; tỉ lệ mỗi lần trung bình; tập câu đỏ ở ít nhất một control."""
    per, n_per, cau_do = defaultdict(list), [], defaultdict(set)
    for c in ctl:
        n = 0
        dem = defaultdict(int)
        for q, gi, it in cap_test(g, c, st):
            n += 1
            for k, v in oracle_reds(st, gi, it, emb).items():
                dem[k] += v
                if v:
                    cau_do[k].add(q)
        n_per.append(n)
        for k in dem:
            per[k].append(dem[k])
        for k in set(per) - set(dem):
            per[k].append(0)
    return {"n_moi_lan": n_per, "do": dict(per),
            "ty_le_moi_lan": {k: sum(v) / sum(n_per) for k, v in per.items()} if sum(n_per) else {},
            "cau_do": {k: sorted(v) for k, v in cau_do.items()}}


def thay_doi(g: dict, run: dict, st: str, emb, chuan_ten: str = "chinh") -> list[dict]:
    """Từng test của một lần thay đổi: truly changed, chiều, đỏ theo mọi oracle."""
    C = cau()
    out = []
    for q, gi, it in cap_test(g, run, st):
        a0, a1 = chuan(chuan_ten, st, gi, C[q]), chuan(chuan_ten, st, it, C[q])
        that = a0 is not None and a1 is not None and a0 != a1
        out.append({"qid": q, "that": int(that), "chieu": ("dung_sang_sai" if a0 else "sai_sang_dung") if that else None,
                    **oracle_reds(st, gi, it, emb)})
    return out


def nham_lan(rows: list[dict], k: str) -> dict:
    tp = sum(1 for r in rows if r["that"] and r[k])
    fn = sum(1 for r in rows if r["that"] and not r[k])
    fp = sum(1 for r in rows if not r["that"] and r[k])
    tn = sum(1 for r in rows if not r["that"] and not r[k])
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "recall": tp / (tp + fn) if tp + fn else None,
            "precision": tp / (tp + fp) if tp + fp else None}


def tong(rows: list[dict], keys: list[str]) -> dict:
    return {k: nham_lan(rows, k) for k in keys}
