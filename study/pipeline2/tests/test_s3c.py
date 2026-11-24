"""Đo bù P6 (S3C), sửa đổi 1 (P6/PREREG_ADDENDUM_MD_AMEND1_20261122.md): test offline, hàm gọi giả — không lời gọi thật."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from p2 import s3, s3c  # noqa: E402
import run_s3c  # noqa: E402


def test_thu_tu_chay_ba_lan_lai_truoc_roi_vong_3_dung_thu_tu():
    goc, moi = s3c.thu_tu(), s3c.thu_tu_chay()
    assert len(moi) == len(goc) == 22 and len(set(moi)) == 22
    n12 = 1 + 2 * len(s3c.BIEN_THE)
    assert moi[n12 - 3:n12] == ["M1-2_i", "T1-2_i", "R1-B-2_i"]          # (d) ba lần chạy lại trước
    assert moi[n12:] == goc[n12:]                                        # rồi vòng 3, thứ tự xáo đã ghi
    assert [t for t in moi[:n12 - 3]] == [t for t in goc[:n12] if t not in s3c.CHAY_LAI]
    assert sorted(s3c.o_ke_hoach(t) for t in moi) == sorted(goc)         # mỗi ô kế hoạch đúng một lần


def test_ten_chay_lai_giu_bien_the_va_server():
    for o, ten in s3c.CHAY_LAI.items():
        assert s3c.goc(ten) == s3c.goc(o)
        assert s3c.runtime(ten) == s3c.runtime(o)
        a, b = s3c.bien_the(ten), s3c.bien_the(o)
        assert (a.model_local, a.temperature, a.k, a.prompt, a.stages_chay) == \
               (b.model_local, b.temperature, b.k, b.prompt, b.stages_chay)  # (e) không tham số gọi nào đổi
    assert s3c.o_ke_hoach("M1-2_i_r") == "M1-2" and s3c.o_ke_hoach("C-3_r") == "C-3" and s3c.o_ke_hoach("G") == "G"
    assert set(s3c.VO_HIEU) == {"M1-2", "M1-2_r", "T1-2", "T1-2_r", "R1-B-2"}


def _man(tmp_path, monkeypatch, dong):
    m = tmp_path / "man.jsonl"
    m.write_text("".join(json.dumps(d) + "\n" for d in dong), encoding="utf-8")
    monkeypatch.setattr(s3c, "MANIFEST", m)
    return m


def test_trang_thai_lan(tmp_path, monkeypatch):
    _man(tmp_path, monkeypatch, [
        {"run": "G", "trang_thai": "ok"},
        {"run": "M1-2", "trang_thai": "hong"}, {"run": "M1-2_r", "trang_thai": "hong"},
        {"run": "R1-B-2", "trang_thai": "hong"},
        {"run": "T1-2_i", "trang_thai": "hong"}, {"run": "T1-2_i_r", "trang_thai": "ok"},
    ])
    tt = s3c.trang_thai_lan()
    assert tt == {"G": "ok", "M1-2": "loai", "R1-B-2": "cho_r", "T1-2_i": "ok"}


def _gia(monkeypatch, tmp_path, ket_qua):
    """mot_lan giả: lần thứ i trả 40 item, lỗi ket_qua[i] item."""
    goi = []

    def mot_lan(arm, bt, qids, g, data=None):
        n_loi = ket_qua[len(goi)]
        goi.append(bt.ten)
        return [{"stage": "generate", "qid": q, "ok": j >= n_loi} for j, q in enumerate(qids)], {}

    monkeypatch.setattr(s3, "mot_lan", mot_lan)
    return goi


def test_chay_mot_hong_roi_r_roi_loai(tmp_path, monkeypatch):
    goi = _gia(monkeypatch, tmp_path, [40, 39])
    res, man = tmp_path / "r.jsonl", tmp_path / "m.jsonl"
    qids = [f"q{i}" for i in range(40)]
    assert run_s3c.chay_mot("M1-2_i", {}, qids, res, man) == "loai"
    runs = [json.loads(l)["run"] for l in man.read_text(encoding="utf-8").splitlines()]
    assert runs == ["M1-2_i", "M1-2_i_r"] and len(goi) == 2


def test_chay_mot_chi_r_khi_chay_tiep(tmp_path, monkeypatch):
    _gia(monkeypatch, tmp_path, [0])
    man = tmp_path / "m.jsonl"
    assert run_s3c.chay_mot("R1-B-2_i", {}, ["q"] * 40, tmp_path / "r.jsonl", man, chi_r=True) == "ok"
    assert [json.loads(l)["run"] for l in man.read_text(encoding="utf-8").splitlines()] == ["R1-B-2_i_r"]


def test_kiem_dia_chan_truoc_r_khong_tinh_lan_hong(tmp_path, monkeypatch):
    goi = _gia(monkeypatch, tmp_path, [40, 0])
    man = tmp_path / "m.jsonl"
    kq = run_s3c.chay_mot("T1-2_i", {}, ["q"] * 40, tmp_path / "r.jsonl", man, kiem_truoc_r=lambda t: "thiếu chỗ")
    assert kq == "dung" and len(goi) == 1                                # _r chưa chạy
    monkeypatch.setattr(s3c, "MANIFEST", man)
    assert s3c.trang_thai_lan() == {"T1-2_i": "cho_r"}                   # đêm sau chỉ chạy _r


def test_dung_con_mo_coi_chi_kill_llama_server_cua_ollama_A_B(monkeypatch, tmp_path):
    """Phụ lục A: kill llama-server dưới thư mục A hoặc zip_dir (B); không đụng llama-server khác hay tiến trình khác."""
    import psutil

    zip_dir = tmp_path / "ollama_0.40.16"
    da_kill = []

    class P:
        def __init__(self, name, exe):
            self.info = {"name": name, "exe": exe}

        def kill(self):
            da_kill.append(self.info["exe"])

    a_exe = str(s3.INSTALLED.parent / "lib" / "ollama" / "llama-server.exe")
    b_exe = str(zip_dir / "lib" / "ollama" / "llama-server.exe")
    ds = [P("llama-server.exe", a_exe), P("llama-server.exe", b_exe),
          P("llama-server.exe", r"D:\Datasets\LLM_Models\_bin\llama-server.exe"),   # llama.cpp của đề tài khác
          P("python.exe", r"C:\x\python.exe"), P("llama-server.exe", None)]
    monkeypatch.setattr(psutil, "process_iter", lambda attrs=None: iter(ds))
    monkeypatch.setattr(psutil, "wait_procs", lambda procs, timeout=None: ([], []))
    assert run_s3c.dung_con_mo_coi(zip_dir) == [a_exe, b_exe]
    assert da_kill == [a_exe, b_exe]


def test_kiem_dia_nguong(monkeypatch):
    monkeypatch.setattr(run_s3c, "d_trong_gib", lambda: 19.9)
    assert "checkpoint" in run_s3c.kiem_dia("K1-3")
    monkeypatch.setattr(run_s3c, "d_trong_gib", lambda: 20.0)
    assert run_s3c.kiem_dia("K1-3") is None


# ------------------------------------------------------------------ sửa đổi 2 (P6/PREREG_ADDENDUM_MD_AMEND2_20261124.md)
def test_cho_san_sang_thu_lai_roi_duoc(monkeypatch):
    monkeypatch.setattr(run_s3c.time, "sleep", lambda s: None)
    lan = []

    class R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"{}"

    def mo(url, timeout=None):
        lan.append((url.rsplit("/", 1)[-1], timeout))
        if len(lan) <= 2:                       # version ok, tags timeout lần đầu
            if url.endswith("tags"):
                raise TimeoutError("timed out")
        return R()

    assert run_s3c.cho_san_sang(mo=mo) is None
    assert [u for u, _ in lan] == ["version", "tags", "version", "tags"]
    assert all(t == 30.0 for _, t in lan)


def test_cho_san_sang_het_han_tra_ly_do(monkeypatch):
    t = [0.0]
    monkeypatch.setattr(run_s3c.time, "time", lambda: t[0])
    monkeypatch.setattr(run_s3c.time, "sleep", lambda s: t.__setitem__(0, t[0] + s))

    def mo(url, timeout=None):
        t[0] += timeout
        raise TimeoutError("timed out")

    ly = run_s3c.cho_san_sang(mo=mo)
    assert ly and "180" in ly and t[0] <= 180 + 30


def test_luot_han_va_su_co_thu_hai(tmp_path):
    f = tmp_path / "luot.json"
    l = run_s3c.Luot(f)
    from datetime import datetime
    han = datetime.fromisoformat(l.d["han"]) - datetime.fromisoformat(l.d["bat_dau"])
    assert han.total_seconds() == 270 * 60
    assert l.da_ket() is None
    assert l.su_co("server_chua_san_sang", "x") is None
    l2 = run_s3c.Luot(f)                                      # khởi động lại runner: giữ hạn + số sự cố
    assert l2.d["bat_dau"] == l.d["bat_dau"] and len(l2.d["su_co"]) == 1
    assert "thứ hai" in l2.su_co("lan_hong", "T1-2_i")
    assert run_s3c.Luot(f).da_ket()


def test_chay_mot_su_co_thu_hai_dung_truoc_r(tmp_path, monkeypatch):
    goi = _gia(monkeypatch, tmp_path, [40, 0])
    man = tmp_path / "m.jsonl"
    kq = run_s3c.chay_mot("M1-2_i", {}, ["q"] * 40, tmp_path / "r.jsonl", man, khi_hong=lambda t: "thứ hai")
    assert kq == "het_luot" and len(goi) == 1
    kq = run_s3c.chay_mot("M1-3", {}, ["q"] * 40, tmp_path / "r.jsonl", man, khi_hong=lambda t: None)
    assert kq == "ok"                                          # sự cố thứ nhất: _r chạy như cũ


def test_local_ngoai_le_van_dung_het(tmp_path, monkeypatch):
    import argparse
    import pytest
    da = []
    monkeypatch.setattr(run_s3c, "dung_het", lambda z: da.append(z) or [])

    def no(a, luot):
        raise TimeoutError("timed out")

    monkeypatch.setattr(run_s3c, "_local", no)
    a = argparse.Namespace(zip_dir=str(tmp_path), bo_khung_dem=True, luot=str(tmp_path / "l.json"))
    with pytest.raises(TimeoutError):
        run_s3c.local(a)
    assert da and json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))["su_co"][0]["loai"] == "ngoai_le"
