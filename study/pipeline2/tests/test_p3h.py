"""Nhánh P3H (AMENDMENT V2-06): executor gọi giả, cổng key, trần USD chung, plan. Không gọi mạng."""
import io
import json
import sys
import urllib.error
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p2 import P2_DIR, backends, executors, prompts, stages  # noqa: E402
from p2.lich_gio import RunnerTheoGio, cho_phep_ngay  # noqa: E402
from mrunner.core import RateLimited  # noqa: E402

KEY = "sk-or-khong-duoc-lo"


class _Tra:
    def __init__(self, d):
        self.b = json.dumps(d).encode()

    def __enter__(self):
        return io.BytesIO(self.b)

    def __exit__(self, *a):
        return False


def _dat(monkeypatch, tra=None, loi=None):
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    goi = []

    def urlopen(req, timeout=None):
        goi.append(req)
        if loi:
            raise loi
        return _Tra(tra)
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    return goi


TOT = {"id": "gen-1", "model": "meta-llama/llama-3.1-8b-instruct", "choices": [{"message": {"content": "ROUTE: RETRIEVE. REASON: x"},
       "finish_reason": "stop", "native_finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 30, "cost": 0.0000032}}


def test_openrouter_ghim_endpoint_tat_fallback(monkeypatch):
    goi = _dat(monkeypatch, TOT)
    r = backends.openrouter("xin chao", 0.0, seed=0)
    b = json.loads(goi[0].data)
    assert b["provider"] == {"order": ["deepinfra/fp8"], "allow_fallbacks": False, "require_parameters": True}
    assert (b["model"], b["temperature"], b["seed"], b["max_tokens"]) == ("meta-llama/llama-3.1-8b-instruct", 0.0, 0, 400)
    assert b["messages"] == [{"role": "user", "content": "xin chao"}]
    assert "noreply@example.org" in goi[0].get_header("User-agent") and goi[0].get_header("Authorization") == f"Bearer {KEY}"
    assert r["text"].startswith("ROUTE") and r["gen_id"] == "gen-1"
    assert r["usage"] == {"in_text": 100, "in_audio": 0, "out": 30, "grounded": 0, "nha": "openrouter", "cost": 0.0000032}
    assert KEY not in json.dumps({k: v for k, v in r.items()})


@pytest.mark.parametrize("sua,chu", [
    ({"error": {"code": 502, "message": "x"}}, "openrouter error"),      # lỗi trong HTTP 200
    ({"provider": "Groq"}, "provider Groq"),                             # rơi sang provider khác
    ({"usage": None}, "usage"),                                          # thiếu usage: trần USD không đếm được
    ({"choices": [{"message": {"content": "  "}, "finish_reason": "stop"}]}, "rỗng"),
])
def test_openrouter_khong_ghi_ok_khi_bat_thuong(monkeypatch, sua, chu):
    _dat(monkeypatch, {**TOT, **sua})
    with pytest.raises(RuntimeError, match=chu):
        backends.openrouter("x", 0.0)


def _http(code, hdr=None):
    return urllib.error.HTTPError("u", code, "m", hdr or {}, io.BytesIO(b'{"error":"thong bao"}'))


def test_openrouter_429_la_rate_limited(monkeypatch):
    _dat(monkeypatch, loi=_http(429, {"Retry-After": "37"}))
    with pytest.raises(RateLimited) as e:
        backends.openrouter("x", 0.0)
    assert e.value.retry_after_s == 37.0


def test_openrouter_loi_khong_lo_key(monkeypatch):
    _dat(monkeypatch, loi=_http(402))
    with pytest.raises(RuntimeError) as e:
        backends.openrouter("x", 0.0)
    assert "HTTP 402" in str(e.value) and KEY not in str(e.value)


def test_cung_prompt_voi_p3_local(monkeypatch):
    """Route và generate của P3H đi qua cùng hàm stage, cùng khuôn prompt, cùng tham số với P3 local."""
    seen = {}

    def gia(ten):
        def f(prompt, temperature, seed=0, **kw):
            seen[ten] = (prompt, temperature, seed)
            return {"text": "ROUTE: ANSWER", "usage": None}
        return f
    monkeypatch.setattr(backends, "openrouter", gia("or"))
    monkeypatch.setattr(backends, "local", gia("local"))
    q = type("Q", (), {"question": "Ai?", "gold_doc": "d0001"})()
    stages.route(q, "openrouter", 0.0, model="m", seed=0)
    stages.route(q, "local", 0.0, model="llama3.1:8b", seed=0)
    assert seen["or"] == seen["local"] == (prompts.ROUTE.format(q="Ai?"), 0.0, 0)
    t = {"params": {"qid": "q", "backend": "openrouter", "seed": 0, "temperature": 0.0}}
    assert executors.mo_ta_model(t["params"], "route")["slug"] == "deepinfra/fp8"


def test_ready_theo_key_va_han(monkeypatch):
    ex = executors.P3HExec("route", clock=lambda: datetime.fromisoformat("2026-11-08T10:00+07:00").timestamp())
    assert ex.kind == "p3h_route"
    monkeypatch.setattr(backends, "key_openrouter", lambda: None)
    assert not ex.ready({"m": "P3HS"}) and not ex.ready({"m": "P3H"})
    monkeypatch.setattr(backends, "key_openrouter", lambda: KEY)
    assert ex.ready({"m": "P3HS"}) and ex.ready({"m": "P3H"})
    tre = executors.P3HExec("route", clock=lambda: datetime.fromisoformat("2026-11-13T12:00+07:00").timestamp())
    assert not tre.ready({"m": "P3HS"})                  # quá hạn: không khởi động nhánh dù có key
    assert tre.ready({"m": "P3H"})                       # đã khởi động trước hạn thì chạy nốt


def _plan(tmp_path, budget=1.0):
    t = [{"id": "P3HS|route|openrouter|s|s01", "m": "P3HS", "kind": "p3h_route", "hosted": True, "heavy": False, "order": 5, "params": {}},
         {"id": "P2|route|hosted|q|r01", "m": "P2", "kind": "p2_route", "hosted": True, "heavy": False, "order": 3, "params": {}}]
    res = {"P2": "P2.jsonl", "P3HS": "s.jsonl", "P3H": "P3H.jsonl"}
    return {"runner_dir": "r", "results": res, "late_missed_s": 7200, "budget_usd": budget, "tasks": t,
            "price": {"in_text": 0.30, "in_audio": 1.0, "out": 2.50, "openrouter": {"in_text": 0.02, "in_audio": 0, "out": 0.04}}}


def now_ts():
    return datetime.fromisoformat("2026-11-08T10:30+07:00").timestamp()


def _gio_ngay(tmp_path, plan, ex):
    now = datetime.fromisoformat("2026-11-08T10:30+07:00").timestamp()
    return RunnerTheoGio(plan, tmp_path, ex, clock=lambda: now, gio=lambda _: 10, ram=lambda: 16.0), now


def test_khong_key_thi_bo_qua_khong_loi(tmp_path, monkeypatch):
    """Thiếu key: task P3H không được chọn, không missed, không bản ghi lỗi; task khác vẫn chạy."""
    monkeypatch.setattr(backends, "key_openrouter", lambda: None)
    plan = _plan(tmp_path)
    plan["tasks"] = plan["tasks"][:1]
    r, now = _gio_ngay(tmp_path, plan, {"p3h_route": executors.P3HExec("route", clock=now_ts)})
    t, wake, missed = r.pick(r.snapshot(), now)
    assert t is None and missed == []
    assert r.step().startswith("idle:") and not list(tmp_path.glob("*.errors.jsonl"))
    plan2 = _plan(tmp_path)
    r2, now2 = _gio_ngay(tmp_path, plan2, {"p3h_route": executors.P3HExec("route", clock=now_ts)})
    assert r2.pick(r2.snapshot(), now2)[0]["id"] == "P2|route|hosted|q|r01"


def test_co_key_thi_chay(tmp_path, monkeypatch):
    monkeypatch.setattr(backends, "key_openrouter", lambda: KEY)
    plan = _plan(tmp_path)
    plan["tasks"] = plan["tasks"][:1]
    r, now = _gio_ngay(tmp_path, plan, {"p3h_route": executors.P3HExec("route", clock=now_ts)})
    assert r.pick(r.snapshot(), now)[0]["id"].startswith("P3HS|")


def _ghi(p, u):
    p.write_text(json.dumps({"task_id": "x", "status": "ok", "ts": "2026-11-08T10:00+07:00", "usage": u}) + "\n", encoding="utf-8")


def test_tran_usd_cong_ca_openrouter(tmp_path):
    """Gemini + OpenRouter cùng vào spent_usd; chạm trần thì task hosted (cả P3H) không được chọn."""
    plan = _plan(tmp_path, budget=0.0005)
    plan["tasks"] = plan["tasks"][1:]
    plan["results"]["P3H"] = "P3H.jsonl"
    _ghi(tmp_path / "P2.jsonl", {"in_text": 1000, "in_audio": 0, "out": 0})                                      # 0,0003 USD
    _ghi(tmp_path / "P3H.jsonl", {"in_text": 1_000_000, "in_audio": 0, "out": 0, "nha": "openrouter", "cost": None})  # 0,02 USD
    r, now = _gio_ngay(tmp_path, plan, {})
    s = r.snapshot()
    assert s.openrouter_usd == pytest.approx(0.02) and s.spent_usd == pytest.approx(0.0203)
    assert r.pick(s, now)[0] is None                     # trần chạm: không chọn task hosted
    _ghi(tmp_path / "P3H.jsonl", {"in_text": 1_000_000, "in_audio": 0, "out": 0, "nha": "openrouter", "cost": 0.5})
    assert r.snapshot().openrouter_usd == pytest.approx(0.5)      # có cost thì dùng cost thật


def test_ngay_cho_phep_p3h():
    assert cho_phep_ngay({"m": "P3H", "kind": "p3h_route"}, 1.0) and cho_phep_ngay({"m": "P3HS", "kind": "p3h_route"}, 1.0)


def _nap_runner():
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_m_all_p2", P2_DIR / "scripts" / "run_m_all_p2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_plan_amendment_v2_06():
    """Plan thật: 3 smoke + 2 000 task; id smoke không thuộc mẫu; tham số khớp P3 local; task cũ trùng khít (sha256)."""
    p = P2_DIR / "runner/plan_p2.json"
    if not p.exists():
        pytest.skip("chưa sinh plan")
    plan = json.loads(p.read_text(encoding="utf-8"))
    a = plan["amendment_v2_06"]
    n = a["n_task_cu"]
    cu, moi = plan["tasks"][:n], plan["tasks"][n:]
    assert n == 19791 and _nap_runner()._bam_tasks(cu) == a["sha256_task_cu"]
    sm = [t for t in moi if t["m"] == "P3HS"]
    h = [t for t in moi if t["m"] == "P3H"]
    assert len(moi) == 2003 and moi[:3] == sm and len(h) == a["p3h_n"] == 2000 and a["n_lan"] == 5
    assert not {t["params"]["qid"] for t in sm} & set(plan["mau"]["n2_qids"]) and "after" not in sm[0]
    by = {t["id"]: t for t in plan["tasks"]}
    for t in h:
        _, stage, _, qid, rk = t["id"].split("|")
        g = by[f"P3|{stage}|local|{qid}|{rk}"]
        assert t["hosted"] and not t["heavy"] and t["kind"] == f"p3h_{stage}"
        assert (t["params"]["qid"], t["params"]["temperature"], t["params"]["seed"]) == (qid, g["params"]["temperature"], g["params"]["seed"])
        assert t["after"]["delta_s"] == (0 if rk == "r01" else 21600)
        if rk == "r01":
            assert t["after"]["task"] == sm[-1]["id"]
    assert plan["price"]["openrouter"]["in_text"] == 0.02 and plan["budget_usd"] == 4.4704
    assert plan["results"]["P3HS"].endswith("smoke_openrouter_20261107.jsonl")


def test_amend_v2_06_tu_choi_hai_lan_va_sai_thu_tu():
    m = _nap_runner()
    with pytest.raises(ValueError):
        m.amend_v2_06({"tasks": [], "results": {}, "price": {}, "mau": {}})
    with pytest.raises(ValueError):
        m.amend_v2_06({"amendment_v2_06": {}, "amendment_v2_07": {}})
