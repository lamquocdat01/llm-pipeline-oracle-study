"""Oracle P2O (§5, V2-02, V2-04, V2-07(c), V2-05 D6). Tính lại từ file obs bằng đúng hàm của hai bộ pytest
(decision ==, `chuan_hoa` ==) rồi đối chiếu với danh sách test đỏ trong junit của runner (bất biến: 0 lệch).
"""
from __future__ import annotations

import json
from pathlib import Path

from .load import chuan_hoa, gio, rd
from .stats import chua_0, margin, wilson

CAP = (("classify", "hosted"), ("classify", "local"), ("route", "hosted"), ("route", "local"),
       ("retrieve", "bm25"), ("generate", "hosted"), ("generate", "local"))
N_TEST = 280
N_DOC = 20


def hop_le(r: dict) -> bool:
    """V2-05 D2: status ok, đủ 280 test ở cả hai bộ (lần golden không chạy suite)."""
    p = r.get("payload") or {}
    if r.get("status") != "ok":
        return False
    if p.get("golden"):
        return True
    return (p.get("decision") or {}).get("n") == N_TEST and (p.get("artefact") or {}).get("n") == N_TEST


def doc_obs(p: Path) -> dict:
    return {it["key"]: it for it in json.loads(p.read_text(encoding="utf-8"))["items"]}


def phan_tich(p2o: dict, all_recs: list[dict], data: Path) -> dict:
    ok = sorted((r for r in p2o.values() if hop_le(r)), key=lambda r: r["ts"])
    if not ok:
        return {"loi": "không có lần hợp lệ"}
    golden = ok[0]
    assert golden["payload"].get("golden"), "lần hợp lệ đầu phải là golden"
    lan_host = [r["task_id"] for r in ok[:N_DOC]]
    lan_loc = rd.lan_oracle_local([(r["task_id"], r["ts"]) for r in ok], N_DOC)
    by_id = {r["task_id"]: r for r in ok}
    obs = {r["task_id"]: doc_obs(data / "oracle" / r["payload"]["obs"]) for r in ok}
    G = obs[golden["task_id"]]

    memo: dict = {}

    def hong(tid: str, key: str) -> tuple[bool, bool]:
        if (tid, key) in memo:
            return memo[(tid, key)]
        it = obs[tid].get(key)
        if it is None:
            v = (True, True)
        else:
            v = (it["decision"] != G[key]["decision"], chuan_hoa(it["artefact"]) != chuan_hoa(G[key]["artefact"]))
        memo[(tid, key)] = v
        return v

    # bất biến: tính lại == junit của runner, ở mọi lần không phải golden
    lech = 0
    for r in ok[1:]:
        for bo, j in (("decision", 0), ("artefact", 1)):
            tinh = sorted(k for k in G if hong(r["task_id"], k)[j])
            if tinh != sorted(r["payload"][bo]["failed"]):
                lech += 1

    o_ra = {}
    for st, be in CAP:
        ds = lan_loc if be == "local" else lan_host
        keys = sorted(k for k in G if k.startswith(f"{st}|{be}|"))
        dec_f = {k: [hong(t, k)[0] for t in ds[1:]] for k in keys}
        art_f = {k: [hong(t, k)[1] for t in ds[1:]] for k in keys}
        kd = sum(any(v) for v in dec_f.values())
        ka = sum(any(v) for v in art_f.values())
        n = len(keys)
        mg = margin(ka, n, kd, n)
        o_ra[f"{st}|{be}"] = {
            "pin": "delegated" if be == "hosted" else "pinnable", "n_tests": n, "so_lan_doc": len(ds),
            "lan": [by_id[t]["payload"]["lan"] for t in ds],
            "dec_do": kd, "art_do": ka, "dec_wilson": list(wilson(kd, n)), "art_wilson": list(wilson(ka, n)),
            **{f"margin_{k}": v for k, v in mg.items() if k in ("margin", "lo", "hi")},
            "khoang_chua_0": chua_0(mg["lo"], mg["hi"]),
            "ghep_dec_do_art_khong": sum(1 for k in keys if any(dec_f[k]) and not any(art_f[k])),
            "ghep_ca_hai_do": sum(1 for k in keys if any(dec_f[k]) and any(art_f[k])),
            "ghep_art_do_dec_khong": sum(1 for k in keys if any(art_f[k]) and not any(dec_f[k])),
            "luy_ke_dec": [sum(any(v[:i + 1]) for v in dec_f.values()) for i in range(len(ds) - 1)],
            "luy_ke_art": [sum(any(v[:i + 1]) for v in art_f.values()) for i in range(len(ds) - 1)],
        }

    # D6: bảng từng lần (mọi bản ghi P2O, kể cả missed)
    bang = []
    for r in sorted(all_recs, key=lambda r: int(r["task_id"].split("lan")[1])):
        tid = r["task_id"]
        row = {"task_id": tid, "lan": int(tid.split("lan")[1]), "status": r.get("status"), "due": r.get("due"),
               "ts": r.get("ts"), "late_by_s": r.get("late_by_s"), "hop_le": hop_le(r)}
        if hop_le(r):
            row.update(doan=rd.doan(r["ts"]), cach_golden_h=gio(golden["ts"], r["ts"]),
                       trong_20_hosted=tid in lan_host, trong_20_local=tid in lan_loc)
            if tid != golden["task_id"]:
                for st, be in CAP:
                    ks = [k for k in G if k.startswith(f"{st}|{be}|")]
                    row[f"dec_do|{st}|{be}"] = sum(hong(tid, k)[0] for k in ks)
                    row[f"art_do|{st}|{be}"] = sum(hong(tid, k)[1] for k in ks)
                row["dec_do_280"] = sum(hong(tid, k)[0] for k in G)
                row["art_do_280"] = sum(hong(tid, k)[1] for k in G)
        bang.append(row)

    # silent runtime update (V2-07(c)(e)): lần hợp lệ ở đoạn B so golden, ô local
    srt = []
    for r in ok:
        if rd.doan(r["ts"]) != "B":
            continue
        for st, be in CAP:
            ks = [k for k in G if k.startswith(f"{st}|{be}|")]
            srt.append({"task_id": r["task_id"], "cap": f"{st}|{be}", "n": len(ks),
                        "dec_do": sum(hong(r["task_id"], k)[0] for k in ks),
                        "art_do": sum(hong(r["task_id"], k)[1] for k in ks)})
    return {"golden": golden["task_id"], "so_hop_le": len(ok), "lan_hosted": lan_host, "lan_local": lan_loc,
            "so_hop_le_hosted_doc": len(lan_host), "so_hop_le_local_doc": len(lan_loc),
            "missed": sum(1 for r in all_recs if r.get("status") == "missed"),
            "lech_junit": lech, "o": o_ra, "bang_lan": bang, "silent_runtime_update": srt}
