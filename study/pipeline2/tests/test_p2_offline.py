"""Test offline pipeline 2 (không gọi model): luật decision (PREREG_V2 §3), BM25 tất định, ghim, mẫu N2.

    cd study\pipeline2 && ..\..\desktop\.venv\Scripts\python.exe -m pytest -q tests
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p2 import P2_DIR, bm25, corpus, executors, stages  # noqa: E402


@pytest.mark.parametrize("text,ra", [
    ('```json\n{"language": "en", "answerable": true}\n```', "answerable"),
    ('{"language": "en", "answerable": false}', "unanswerable"),
    ('{"language": "en", "answerable": "False"}', "unanswerable"),
    ('{"language": "en", "answerable": "maybe"}', "PARSE_FAIL"),
    ('{"language": "en"}', "PARSE_FAIL"),
    ("not json", "PARSE_FAIL"),
])
def test_dec_classify(text, ra):
    assert stages.dec_classify(text) == ra


def test_lang_classify_chi_log():
    assert stages.lang_classify('{"language": "EN", "answerable": true}') == "en"


@pytest.mark.parametrize("text,ra", [
    ("ROUTE: RETRIEVE. REASON: x", "RETRIEVE"),
    ("ROUTE: RETRIEVÉ\nREASON: x", "RETRIEVE"),
    ("route: answer. reason: y", "ANSWER"),
    ("**ROUTE:** REFUSE", "REFUSE"),
    ("ROUTE: RETRIEVW: x", "PARSE_FAIL"),
    ("ROUTE: RETRIEVEMETHOD: x", "PARSE_FAIL"),
    ("I would retrieve", "PARSE_FAIL"),
])
def test_dec_route(text, ra):
    assert stages.dec_route(text) == ra


def test_dec_generate():
    assert stages.dec_generate("NOT IN DOCUMENTS", "d0001") == "abstain"
    assert stages.dec_generate("X is Y [d0001][d0002].", "d0001") == "gold"
    assert stages.dec_generate("X is Y [d0002].", "d0001") == "other"
    assert stages.dec_generate("X is Y.", "d0001") == "nocite"
    assert stages.dec_generate("NOT IN DOCUMENTS [d0001]", "d0001") == "gold"


def test_domain():
    assert stages.domain({"title": "www.britannica.com", "uri": "https://vertexaisearch/x"}) == "britannica.com"
    assert stages.domain({"title": "Some Page Title", "uri": "https://en.wikipedia.org/wiki/A"}) == "en.wikipedia.org"


def test_bm25_tat_dinh_va_pha_hoa():
    docs = [{"id": "d0001", "text": "alpha beta"}, {"id": "d0000", "text": "alpha beta"}, {"id": "d0002", "text": "gamma"}]
    idx = bm25.build(docs)
    r = bm25.search(idx, "alpha", 3)
    assert [d for d, _ in r] == ["d0000", "d0001"]
    assert bm25.search(idx, "alpha", 3) == r


co_corpus = pytest.mark.skipif(not corpus.duong_dan().exists(), reason="chưa có corpus ở THS_DATASETS")


@co_corpus
def test_index_ghim():
    pin = json.loads((P2_DIR / "data/index_pin.json").read_text(encoding="utf-8"))
    idx = bm25.nap(P2_DIR / "data/bm25_index.json", pin["sha256"])
    docs, _ = corpus.nap()
    assert len(docs) == pin["n_docs"] == len(idx["ids"])


@co_corpus
def test_mau_n2_loai_smoke_va_on_dinh():
    _, cau = corpus.nap()
    a, b = corpus.mau_n2(cau), corpus.mau_n2(cau)
    assert [c.qid for c in a] == [c.qid for c in b] and len(a) == 200
    assert not {c.qid for c in a} & corpus.smoke_ids(cau)
    assert {c.qid for c in corpus.mau_oracle(cau)} <= {c.qid for c in a}


@co_corpus
def test_plan_khop_mau():
    p = P2_DIR / "runner/plan_p2.json"
    if not p.exists():
        pytest.skip("chưa sinh plan")
    plan = json.loads(p.read_text(encoding="utf-8"))
    _, cau = corpus.nap()
    assert plan["mau"]["n2_qids"] == [c.qid for c in corpus.mau_n2(cau)]
    assert not set(plan["mau"]["n2_qids"]) & set(plan["mau"]["smoke_qids_loai"])
    ids = [t["id"] for t in plan["tasks"]]
    assert len(ids) == len(set(ids))


def test_executor_kinds():
    assert set(executors.executors()) == {"p2_classify", "p2_route", "p2_retrieve", "p2_generate", "p2_live"}


def test_ten_runner_duoc_gate_nhan():
    """core.pid_song / gate._alive_runner nhận runner theo chuỗi `run_m_all` trong cmdline (sự cố 01-11 09:21)."""
    import subprocess
    import psutil
    from mrunner import gate
    from mrunner.core import pid_song
    s = P2_DIR / "scripts" / "run_m_all_p2.py"
    assert s.exists() and "run_m_all" in s.name
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)", str(s)])
    try:
        assert gate._alive_runner(p.pid) is True
        assert "python" in psutil.Process(p.pid).name().lower() and pid_song(p.pid)
    finally:
        p.kill()


def test_plan_oracle_amendment_v2_02():
    """AMENDMENT V2-02 (03-11-2026): P2O = 28 mốc cách 6 h (00/06/12/18 giờ, +07), 7 ngày, cùng 40 câu oracle."""
    from datetime import datetime, timedelta
    p = P2_DIR / "runner/plan_p2.json"
    if not p.exists():
        pytest.skip("chưa sinh plan")
    plan = json.loads(p.read_text(encoding="utf-8"))
    a = plan["amendment_v2_02"]
    o = [t for t in plan["tasks"] if t["m"] == "P2O"][:a["p2o_n"]]     # V2-04 chỉ nới thêm mốc phía sau
    assert len(o) == a["p2o_n"] == 28 and a["doc_hop_le_dau"] == 20 and plan["late_missed_s"] == 7200
    at = [datetime.fromisoformat(t["at"]) for t in o]
    assert at[0] == datetime.fromisoformat(a["p2o_first"]) and at[-1] == datetime.fromisoformat(a["p2o_last"])
    assert all(b - x == timedelta(hours=6) for x, b in zip(at, at[1:])) and at[-1] - at[0] == timedelta(hours=162)
    assert {x.hour for x in at} == {0, 6, 12, 18} and all(x.utcoffset() == timedelta(hours=7) for x in at)
    assert [t["id"] for t in o] == [f"P2O|lan{k:02d}" for k in range(1, 29)]
    assert all(t["params"]["lan"] == k for k, t in enumerate(o, 1))
    assert all(t["params"]["qids"] == plan["mau"]["oracle_qids"] for t in o)
    assert all(t["kind"] == "p2_oracle" and t["hosted"] and t["cho_pause"] and not t.get("khong_missed") for t in o)


def test_kiem_tu_choi_runtime_lech(monkeypatch):
    """AMENDMENT V2-04: runtime Ollama lệch (hoặc không hỏi được) ⇒ kiểm ghim báo lỗi, task không ghi "ok"."""
    from p2 import pin
    model = "qwen2.5:3b"
    for v in ("0.40.15", None):
        monkeypatch.setattr(pin, "phien_ban_ollama", lambda v=v: v)
        assert any("runtime Ollama" in x for x in pin.kiem(model, pin.PIN[model]["manifest_digest"]))
    monkeypatch.setattr(pin, "phien_ban_ollama", lambda: pin.OLLAMA_RUNTIME)
    assert not any("runtime Ollama" in x for x in pin.kiem(model, pin.PIN[model]["manifest_digest"]))


def _nap_runner():
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_m_all_p2", P2_DIR / "scripts" / "run_m_all_p2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _plan_gia(m):
    from datetime import datetime, timedelta
    t0 = datetime.fromisoformat(m.V202_FIRST)
    o = [{"id": f"P2O|lan{k:02d}", "m": "P2O", "kind": "p2_oracle", "hosted": True, "heavy": True, "order": 0, "cho_pause": True,
          "at": (t0 + timedelta(hours=6 * (k - 1))).isoformat(timespec="minutes"), "params": {"lan": k, "qids": ["a", "b"]}}
         for k in range(1, 29)]
    return {"amendment_v2_02": {"p2o_n": 28}, "late_missed_s": 7200,
            "tasks": [{"id": "P2|x|r01", "m": "P2"}, *o, {"id": "P3|y|r01", "m": "P3"}]}


@pytest.mark.parametrize("now,n,cuoi,ke", [
    ("2026-11-07T10:40+07:00", 41, "2026-11-13T12:00+07:00", "P2O|lan17"),     # trước mốc 07-11 12:00
    ("2026-11-07T12:01+07:00", 42, "2026-11-13T18:00+07:00", "P2O|lan18"),     # lỡ cơ hội commit trước 12:00
])
def test_amend_v2_04_luat_noi_moc(now, n, cuoi, ke):
    """T nhỏ nhất sao cho số mốc từ mốc kế tiếp tới T ≥ (20 − v) + 8; lan01..28 và task khác không đổi."""
    from datetime import datetime
    m = _nap_runner()
    plan = _plan_gia(m)
    moi = m.amend_v2_04(plan, {"P2O|lan01", "P2O|lan03", "P2O|lan04"}, datetime.fromisoformat(now))
    a = moi["amendment_v2_04"]
    o = [t for t in moi["tasks"] if t["m"] == "P2O"]
    assert (a["p2o_n"], a["p2o_last"], a["moc_ke_tiep"], a["v_hop_le"]) == (n, cuoi, ke, 3)
    assert a["so_moc_can"] == 25 and a["so_moc_con"] == 25
    assert o[:28] == [t for t in plan["tasks"] if t["m"] == "P2O"]
    assert [t["id"] for t in o] == [f"P2O|lan{k:02d}" for k in range(1, n + 1)]
    assert [t["params"]["lan"] for t in o] == list(range(1, n + 1)) and o[-1]["at"] == cuoi
    assert moi["tasks"][0]["id"] == "P2|x|r01" and moi["tasks"][-1]["id"] == "P3|y|r01"
    with pytest.raises(ValueError):
        m.amend_v2_04(moi, set(), datetime.fromisoformat(now))


def test_plan_oracle_amendment_v2_04():
    """Plan thật: nhịp 6 h, đủ mốc theo luật V2-04, 19 450 task không phải P2O trùng khít (sha256)."""
    from datetime import datetime, timedelta
    p = P2_DIR / "runner/plan_p2.json"
    if not p.exists():
        pytest.skip("chưa sinh plan")
    plan = json.loads(p.read_text(encoding="utf-8"))
    a = plan["amendment_v2_04"]
    o = [t for t in plan["tasks"] if t["m"] == "P2O"]
    at = [datetime.fromisoformat(t["at"]) for t in o]
    assert len(o) == a["p2o_n"] and o[-1]["at"] == a["p2o_last"] and plan["late_missed_s"] == 7200 and a["doc_hop_le_dau"] == 20
    assert all(b - x == timedelta(hours=6) for x, b in zip(at, at[1:])) and {x.hour for x in at} == {0, 6, 12, 18}
    assert o[0]["at"] == "2026-11-03T12:00+07:00" and o[27]["at"] == "2026-11-10T06:00+07:00"
    assert [t["id"] for t in o] == [f"P2O|lan{k:02d}" for k in range(1, len(o) + 1)]
    assert all(t["params"]["lan"] == k and t["params"]["qids"] == plan["mau"]["oracle_qids"] for k, t in enumerate(o, 1))
    assert all(t["kind"] == "p2_oracle" and t["hosted"] and t["cho_pause"] and not t.get("khong_missed") for t in o)
    i_ke = [t["id"] for t in o].index(a["moc_ke_tiep"])
    assert len(o) - i_ke >= (20 - a["v_hop_le"]) + 8 == a["so_moc_can"]
    khac = [t for t in plan["tasks"] if t["m"] in ("P2", "P3", "MD3")]     # khối thêm sau V2-04 không tính
    assert len(khac) == a["n_task_khac"] == 19450 and _nap_runner()._bam_tasks(khac) == a["sha256_task_khac"]


def test_amend_v2_07_chi_them_md3r():
    """V2-07(d): MD3R cùng kind + params với t0 của MD3; task cũ không đổi; từ chối chạy hai lần."""
    m = _nap_runner()
    p = {"tasks": [{"id": "MD3|M2|a|l|t0", "m": "MD3", "kind": "m2_local", "hosted": False, "heavy": True, "order": 6, "params": {"x": 1}},
                   {"id": "MD3|M2|a|l|t24h", "m": "MD3", "kind": "m2_local", "after": {"task": "MD3|M2|a|l|t0", "delta_s": 86400}, "params": {"x": 1}},
                   {"id": "MD3|M2|a|l@t08|probe", "m": "MD3", "kind": "m2_local", "params": {"x": 2}}],
         "results": {"MD3": "r/MD3.jsonl"}, "amendment_v2_04": {"n": 1}}
    with pytest.raises(ValueError):
        m.amend_v2_07(p)                                 # chỉ nhận đúng 150 t0
    m.V207_N_T0 = 1
    moi = m.amend_v2_07(p)
    assert moi["tasks"][:3] == p["tasks"] and moi["amendment_v2_07"]["sha256_task_cu"] == m._bam_tasks(p["tasks"])
    t0, t24 = moi["tasks"][3:]
    assert (t0["id"], t0["m"], t0["kind"], t0["params"]) == ("MD3R|M2|a|l|t0", "MD3R", "m2_local", {"x": 1}) and "after" not in t0
    assert t24["id"] == "MD3R|M2|a|l|t24h" and t24["after"] == {"task": "MD3R|M2|a|l|t0", "delta_s": 86400}
    assert moi["results"]["MD3R"].endswith("MD3R_20261102_v1.jsonl")
    with pytest.raises(ValueError):
        m.amend_v2_07(moi)


def test_plan_amendment_v2_07():
    """Plan thật: 300 task MD3R, cùng params với MD3, mọi task trước đó trùng khít (sha256)."""
    p = P2_DIR / "runner/plan_p2.json"
    if not p.exists():
        pytest.skip("chưa sinh plan")
    plan = json.loads(p.read_text(encoding="utf-8"))
    a = plan["amendment_v2_07"]
    cu = plan["tasks"][:a["n_task_cu"]]
    assert a["n_task_cu"] == 19491 and _nap_runner()._bam_tasks(cu) == a["sha256_task_cu"]
    r = [t for t in plan["tasks"] if t["m"] == "MD3R"]
    assert len(r) == a["md3r_n"] == 300 and plan["tasks"][a["n_task_cu"]:a["n_task_cu"] + 300] == r
    by = {t["id"]: t for t in cu}
    for t in r:
        g = by[t["id"].replace("MD3R|", "MD3|", 1).rsplit("|", 1)[0] + "|t0"]
        assert t["params"] == g["params"] and t["kind"] == g["kind"] and t["heavy"] and not t["hosted"] and not t.get("at")
        if t["id"].endswith("|t24h"):
            assert t["after"] == {"task": t["id"].rsplit("|", 1)[0] + "|t0", "delta_s": 86400}
        else:
            assert t["id"].endswith("|t0") and "after" not in t


@pytest.mark.parametrize("ts,ra", [
    ("2026-11-03T18:06:27+07:00", "A"), ("2026-11-03T20:15:55+07:00", "B"),
    ("2026-11-07T10:57:16+07:00", "B"), ("2026-11-07T10:57:17+07:00", "D"),
])
def test_doan_runtime(ts, ra):
    from p2.runtime_doan import doan
    assert doan(ts) == ra


def test_chon_k_cung_runtime():
    """V2-07(b): k nhỏ nhất ≥ 5, cả hai lần ở A/D, cách ≥ 24 h."""
    from p2.runtime_doan import chon_k
    a, b, d1, d2 = "2026-11-01T10:00+07:00", "2026-11-03T22:00+07:00", "2026-11-07T23:00+07:00", "2026-11-08T05:00+07:00"
    assert chon_k({1: a, 5: b, 6: d1, 7: d2}) == 6          # r05 ở B thì bỏ
    assert chon_k({1: a, 5: d1, 6: d2}) == 5                # r05 ở D: đúng cặp 1→5
    assert chon_k({1: a, 2: "2026-11-02T10:00+07:00", 5: b}) is None
    assert chon_k({1: b, 6: d1}) is None                    # lần 1 ở B
    assert chon_k({5: d1}) is None
    assert chon_k({1: "2026-11-07T11:00+07:00", 5: "2026-11-08T05:00+07:00", 6: "2026-11-08T11:00+07:00"}) == 6   # 1→5 chưa đủ 24 h


def test_lan_oracle_local_bo_doan_b():
    """V2-07(c): lan03, lan04 (đoạn B) không vào 20 lần của ô local; lấy đúng n lần đầu thuộc A/D."""
    from p2.runtime_doan import lan_oracle_local
    ok = [("lan01", "2026-11-03T12:01+07:00"), ("lan03", "2026-11-04T00:14+07:00"), ("lan04", "2026-11-04T06:00+07:00"),
          ("lan17", "2026-11-07T12:00+07:00"), ("lan18", "2026-11-07T18:00+07:00")]
    assert lan_oracle_local(ok) == ["lan01", "lan17", "lan18"]
    assert lan_oracle_local(ok, 2) == ["lan01", "lan17"]
