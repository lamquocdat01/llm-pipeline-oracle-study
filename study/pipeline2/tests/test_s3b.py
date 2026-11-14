"""Đợt đo bù V2-09: test offline, hàm gọi giả — không lời gọi thật nào."""
from __future__ import annotations

import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import pytest  # noqa: E402

from p2 import corpus, s3, s3b  # noqa: E402


def test_p1p_chi_doi_mot_tu_moi_stage():
    for st in s3.STAGES:
        a, b = s3.GOC[st].split(" "), s3b.PROMPT_P1P[st].split(" ")
        assert len(a) == len(b)                                   # không thêm/bớt từ, không đảo
        khac = [(x, y) for x, y in zip(a, b) if x != y]
        assert len(khac) == 1, (st, khac)
        # phần còn lại giữ nguyên từng ký tự (cả khoảng trắng, thứ tự Passage/Question)
        assert s3b.PROMPT_P1P[st].replace(khac[0][1], khac[0][0], 1) == s3.GOC[st]
    assert s3b.PROMPT_P1P["classify"].index("Passage:") < s3b.PROMPT_P1P["classify"].index("Question:")


def test_mc_qids_ngoai_oracle_va_tat_dinh():
    a, b = s3b.mc_qids(), s3b.mc_qids()
    assert a == b and len(a) == 40 and len(set(a)) == 40
    assert not set(a) & set(s3b.oracle_qids())
    assert set(a) <= set(s3b.plan()["n2_qids"])


def test_thu_tu_co_dinh_doi_chung_truoc_thay_doi():
    h = s3b.HOSTED
    assert h.index("MC-goc") < h.index("MC-P1p") < h.index("golden")
    assert max(h.index(c) for c in ("C1", "C2", "C3")) < h.index("P1p")
    assert s3b.LOCAL_KHOI_A == ["golden", "C1", "C2", "C3", "P1p"]
    assert s3b.LOCAL_R1 == ["B1", "A1", "B2", "A2", "B3", "A3"]


def test_bien_the():
    assert s3b.bien_the("P1p").prompt is s3b.PROMPT_P1P and s3b.bien_the("MC-P1p").prompt is s3b.PROMPT_P1P
    assert s3b.bien_the("B2").runtime == s3.OLLAMA_B and s3b.bien_the("A2").runtime == s3.OLLAMA_A
    assert s3b.bien_the("D1").prompt is s3.GOC
    assert s3b.qids_cho("MC-goc") == s3b.mc_qids() and s3b.qids_cho("C2") == s3b.oracle_qids()
    with pytest.raises(ValueError):
        s3b.bien_the("P1")


@pytest.fixture
def tam(tmp_path, monkeypatch):
    monkeypatch.setattr(s3b, "RESULT", tmp_path / "r.jsonl")
    monkeypatch.setattr(s3b, "MANIFEST", tmp_path / "m.jsonl")
    q = {f"q{i}": corpus.Cau(f"q{i}", f"Question {i}?", f"d{i:04d}", i % 2 == 0, (f"ans{i}",), "T") for i in range(3)}
    data = {"q": q, "by_id": {f"d{i:04d}": {"id": f"d{i:04d}", "text": f"t{i}"} for i in range(6)}, "idx": None}
    monkeypatch.setattr(s3, "du_lieu", lambda: data)
    monkeypatch.setattr(s3.bm25, "search", lambda idx, text, k: [(f"d{i:04d}", 1.0) for i in range(k)])
    monkeypatch.setattr(s3b, "qids_cho", lambda ten: list(q))
    return tmp_path


def test_chay_mot_ghi_file_moi_va_tien(tam):
    import run_s3b
    goi = s3.Goi(hosted=lambda p, m, t: {"text": '{"language":"en","answerable":true}', "model_version": "x",
                                         "usage": {"in": 1000, "out": 100}}, ngu=lambda s: None)
    assert run_s3b.chay_mot("hosted", "golden", {"nhanh": "hosted"}, goi)
    rows = [json.loads(l) for l in (tam / "r.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 9 and all(r["run"] == "golden" for r in rows)
    man = [json.loads(l) for l in (tam / "m.jsonl").read_text(encoding="utf-8").splitlines()]
    assert man[0]["trang_thai"] == "ok" and man[0]["qids"] == "oracle" and man[0]["usd"] > 0
    assert s3b.tien() == pytest.approx(man[0]["usd"])
    assert s3.RESULT.name == "S3_20261112_v1.jsonl"            # file nghiên cứu 3 không bị trỏ lại


def test_hosted_dung_o_tran(tam, monkeypatch):
    import run_s3b
    s3.ghi(s3b.MANIFEST, {"arm": "hosted", "run": "X", "trang_thai": "ok", "usd": 0.18})
    goi_thu = []
    monkeypatch.setattr(run_s3b, "chay_mot", lambda *a, **k: goi_thu.append(a) or True)
    assert run_s3b.hosted(None) == 2 and not goi_thu


def test_khong_ghi_vao_file_khoa():
    assert s3b.RESULT.name.startswith("S3B_") and s3b.MANIFEST.name.startswith("S3B_")
    assert difflib.SequenceMatcher(None, s3b.RESULT.name, s3.RESULT.name).ratio() < 1
