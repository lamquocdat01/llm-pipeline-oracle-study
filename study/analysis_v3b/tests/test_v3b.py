"""Dữ liệu GIẢ cho phân tích V2-09 — kiểm bất biến trước khi đọc dữ liệu thật (V2-09 (f))."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import av3b  # noqa: E402
import run_v3b  # noqa: E402

QS = [f"q{i:02d}" for i in range(40)]
MC = [f"m{i:02d}" for i in range(40)]


def gia(tmp: Path) -> tuple[Path, Path, Path]:
    """local: golden; C1–C3 = golden; D1–D3: generate decision đổi 6 test; P1p: artefact đổi 20, decision 0;
    B1–B3: route decision đổi 9 test (3 là PARSE_FAIL); A1–A3 = golden. MC: P1p đổi tính đúng classify 1 câu."""
    res, man = [], []

    def g(st, i):
        dec = {"classify": "answerable" if i % 2 else "unanswerable", "route": "RETRIEVE",
               "generate": "gold" if i % 2 else "abstain"}[st]
        art = f"ans{i} [d0001]" if st == "generate" and i % 2 else ("NOT IN DOCUMENTS" if st == "generate" else f"text {i}")
        return dec, art

    def lan(name, f, qs=QS):
        for st in av3b.STAGES:
            for i, q in enumerate(qs):
                d, a = f(st, i)
                res.append({"arm": "local", "run": name, "bien_the": name, "stage": st, "qid": q, "ok": True,
                            "decision": d, "artefact": a})
        man.append({"arm": "local", "run": name, "bien_the": name, "trang_thai": "ok"})

    lan("MC-goc", g, MC)
    lan("MC-P1p", lambda st, i: (("unanswerable" if g(st, i)[0] == "answerable" else "answerable")
                                 if st == "classify" and i == 1 else g(st, i)[0], g(st, i)[1]), MC)
    lan("golden", g)
    for c in ("C1", "C2", "C3", "A1", "A2", "A3"):
        lan(c, g)
    for d in ("D1", "D2", "D3"):
        lan(d, lambda st, i: (("nocite" if st == "generate" and i < 6 else g(st, i)[0]),
                              g(st, i)[1] + (" z" if st == "generate" and i < 6 else "")))
    lan("P1p", lambda st, i: (g(st, i)[0], g(st, i)[1] + (" y" if i < 20 else "")))
    for b in ("B1", "B2", "B3"):
        lan(b, lambda st, i: ((("PARSE_FAIL" if i < 3 else "ANSWER") if st == "route" and i < 9 else g(st, i)[0]),
                              g(st, i)[1] + (" b" if i < 9 else "")))
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "S3B_20261113_v1.jsonl").write_text("\n".join(json.dumps(r) for r in res) + "\n", encoding="utf-8")
    (tmp / "S3B_20261113_v1.manifest.jsonl").write_text("\n".join(json.dumps(m) for m in man) + "\n", encoding="utf-8")
    cau = {q: {"impossible": i % 2 == 0, "answers": [f"ans{i}"]} for i, q in enumerate(QS)}
    cau.update({q: {"impossible": i % 2 == 0, "answers": [f"ans{i}"]} for i, q in enumerate(MC)})
    (tmp / "cau.json").write_text(json.dumps(cau), encoding="utf-8")
    v3 = {"arms": {"local": {"runs": {c: {"stages": {"generate": {"dec_do": x}}} for c, x in
                                      (("C1", 8), ("C2", 4), ("C3", 8))}}}}
    (tmp / "v3.json").write_text(json.dumps(v3), encoding="utf-8")
    return tmp, tmp / "cau.json", tmp / "v3.json"


def chay(tmp: Path) -> dict:
    d, c, v3 = gia(tmp / "d")
    assert run_v3b.main(["--data", str(d), "--cau-json", str(c), "--v3", str(v3), "--out", str(tmp / "o")]) == 0
    return json.loads((tmp / "o" / "numbers_v3b.json").read_text(encoding="utf-8"))


def test_luat_v209(tmp_path):
    A = chay(tmp_path)["arms"]["local"]
    # (b) kiểm thao tác: classify đổi 1 ≤ 2 ⇒ đạt
    assert A["kiem_thao_tac"]["classify"]["doi"] == 1 and A["kiem_thao_tac"]["dat"] is True
    # (b) S2′: decision yên, artefact đỏ ở mọi stage
    for st in av3b.STAGES:
        assert A["S2p"][st]["dat"] is True
    # (a) A2: D khác C′ ở generate decision (6/40), không ở classify
    assert A["A2"]["generate"]["dec"]["khac"] is True and A["A2"]["classify"]["dec"]["khac"] is False
    assert A["lan"]["D2"]["generate"]["dec_do"] == 6 and A["lan"]["C1"]["generate"]["dec_do"] == 0
    # (a) A3: C′ (0) sạch hơn V2-08 (20) ⇒ mức nền chính
    assert A["A3"]["c_moi_la_muc_nen_chinh"] is True and A["A3"]["v208_generate_dec"] == [8, 4, 8]
    # (c) R1: route decision lặp lại; 3 PARSE_FAIL trong 9 decision đỏ mỗi lần B
    assert A["R1"]["stages"]["route"]["dec"]["lap_lai"] is True
    assert A["R1"]["stages"]["classify"]["dec"]["lap_lai"] is False
    assert A["lan"]["B1"]["route"]["dec_do"] == 9 and A["lan"]["B1"]["route"]["dec_do_parse_fail"] == 3
    # S3 mở rộng: D ở generate: 6 decision đổi, nhưng chỉ 3 câu không trả lời được đổi tính đúng (câu trả lời được vẫn chứa đáp án)
    s = A["s3"]["D1"]["generate"]
    assert s["doi_that"] == 3 and s["that_tra_loi_duoc"] == 0 and s["that_khong_tra_loi_duoc"] == 3
    assert s["dung_sang_sai"] == 3 and s["sai_sang_dung"] == 0 and s["bo_sot"] == 0


def test_tat_dinh(tmp_path):
    a = chay(tmp_path / "1")
    b = chay(tmp_path / "2")
    a.pop("inputs"), b.pop("inputs")
    assert a == b
