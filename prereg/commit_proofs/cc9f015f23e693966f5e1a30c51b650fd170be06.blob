"""Nghiên cứu 3 (V2-08): test offline, hàm gọi giả — không lời gọi thật nào."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from p2 import corpus, s3  # noqa: E402


def du_lieu_gia():
    q = {f"q{i}": corpus.Cau(f"q{i}", f"Question {i}?", f"d{i:04d}", i % 2 == 0, (f"ans{i}",), "T") for i in range(4)}
    by_id = {f"d{i:04d}": {"id": f"d{i:04d}", "text": f"text {i}"} for i in range(6)}
    return {"q": q, "by_id": by_id, "idx": None}


@pytest.fixture(autouse=True)
def bm25_gia(monkeypatch):
    monkeypatch.setattr(s3.bm25, "search", lambda idx, text, k: [(f"d{i:04d}", 1.0) for i in range(k)])


def test_thu_tu_co_dinh_va_golden_dau():
    a, b = s3.thu_tu("hosted"), s3.thu_tu("hosted")
    assert a == b and a[0] == "golden" and sorted(a[1:]) == sorted(s3.RUNS_HOSTED)
    assert s3.thu_tu("local")[0] == "golden"
    assert "Q1" not in s3.RUNS_LOCAL                       # V2-08 (c): bỏ trước khi chạy


def test_bien_the():
    assert s3.bien_the("K1").k == 3 and s3.bien_the("K1").stages_chay == ("generate",)
    assert s3.bien_the("T1").temperature == 0.8
    assert s3.bien_the("M1").model_hosted == "gemini-2.5-flash-lite" and s3.bien_the("M1").model_local == "qwen2.5:7b"
    assert s3.bien_the("C2").prompt is s3.GOC and s3.bien_the("R1-B").runtime == s3.OLLAMA_B
    for st in s3.STAGES:
        assert s3.PROMPT_P1[st] != s3.GOC[st] and s3.PROMPT_P2[st] != s3.GOC[st]
    assert "REFUSE" not in s3.PROMPT_P2["route"] and "Cite" not in s3.PROMPT_P2["generate"]


def test_mot_lan_hosted_gia():
    seen = []

    def h(prompt, model, temp):
        seen.append((model, temp))
        if "JSON" in prompt:
            return {"text": '{"language": "en", "answerable": true}', "usage": {"in": 10, "out": 2}}
        if "router" in prompt or "route" in prompt:
            return {"text": "ROUTE: RETRIEVE. REASON: x.", "usage": {"in": 10, "out": 2}}
        return {"text": "ans1 [d0001]", "usage": {"in": 10, "out": 2}}

    items, u = s3.mot_lan("hosted", s3.bien_the("golden"), ["q1", "q2"], s3.Goi(hosted=h, ngu=lambda s: None),
                          data=du_lieu_gia())
    assert len(items) == 6 and all(i["ok"] for i in items)
    assert {i["decision"] for i in items if i["stage"] == "classify"} == {"answerable"}
    assert {i["decision"] for i in items if i["stage"] == "route"} == {"RETRIEVE"}
    assert u == {"in": 60, "out": 12} and {m for m, _ in seen} == {"gemini-2.5-flash"}


def test_thu_lai_429_roi_loi():
    n = {"k": 0}

    def h(prompt, model, temp):
        n["k"] += 1
        raise s3.Loi429("429")

    items, _ = s3.mot_lan("hosted", s3.bien_the("K1"), ["q1"], s3.Goi(hosted=h, ngu=lambda s: None), data=du_lieu_gia())
    assert len(items) == 1 and not items[0]["ok"] and n["k"] == len(s3.LUI) + 1
    assert s3.hong(items)


def test_k1_dung_top3(monkeypatch):
    lay = []
    monkeypatch.setattr(s3.bm25, "search", lambda idx, text, k: lay.append(k) or [(f"d{i:04d}", 1.0) for i in range(k)])
    s3.mot_lan("local", s3.bien_the("K1"), ["q1"], s3.Goi(local=lambda p, m, t: {"text": "NOT IN DOCUMENTS"}),
               data=du_lieu_gia())
    assert lay == [3]


def test_usd():
    assert abs(s3.usd("gemini-2.5-flash", {"in": 1_000_000, "out": 1_000_000}) - 2.80) < 1e-9
