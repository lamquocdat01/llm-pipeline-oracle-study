"""HẬU KIỂM — viết SAU khi đã xem kết quả lần chạy thật đầu tiên (12-11-2026 ~13:15), commit riêng sau FROZEN.
Không dùng cho kết luận H1/H2/H3/V2-06. Mục đích: mô tả cơ chế khả dĩ cho mục "Where the matrix was wrong".

(a) Oracle ô local (0.30.10): mỗi test có bao nhiêu biến thể artefact (chuan_hoa) qua 20 lần A/D, và các lần đỏ có
    đi theo cụm (lần liền nhau trả cùng biến thể) hay rải đều.
(b) M-protocol ô local: cặp lần liền kề (k → k+1) mà CẢ HAI ở đoạn D — đổi trong cùng một runtime, không qua A.
"""
from __future__ import annotations

import json
from pathlib import Path

from .cells import gia_tri
from .load import chuan_hoa, rd
from .stats import wilson


def oracle_bien_the(orc: dict, data: Path, p2o: dict) -> dict:
    by_id = {r["task_id"]: r for r in p2o.values()}
    lan = orc["lan_local"]
    obs = {t: {it["key"]: it for it in json.loads((data / "oracle" / by_id[t]["payload"]["obs"])
                                                  .read_text(encoding="utf-8"))["items"]} for t in lan}
    ra = {}
    for cap in ("classify|local", "route|local", "generate|local"):
        keys = sorted(k for k in obs[lan[0]] if k.startswith(cap + "|"))
        nhieu, maxv = 0, 1
        do_theo_lan = []
        for t in lan[1:]:
            do_theo_lan.append(sorted(k for k in keys if chuan_hoa(obs[t][k]["artefact"])
                                      != chuan_hoa(obs[lan[0]][k]["artefact"])))
        for k in keys:
            v = {chuan_hoa(obs[t][k]["artefact"]) for t in lan}
            nhieu += len(v) > 1
            maxv = max(maxv, len(v))
        lan_do = [lan[i + 1] for i, d in enumerate(do_theo_lan) if d]
        cum = sum(1 for i in range(len(do_theo_lan) - 1) if do_theo_lan[i] and do_theo_lan[i] == do_theo_lan[i + 1])
        ra[cap] = {"n_tests": len(keys), "test_co_hon_1_bien_the": nhieu, "so_bien_the_toi_da": maxv,
                   "lan_co_test_do": lan_do, "so_lan_co_test_do": len(lan_do),
                   "cap_lan_lien_ke_do_trung_tap_test": cum,
                   "so_test_do_theo_lan": [len(d) for d in do_theo_lan]}
    return ra


def cap_lien_ke_d(chuoi: dict) -> list[dict]:
    rows = []
    for nguon, stage in (("P2", "classify"), ("P2", "route"), ("P2", "generate"), ("P3", "route"), ("P3", "generate")):
        n = kd = ka = 0
        for (m, st, be, q), runs in sorted(chuoi.items()):
            if m != nguon or st != stage or be != "local":
                continue
            ks = sorted(k for k in runs if isinstance(k, int))
            for a, b in zip(ks, ks[1:]):
                if rd.doan(runs[a]["ts"]) == "D" and rd.doan(runs[b]["ts"]) == "D":
                    n += 1
                    kd += gia_tri(runs[a], "dec") != gia_tri(runs[b], "dec")
                    ka += gia_tri(runs[a], "art") != gia_tri(runs[b], "art")
        rows.append({"nguon": nguon, "stage": stage, "n_cap": n, "dec_doi": kd, "art_doi": ka,
                     "art_wilson": list(wilson(ka, n)), "dec_wilson": list(wilson(kd, n))})
    return rows


def chay(orc: dict, data: Path, p2o: dict, chuoi: dict) -> dict:
    return {"nhan": "HẬU KIỂM — viết sau khi xem kết quả (12-11-2026), không dùng cho kết luận H",
            "oracle_local_bien_the": oracle_bien_the(orc, data, p2o),
            "mprotocol_cap_lien_ke_trong_D": cap_lien_ke_d(chuoi)}
