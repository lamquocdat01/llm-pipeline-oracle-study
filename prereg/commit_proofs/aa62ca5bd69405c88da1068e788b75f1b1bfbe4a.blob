"""Lịch chọn task theo giờ (p2/lich_gio.py, 03-11-2026): đêm ưu tiên P3/MD3; ngày chỉ oracle + P2 hosted/retrieve,
P3 khi RAM ≥ 8 GB. Không gọi model; plan giả trong tmp_path."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p2.lich_gio import RunnerTheoGio, cho_phep_ngay, la_dem  # noqa: E402

TZ = timezone(timedelta(hours=7))


def _plan(tmp_path, them=()):
    t = [
        {"id": "P2|route|hosted|q|r05", "m": "P2", "kind": "p2_route", "hosted": True, "order": 3},
        {"id": "P2|retrieve|bm25|q|r05", "m": "P2", "kind": "p2_retrieve", "hosted": False, "order": 1},
        {"id": "P2|generate|local|q|r05", "m": "P2", "kind": "p2_generate", "hosted": False, "heavy": True, "order": 0},
        {"id": "P3|generate|local|q|r05", "m": "P3", "kind": "p2_generate", "hosted": False, "heavy": True, "order": 5},
        {"id": "MD3|M2|x|t0", "m": "MD3", "kind": "m2_local", "hosted": False, "heavy": True, "order": 6},
        *them,
    ]
    res = {m: str(tmp_path / f"{m}.jsonl") for m in ("P2", "P2O", "P3", "MD3")}
    return {"runner_dir": "r", "results": res, "late_missed_s": 7200, "budget_usd": 1.0,
            "price": {"in_text": 0, "in_audio": 0, "out": 0}, "tasks": t}


def _r(tmp_path, gio, ram=16.0, them=()):
    plan = _plan(tmp_path, them)
    now = datetime(2026, 11, 4, gio, 30, tzinfo=TZ).timestamp()
    r = RunnerTheoGio(plan, tmp_path, {}, clock=lambda: now, gio=lambda _n: gio, ram=lambda: ram)
    return r, now


def _chon(r, now):
    t, _, missed = r.pick(r.snapshot(), now)
    return t["id"] if t else None, missed


def test_la_dem():
    assert [g for g in range(24) if la_dem(g)] == [0, 1, 2, 3, 4, 5, 6, 7, 23]


def test_dem_uu_tien_p3_md3(tmp_path):
    r, now = _r(tmp_path, 2)
    assert _chon(r, now)[0] == "P3|generate|local|q|r05"       # order P2 local = 0 vẫn đứng sau P3
    assert r.tasks is r._tat_ca and len(r.tasks) == 5             # khôi phục danh sách sau lượt lọc


def test_dem_het_p3_md3_thi_chay_p2(tmp_path):
    r, now = _r(tmp_path, 23)
    r._tat_ca = r.tasks = [t for t in r.tasks if t["m"] == "P2"]
    assert _chon(r, now)[0] == "P2|generate|local|q|r05"


def test_ngay_khong_chay_local_tru_retrieve(tmp_path):
    r, now = _r(tmp_path, 10, ram=7.9)
    assert _chon(r, now)[0] == "P2|retrieve|bm25|q|r05"
    chon = {t["id"] for t in r.tasks if cho_phep_ngay(t, 7.9)}
    assert chon == {"P2|route|hosted|q|r05", "P2|retrieve|bm25|q|r05"}
    assert "P3|generate|local|q|r05" in {t["id"] for t in r.tasks if cho_phep_ngay(t, 8.0)}
    assert not any(t["m"] == "MD3" for t in r.tasks if cho_phep_ngay(t, 32.0))


def test_md3r_dem_truoc_p3_ngay_khong_chay(tmp_path):
    """V2-07(d): t0 của MD3R đi trước P3 ban đêm dù P3 có `after`; ban ngày không chạy ở bất kỳ mức RAM nào."""
    m = {"id": "MD3R|M2|x|t0", "m": "MD3R", "kind": "m2_local", "hosted": False, "heavy": True, "order": 6}
    r, now = _r(tmp_path, 2, them=[m])
    p3 = next(t for t in r.tasks if t["m"] == "P3")
    p3["after"] = {"task": "MD3|M2|x|t0", "delta_s": 0}      # có `after` nên core xếp nhóm g1, trước g2
    r.snapshot = lambda: type("S", (), {"done": {"MD3|M2|x|t0": {"status": "ok", "ts": "2026-11-01T00:00+07:00"}}, "errors": {},
                                        "spent_usd": 0.0, "hosted_cooldown_until": 0.0})()
    assert _chon(r, now)[0] == "MD3R|M2|x|t0"
    assert not cho_phep_ngay(m, 32.0)
    r2, now2 = _r(tmp_path, 10, ram=32.0, them=[m])
    assert _chon(r2, now2)[0] != "MD3R|M2|x|t0"


def test_oracle_dung_moc_va_missed_ca_ngay_lan_dem(tmp_path):
    o = {"id": "P2O|lan01", "m": "P2O", "kind": "p2_oracle", "hosted": True, "heavy": True, "order": 0,
         "cho_pause": True}
    for gio in (2, 14):
        (tmp_path / str(gio)).mkdir()
        r, now = _r(tmp_path / str(gio), gio, ram=4.0)
        at = datetime.fromtimestamp(now, TZ).replace(minute=0)
        r._tat_ca = r.tasks = r.tasks + [{**o, "at": at.isoformat(timespec="minutes")}]
        r.by_id = {t["id"]: t for t in r.tasks}
        assert _chon(r, now)[0] == "P2O|lan01"                     # g0 (mốc tuyệt đối) đi trước
        tre = now + 7201 + 1800
        _, missed = _chon(r, tre)
        assert [m["id"] for m in missed] == ["P2O|lan01"]
