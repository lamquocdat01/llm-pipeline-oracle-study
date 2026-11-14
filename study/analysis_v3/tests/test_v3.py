"""Dữ liệu GIẢ cho phân tích nghiên cứu 3 — kiểm bất biến trước khi đọc dữ liệu thật (V2-08 (h))."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "desktop"))
import av3  # noqa: E402
import run_v3  # noqa: E402

QS = [f"q{i:02d}" for i in range(40)]


def gia(tmp: Path) -> Path:
    """golden; C1–C3 giống golden trừ 2 test artefact đổi; P1: artefact đổi 20 test, decision 0; P2: decision đổi 10 test."""
    res, man = [], []

    def lan(name, f):
        for st in av3.STAGES:
            for i, q in enumerate(QS):
                d, a = f(st, i)
                res.append({"arm": "hosted", "run": name, "bien_the": name, "stage": st, "qid": q, "ok": True,
                            "decision": d, "artefact": a})
        man.append({"arm": "hosted", "run": name, "bien_the": name, "trang_thai": "ok"})

    def g(st, i):
        dec = {"classify": "answerable" if i % 2 else "unanswerable", "route": "RETRIEVE",
               "generate": "gold" if i % 2 else "abstain"}[st]
        art = f"ans{i} [d0001]" if st == "generate" and i % 2 else ("NOT IN DOCUMENTS" if st == "generate" else f"text {i}")
        return dec, art

    lan("golden", g)
    for c in ("C1", "C2", "C3"):
        lan(c, lambda st, i: (g(st, i)[0], g(st, i)[1] + (" x" if i < 2 else "")))
    lan("P1", lambda st, i: (g(st, i)[0], g(st, i)[1] + (" y" if i < 20 else "")))

    def p2(st, i):
        d, a = g(st, i)
        if i < 10:
            d = {"classify": "answerable" if d == "unanswerable" else "unanswerable", "route": "ANSWER",
                 "generate": "nocite"}[st]
            a = a + " changed"
        return d, a
    lan("P2", p2)
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "S3_20261112_v1.jsonl").write_text("\n".join(json.dumps(r) for r in res) + "\n", encoding="utf-8")
    (tmp / "S3_20261112_v1.manifest.jsonl").write_text("\n".join(json.dumps(m) for m in man) + "\n", encoding="utf-8")
    cau = {q: {"impossible": i % 2 == 0, "answers": [f"ans{i}"]} for i, q in enumerate(QS)}
    (tmp / "cau.json").write_text(json.dumps(cau), encoding="utf-8")
    return tmp


def test_chuan_hoa_khop_ban_goc():
    from mrunner.oracle import chuan_hoa
    for s in ["Hello, World!", "  A  b\n", "Tiếng Việt: dấu?", None, "ROUTE: RETRIEVE. REASON: x."]:
        assert av3.chuan_hoa(s) == chuan_hoa(s)


def test_bat_bien_va_tat_dinh(tmp_path):
    d = gia(tmp_path / "data")
    for o in ("o1", "o2"):
        run_v3.main(["--data", str(d), "--out", str(tmp_path / o), "--cau-json", str(d / "cau.json")])
    a = (tmp_path / "o1" / "numbers_v3.json").read_bytes()
    assert a == (tmp_path / "o2" / "numbers_v3.json").read_bytes()
    N = json.loads(a)
    R = N["arms"]["hosted"]["runs"]
    # đối chứng: 2 test artefact đỏ, decision 0
    assert R["C1"]["stages"]["route"]["art_do"] == 2 and R["C1"]["stages"]["route"]["dec_do"] == 0
    # P1: decision yên, artefact đổi ⇒ S2 đạt
    s = R["P1"]["stages"]["route"]
    assert s["dec_do"] == 0 and s["art_do"] == 20 and s["S2"]["dat"] is True
    assert abs(s["delta_art"]["delta"] - 18 / 40) < 1e-9
    # P2: decision đổi 10 ⇒ S1 đạt, Δ_dec = 10/40
    s = R["P2"]["stages"]["classify"]
    assert s["dec_do"] == 10 and s["S1"]["dat"] is True and abs(s["delta_dec"]["delta"] - 0.25) < 1e-9
    # S3 classify: 10 test lật nhãn ⇒ đổi thật 10, decision bắt 10, không bỏ sót
    assert s["S3"]["doi_that"] == 10 and s["S3"]["dec_bat"] == 10 and s["S3"]["bo_sot_dec_ma_art_bat"] == 0
    # S3 generate: nocite ở câu i<10 → câu chẵn (impossible) từ abstain thành nocite: đổi thật; câu lẻ: vẫn chứa đáp án
    g = R["P2"]["stages"]["generate"]["S3"]
    assert g["doi_that"] == 5 and g["dec_bat"] == 5
    # route không có S3
    assert "S3" not in R["P2"]["stages"]["route"]


def test_wilson():
    lo, hi = av3.wilson(0, 40)
    assert lo == 0 and abs(hi - 0.0876) < 1e-3
