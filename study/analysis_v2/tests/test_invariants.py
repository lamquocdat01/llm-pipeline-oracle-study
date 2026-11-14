"""Bất biến của phân tích v2 — chạy trên dữ liệu GIẢ (`fake.py`), không đọc dữ liệu thật.

    python -m pytest -q study/analysis_v2/tests
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

AV2 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AV2))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fake  # noqa: E402
import run_analysis  # noqa: E402
from av2 import analysis, logit  # noqa: E402
from av2.cells import BY_O, CAP_MARGIN, DV_N3, DV_P2, DV_P3H, O_ALL  # noqa: E402
from av2.stats import KHONG, ON, newcombe, phan_quyet, wilson  # noqa: E402

B_TEST = 40


@pytest.fixture(scope="module")
def gia(tmp_path_factory):
    d = fake.make(tmp_path_factory.mktemp("fake"))
    out = tmp_path_factory.mktemp("out")
    run_analysis.main(["--data", str(d), "--out", str(out), "--B", str(B_TEST), "--no-fig"])
    N = json.loads((out / "numbers_v2.json").read_text(encoding="utf-8"))
    return d, out, N


# ---------------------------------------------------------------- thống kê = số v1.1 đã công bố
def test_wilson_newcombe_khop_v11():
    assert round(wilson(0, 50)[1], 4) == 0.0713          # §6: n = 50 → cận trên 7,1 %
    assert round(wilson(0, 30)[1], 4) == 0.1135          # CP0: "0/30 ≤ 10 %" sai Wilson (đúng 11,3 %)
    d, lo, hi = newcombe(40, 40, 10, 40)                  # M6 routing-hosted: 0,750 (0,575–0,858)
    assert (round(d, 3), round(lo, 3), round(hi, 3)) == (0.75, 0.575, 0.858)
    assert [round(x, 3) for x in wilson(9, 50)] == [0.098, 0.308]


def test_phan_quyet_luat_s6():
    assert phan_quyet(ON, 10, 200)["phan_quyet"] == "đúng"
    assert phan_quyet(ON, 11, 200)["phan_quyet"] == "không phân định"
    assert phan_quyet(ON, 26, 200)["phan_quyet"] == "sai"            # 13 % > 12,5 %
    assert phan_quyet(ON, 1, 50)["phan_quyet"] == "không phân định"  # n = 50 chỉ k = 0 đúng
    assert phan_quyet(ON, 0, 50)["phan_quyet"] == "đúng"
    assert phan_quyet(ON, 0, 31)["thieu_luc"] and not phan_quyet(ON, 0, 31)["vao_mau_so"]
    assert phan_quyet(KHONG, 40, 200)["phan_quyet"] == "đúng"
    assert phan_quyet(KHONG, 10, 200)["phan_quyet"] == "sai"
    assert phan_quyet(KHONG, 24, 200)["phan_quyet"] == "sai"         # 12 % < 12,5 %
    assert phan_quyet(KHONG, 30, 200)["phan_quyet"] == "không phân định"


def test_bang_o_khop_prereg():
    assert len(O_ALL) == 29 and len(DV_P2) == 13 and len(DV_N3) == 4 and len(DV_P3H) == 4
    for o in DV_P2 + DV_N3 + DV_P3H:
        c = BY_O[o]
        assert c.tinh_diem
        assert c.du_doan == (KHONG if (c.obs == "art" and c.pin == "delegated") else ON)   # luật §1
    assert all(not BY_O[o].tinh_diem for o in (3, 7, 10, 16, 18, 20, 22, 24))


# ---------------------------------------------------------------- hồi quy
def test_logit_ml_hoi_phuc_he_so():
    rng = np.random.default_rng(0)
    n = 4000
    X = np.column_stack([np.ones(n), rng.integers(1, 5, n), rng.integers(0, 2, n), rng.integers(0, 2, n)]).astype(float)
    b = np.array([0.5, -0.2, 1.0, -0.8])
    y = (rng.random(n) < 1 / (1 + np.exp(-X @ b))).astype(float)
    sep, r = logit.tach(X, y)
    assert not sep and np.max(np.abs(r["beta"] - b)) < 0.25


def test_firth_huu_han_khi_tach_hoan_toan():
    X = np.column_stack([np.ones(200), np.r_[np.ones(100), np.zeros(100)]])
    y = np.r_[np.ones(100), (np.arange(100) % 3 == 0).astype(float)]     # nhóm 1 không đổi lần nào
    sep, _ = logit.tach(X, y)
    assert sep
    r = logit.fit(X, y, firth=True)
    assert r["converged"] and np.all(np.isfinite(r["beta"])) and r["beta"][1] > 0


# ---------------------------------------------------------------- bất biến trên dữ liệu giả
def test_tong_don_vi(gia):
    _, _, N = gia
    assert N["dem_don_vi"] == {"pipeline2": 13, "n3": 4, "p3h_k": 4, "tong": 21}
    for nhom, so in (("pipeline2_13", 13), ("n3_4", 4), ("p3h_4", 4)):
        t = N["tom_tat_don_vi"][nhom]
        assert t["đúng"] + t["sai"] + t["không phân định"] + t["khong_co_cap"] == so


def test_margin_trong_khoang(gia):
    _, _, N = gia
    assert set(N["margin"]) == set(CAP_MARGIN)
    for t, m in N["margin"].items():
        assert -1 <= m["lo"] <= m["margin"] <= m["hi"] <= 1, t
    for k, v in N["oracle"]["o"].items():
        assert -1 <= v["margin_lo"] <= v["margin_margin"] <= v["margin_hi"] <= 1, k


def _doan(ts):
    t = datetime.fromisoformat(ts)
    return "A" if t <= datetime.fromisoformat("2026-11-03T18:06:27+07:00") else (
        "D" if t >= datetime.fromisoformat("2026-11-07T10:57:17+07:00") else "B")


def test_so_cap_khop_dem_task_id(gia):
    """n mỗi ô == số cặp đếm độc lập từ task_id (+ ts cho V2-07(b)), viết lại không dùng av2."""
    d, _, N = gia
    recs = {}
    for f in d.glob("*_v1.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["status"] == "ok":
                recs[r["task_id"]] = r["ts"]
    for c in O_ALL:
        if c.cap == "md3r":
            items = {t.split("|")[2] for t in recs if t.startswith(f"MD3R|{c.stage}|")}
            n = sum(1 for i in items if f"MD3R|{c.stage}|{i}|llama3.1:8b|t0" in recs
                    and f"MD3R|{c.stage}|{i}|llama3.1:8b|t24h" in recs)
        else:
            pre = f"{c.nguon}|{c.stage}|{c.be}|"
            qs = {t[len(pre):].split("|")[0] for t in recs if t.startswith(pre) and t.endswith("|r01")}
            if c.cap == "1to5":
                n = sum(1 for q in qs if f"{pre}{q}|r05" in recs)
            else:
                n = 0
                for q in qs:
                    t1 = recs[f"{pre}{q}|r01"]
                    if _doan(t1) == "B":
                        continue
                    for k in range(5, 11):
                        tk = recs.get(f"{pre}{q}|r{k:02d}")
                        if tk and _doan(tk) != "B" and datetime.fromisoformat(tk) - datetime.fromisoformat(t1) >= timedelta(hours=24):
                            n += 1
                            break
        assert N["don_vi"][str(c.o)]["n"] == n, c.o


def test_oracle_bat_bien(gia):
    _, _, N = gia
    o = N["oracle"]
    assert o["lech_junit"] == 0
    assert o["so_hop_le_hosted_doc"] == 20 and o["so_hop_le_local_doc"] == 20
    assert o["golden"] == "P2O|lan01"
    assert "P2O|lan03" in o["lan_hosted"] and "P2O|lan03" not in o["lan_local"]
    for k, v in o["o"].items():
        assert v["n_tests"] == 40
        assert v["ghep_dec_do_art_khong"] + v["ghep_ca_hai_do"] == v["dec_do"]
    assert {s["task_id"] for s in o["silent_runtime_update"]} == {"P2O|lan03", "P2O|lan04"}


def test_ket_luan_co_mat(gia):
    _, _, N = gia
    for h in ("h1", "h2", "h3"):
        blk = N[h]["chinh"] if h == "h1" else N[h]
        assert blk["ket_luan"] and blk["luat"]
    assert len(N["h1"]["chinh"]["mo_hinh"]["bootstrap"]) == 5
    assert N["v206_p3h"]["co_du_lieu"]


def test_tat_dinh_trung_byte(gia, tmp_path):
    d, out, _ = gia
    run_analysis.main(["--data", str(d), "--out", str(tmp_path), "--B", str(B_TEST), "--no-fig"])
    assert (tmp_path / "numbers_v2.json").read_bytes() == (out / "numbers_v2.json").read_bytes()


def test_csv_du(gia):
    _, out, _ = gia
    for f in ("units_scoring.csv", "margins.csv", "oracle_failure.csv", "h1_logit.csv",
              "runtime_update_exploratory.csv", "p3h_control.csv"):
        assert (out / f).exists() and (out / f).stat().st_size > 0, f


def test_it_hon_5_seed_bi_tu_choi(gia, tmp_path):
    d, _, _ = gia
    with pytest.raises(SystemExit):
        run_analysis.main(["--data", str(d), "--out", str(tmp_path), "--seed", "1"])


def test_gop_bang_tung_hang():
    """Dạng gộp binomial == dạng từng hàng: β ML, β Firth, SE cluster (CR1 viết lại theo hàng)."""
    rng = np.random.default_rng(1)
    G, m = 60, 12
    cl = np.repeat(np.arange(G), m)
    n = G * m
    X = np.column_stack([np.ones(n), rng.integers(1, 5, n), rng.integers(0, 2, n), rng.integers(0, 2, n)]).astype(float)
    u = rng.normal(0, 0.7, G)[cl]
    y = (rng.random(n) < 1 / (1 + np.exp(-(X @ np.array([0.3, 0.2, 1.0, -1.0]) + u)))).astype(float)
    g = logit.gom(X, y, cl)
    for firth in (False, True):
        a = logit.fit(X, y, firth=firth)["beta"]
        b = logit.fit(g["Xp"], g["Y"].sum(0), firth=firth, n=g["Nn"].sum(0))["beta"]
        assert np.allclose(a, b, atol=1e-7)
    b = logit.fit(X, y)["beta"]
    p = 1 / (1 + np.exp(-X @ b))
    inv = np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))
    s = X * (y - p)[:, None]
    meat = sum(np.outer(s[cl == k].sum(0), s[cl == k].sum(0)) for k in range(G))
    se = np.sqrt(np.diag(inv @ meat @ inv * (G / (G - 1)) * ((n - 1) / (n - 4))))
    assert np.allclose(se, logit.se_cluster(g, b), rtol=1e-8)


def test_hau_kiem_co_nhan(gia):
    _, _, N = gia
    hk = N["hau_kiem"]
    assert hk["nhan"].startswith("HẬU KIỂM")
    for v in hk["oracle_local_bien_the"].values():
        assert v["n_tests"] == 40 and len(v["so_test_do_theo_lan"]) == 19
