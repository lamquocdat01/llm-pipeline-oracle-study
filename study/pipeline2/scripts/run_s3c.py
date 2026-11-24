r"""Chạy đo bù P6 (R2-02) — kế hoạch `P6/PREREG_ADDENDUM_MD_20261121.md` (a).

    python scripts\run_s3c.py plan                    # in thứ tự 22 lần (sau sửa đổi 1), không gọi gì
    python scripts\run_s3c.py local [--zip-dir D]     # chờ khung đêm (lich_gio.la_dem), chạy tiếp từ checkpoint, dừng trước 08:00
    python scripts\run_s3c.py smoke [--zip-dir D]     # 2 câu, prompt gốc, server A rồi server B: chỉ kiểm đường chạy + ghim;
                                                      # ghi results/S3C_SMOKE_<ngày>.jsonl, loại khỏi mẫu
    python scripts\run_s3c.py status

Mỗi lần: dừng mọi ollama → khởi động đúng phiên bản → kiểm /api/version + ghim → chạy 40 câu generate. Từ chối khi lệch.
Sửa đổi 1 (P6/PREREG_ADDENDUM_MD_AMEND1_20261122.md): thứ tự `s3c.thu_tu_chay()` (M1-2_i, T1-2_i, R1-B-2_i rồi vòng 3);
trước MỖI lần (kể cả _r) ổ chứa kết quả trống ≥ 20 GiB, thiếu ⇒ dừng mã 6 (checkpoint, không tính là lần hỏng);
lần đầu hỏng mà _r chưa chạy (bị dừng giữa chừng) ⇒ lần sau chỉ chạy _r; hỏng cả hai ⇒ loại, không chạy lại.
Sửa đổi 2 (P6/PREREG_ADDENDUM_MD_AMEND2_20261124.md): `local --bo-khung-dem` bỏ chờ khung đêm, thay hạn 08:00 bằng hạn
lượt (bắt đầu + 4 h 30, ghi ở `results/S3C_LUOT_*.json`); chờ server sẵn sàng (/api/version + /api/tags ≤ 180 s, mỗi lần
thử timeout 30 s; không được ⇒ mã 7, checkpoint); thoát vì ngoại lệ vẫn `dung_het`; ghi CPU % + RAM trống trước mỗi lần;
sự cố hạ tầng thứ hai trong lượt hoặc quá hạn ⇒ kết thúc lượt (mã 8), không chạy lại nữa.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from p2 import s3, s3b, s3c  # noqa: E402
from p2.lich_gio import la_dem  # noqa: E402

ZIP_DIR_MAC_DINH = Path(r"C:\Users\Admin\AppData\Local\Temp\claude\832de303e2f15407\a0dae9c7-1dd4-4d86-98dc-61ee9890fc8a\scratchpad\ollama_0.40.16")
RAM_TOI_THIEU_GB = 6.0


def smoke_file() -> Path:
    return HERE / "results" / f"S3C_SMOKE_{datetime.now():%Y%m%d}.jsonl"


def in_(msg: str) -> None:
    print(f"[{s3.bay_gio()}] {msg}", flush=True)


def ram_trong_gb() -> float:
    import psutil
    return psutil.virtual_memory().available / 2 ** 30


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def d_trong_gib() -> float:
    return shutil.disk_usage(s3c.RESULT.anchor).free / 2 ** 30


def kiem_dia(ten: str) -> str | None:
    """(c) sửa đổi 1: trả lý do dừng nếu ổ chứa kết quả trống < D_TOI_THIEU_GIB; None nếu đủ."""
    x = d_trong_gib()
    if x < s3c.D_TOI_THIEU_GIB:
        return (f"dừng trước {ten}: ổ {s3c.RESULT.anchor} trống {x:.1f} GiB < {s3c.D_TOI_THIEU_GIB:.0f} "
                f"(checkpoint, không tính là lần hỏng)")
    return None


def exe_cho(ten: str, zip_dir: Path) -> Path:
    return zip_dir / "ollama.exe" if s3c.runtime(ten) == s3.OLLAMA_B else s3.INSTALLED


def dung_con_mo_coi(zip_dir: Path) -> list[str]:
    """Phụ lục A sửa đổi 1: `s3.dung_ollama` chỉ kill tên bắt đầu bằng 'ollama'; tiến trình con `llama-server*.exe` của
    server A/B sống mồ côi sau khi cha bị kill, mỗi cái giữ ~2,2 GB (3b) / ~5 GB (7b) commit ⇒ pagefile trên D nở
    (P6/INCIDENT_S3C_20261122.md). Kill thêm đúng các llama-server nằm dưới thư mục Ollama A hoặc `zip_dir` (B)."""
    import psutil
    goc = [str(s3.INSTALLED.parent).lower(), str(Path(zip_dir)).lower()]
    da = []
    for p in psutil.process_iter(["name", "exe"]):
        ten = (p.info["name"] or "").lower()
        exe = (p.info["exe"] or "").lower()
        if ten.startswith("llama-server") and any(exe.startswith(g) for g in goc):
            try:
                p.kill()
                da.append(p.info["exe"])
            except Exception:
                pass
    if da:
        psutil.wait_procs([q for q in psutil.process_iter(["name"]) if (q.info["name"] or "").lower().startswith("llama-server")],
                          timeout=10)
    return da


def dung_het(zip_dir: Path) -> list[str]:
    return s3.dung_ollama() + dung_con_mo_coi(zip_dir)


CHO_SAN_SANG_S = 180.0      # sửa đổi 2 (b)
TIMEOUT_THU_S = 30.0
PHUT_LUOT = 270             # sửa đổi 2 (e)(ii): 4 h 30


def cho_san_sang(han_s: float = CHO_SAN_SANG_S, to: float = TIMEOUT_THU_S, mo=None) -> str | None:
    """(b) sửa đổi 2: thử /api/version rồi /api/tags tới khi cả hai trả lời, tối đa han_s; None nếu sẵn sàng."""
    import urllib.request
    from mrunner.thuc import OLLAMA
    mo = mo or urllib.request.urlopen
    t0, cuoi = time.time(), "chưa thử"
    while True:
        try:
            for duong in ("/api/version", "/api/tags"):
                with mo(OLLAMA + duong, timeout=to) as r:
                    r.read()
            return None
        except Exception as e:  # noqa: BLE001
            cuoi = f"{type(e).__name__}: {e}"
        if time.time() - t0 + 5 >= han_s:
            return f"server chưa sẵn sàng sau {han_s:.0f} s ({cuoi})"
        time.sleep(5)


def tai_may() -> dict:
    """(d) sửa đổi 2: CPU % (trung bình 3 s) và RAM trống trước mỗi lần."""
    import psutil
    return {"cpu_pct_truoc": psutil.cpu_percent(interval=3), "ram_trong_gb_truoc": round(ram_trong_gb(), 2)}


def khoi_dong(ten: str, zip_dir: Path) -> dict:
    exe = exe_cho(ten, zip_dir)
    ky_vong = s3c.runtime(ten)
    da = dung_het(zip_dir)
    tai = tai_may()
    v = s3.bat_ollama(exe)
    loi = []
    san_sang = cho_san_sang() if v is not None else "server không trả /api/version sau 90 s"
    if san_sang:
        in_(f"khởi động {exe}: {san_sang}")
        return {"api_version": v, "ky_vong": ky_vong, "exe": str(exe), "da_dung": da, "ghim_loi": [],
                "chua_san_sang": san_sang, **tai}
    if v != ky_vong:
        loi.append(f"/api/version {v} ≠ {ky_vong}")
    bt = s3c.bien_the(ten)
    for m in sorted({"qwen2.5:3b", bt.model_local}):
        loi += s3.kiem_ghim(m)
    meta = {"api_version": v, "ky_vong": ky_vong, "exe": str(exe), "exe_sha256": sha_file(exe),
            "cli_version": s3.cli_version(exe), "da_dung": da, "ghim_loi": loi,
            "digest": s3.PIN_S3[bt.model_local]["manifest_digest"],
            "weights_sha256": s3.PIN_S3[bt.model_local]["weights_sha256"], "ram_trong_gb": round(ram_trong_gb(), 2),
            **tai}
    in_(f"khởi động {exe} → {v}; ghim {loi or 'khớp'}; CPU {tai['cpu_pct_truoc']} %, RAM trống {tai['ram_trong_gb_truoc']} GB")
    return meta


def chay_mot(ten: str, meta: dict, qids: list[str], result: Path, manifest: Path | None,
             chi_r: bool = False, kiem_truoc_r=None, khi_hong=None) -> str:
    """'ok' | 'loai' (hỏng cả lần đầu và _r) | 'dung' (kiem_truoc_r chặn trước _r — checkpoint, chưa tính _r)
    | 'het_luot' (sửa đổi 2 (e)(iii): khi_hong(tên) trả lý do — sự cố hạ tầng thứ hai trong lượt, dừng ngay)."""
    bt = s3c.bien_the(ten)
    for ten_ghi in ((ten + "_r",) if chi_r else (ten, ten + "_r")):
        if ten_ghi.endswith("_r") and kiem_truoc_r is not None:
            ly_do = kiem_truoc_r(ten_ghi)
            if ly_do:
                in_(ly_do)
                return "dung"
        t0 = s3.bay_gio()
        items, _ = s3.mot_lan("local", bt, qids, s3.Goi())
        for it in items:
            s3.ghi(result, {"arm": "local", "run": ten_ghi, "bien_the": s3c.goc(ten), **it})
        hong = s3.hong(items)
        if manifest is not None:
            s3.ghi(manifest, {"arm": "local", "run": ten_ghi, "bien_the": s3c.goc(ten), "ts": t0, "ts_end": s3.bay_gio(),
                              "trang_thai": "hong" if hong else "ok", "n_item": len(items),
                              "n_loi": sum(1 for i in items if not i["ok"]), "model": bt.model_local,
                              "temperature": bt.temperature, "k": bt.k, "stages": list(bt.stages_chay),
                              "prompt_sha256": {st: s3.sha(bt.prompt[st]) for st in bt.stages_chay}, **meta})
        in_(f"{ten_ghi}: {len(items)} item, lỗi {sum(1 for i in items if not i['ok'])}, {'HỎNG' if hong else 'ok'}")
        if not hong:
            return "ok"
        if khi_hong is not None:
            ly_do = khi_hong(ten_ghi)
            if ly_do:
                in_(ly_do)
                return "het_luot"
    return "loai"


def han_08() -> datetime:
    n = datetime.now()
    h = n.replace(hour=8, minute=0, second=0, microsecond=0)
    return h if n.hour < 8 else h + timedelta(days=1)


class Luot:
    """Sửa đổi 2 (e): một lượt chạy ngoài khung đêm — hạn = bắt đầu + 4 h 30, đếm sự cố hạ tầng; lưu ở file JSON để
    khởi động lại runner trong cùng lượt vẫn giữ hạn và số sự cố. Sự cố thứ hai hoặc quá hạn ⇒ lượt kết thúc."""

    def __init__(self, path: Path, phut: int = PHUT_LUOT):
        self.path = path
        if path.exists():
            self.d = json.loads(path.read_text(encoding="utf-8"))
        else:
            bd = datetime.now().astimezone()
            self.d = {"bat_dau": bd.isoformat(timespec="seconds"),
                      "han": (bd + timedelta(minutes=phut)).isoformat(timespec="seconds"), "su_co": [], "ket_thuc": None}
            self.luu()

    def luu(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    @property
    def han(self) -> datetime:
        return datetime.fromisoformat(self.d["han"]).replace(tzinfo=None)

    def su_co(self, loai: str, chi_tiet: str) -> str | None:
        """Ghi một sự cố hạ tầng; trả lý do kết thúc lượt nếu đây là sự cố thứ hai."""
        self.d["su_co"].append({"ts": s3.bay_gio(), "loai": loai, "chi_tiet": chi_tiet})
        self.luu()
        if len(self.d["su_co"]) >= 2:
            return self.ket(f"sự cố hạ tầng thứ hai trong lượt ({loai}: {chi_tiet}) — kết thúc lượt, không chạy thêm")
        return None

    def ket(self, ly_do: str) -> str:
        if not self.d.get("ket_thuc"):
            self.d["ket_thuc"] = {"ts": s3.bay_gio(), "ly_do": ly_do}
            self.luu()
        return ly_do

    def da_ket(self) -> str | None:
        if self.d.get("ket_thuc"):
            return self.d["ket_thuc"]["ly_do"]
        if datetime.now() >= self.han:
            return self.ket(f"quá hạn lượt {self.d['han']}")
        return None


def luot_file() -> Path:
    return HERE / "results" / f"S3C_LUOT_{datetime.now():%Y%m%d}.json"


def local(a) -> int:
    luot = Luot(Path(a.luot) if a.luot else luot_file()) if a.bo_khung_dem else None
    try:
        return _local(a, luot)
    except BaseException as e:
        # (c) sửa đổi 2: thoát vì lỗi vẫn dừng ollama serve / llama-server
        try:
            dung_het(Path(a.zip_dir))
        finally:
            if luot is not None and not isinstance(e, KeyboardInterrupt):
                luot.su_co("ngoai_le", f"{type(e).__name__}: {e}")
        raise


def _local(a, luot: Luot | None) -> int:
    zip_dir = Path(a.zip_dir)
    if s3c.su_co_truoc():
        in_("DỪNG: manifest có sự cố từ trước — chờ anh xem (kế hoạch (a))")
        return 5
    if luot is None:
        while not la_dem(datetime.now().hour):
            time.sleep(60)
        in_("bắt đầu đo bù P6 (khung đêm)")
        han, ten_han = han_08(), "08:00"
    else:
        ly = luot.da_ket()
        if ly:
            in_(f"lượt đã kết thúc: {ly}")
            return 8
        in_(f"bắt đầu đo bù P6 NGOÀI khung đêm (sửa đổi 2), lượt {luot.d['bat_dau']} → hạn {luot.d['han']}, "
            f"sự cố đã có {len(luot.d['su_co'])}")
        han, ten_han = luot.han, f"hạn lượt {luot.d['han']}"

    def su_co(loai: str, chi_tiet: str, rc: int) -> int:
        dung_het(zip_dir)
        if luot is not None and luot.su_co(loai, chi_tiet):
            in_(luot.d["ket_thuc"]["ly_do"])
            return 8
        return rc

    xong = s3c.trang_thai_lan()
    qids = s3b.oracle_qids()
    for ten in s3c.thu_tu_chay():
        tt = xong.get(ten)
        if tt in ("ok", "loai"):
            continue
        if datetime.now() + timedelta(minutes=s3c.phut_uoc(ten)) > han:
            in_(f"dừng trước {ten}: không đủ giờ trước {ten_han}"
                + (" — đêm sau chạy tiếp từ checkpoint" if luot is None else " — kết thúc lượt (sửa đổi 2 (e)(ii))"))
            dung_het(zip_dir)
            if luot is not None:
                luot.ket(f"không đủ giờ cho {ten} trước {ten_han}")
                return 8
            return 0
        cho = 0
        while ram_trong_gb() < RAM_TOI_THIEU_GB and cho < 30:
            time.sleep(60)
            cho += 1
        if ram_trong_gb() < RAM_TOI_THIEU_GB:
            in_(f"dừng trước {ten}: RAM trống {ram_trong_gb():.1f} GB < {RAM_TOI_THIEU_GB} (checkpoint)")
            return su_co("ram", f"trước {ten}: {ram_trong_gb():.1f} GB", 3)
        ly_do = kiem_dia(ten)
        if ly_do:
            in_(ly_do)
            return su_co("dia", ly_do, 6)
        meta = khoi_dong(ten, zip_dir)
        if meta.get("chua_san_sang"):
            in_(f"dừng trước {ten}: {meta['chua_san_sang']} (sửa đổi 2 (b): checkpoint, không tính là lần hỏng)")
            return su_co("server_chua_san_sang", f"trước {ten}: {meta['chua_san_sang']}", 7)
        if meta["ghim_loi"]:
            s3.ghi(s3c.MANIFEST, {"arm": "local", "run": ten, "trang_thai": "su_co", "ts": s3.bay_gio(), **meta})
            in_("SỰ CỐ: phiên bản/ghim lệch — DỪNG toàn bộ (kế hoạch (a))")
            dung_het(zip_dir)
            return 5
        khi_hong = (lambda t: luot.su_co("lan_hong", t)) if luot is not None else None
        kq = chay_mot(ten, meta, qids, s3c.RESULT, s3c.MANIFEST, chi_r=(tt == "cho_r"), kiem_truoc_r=kiem_dia,
                      khi_hong=khi_hong)
        if kq == "dung":
            return su_co("dia", f"trước {ten}_r", 6)
        if kq == "het_luot":
            dung_het(zip_dir)
            return 8
        if kq == "loai":
            in_(f"{ten} hỏng hai lần — loại, báo")
    dung_het(zip_dir)
    if luot is not None:
        luot.ket("xong mọi lần theo thứ tự")
    in_("đo bù P6 xong 22 lần")
    return 0


def smoke(a) -> int:
    """Không thuộc mẫu: 2 câu đầu, prompt gốc, server A (C-0) rồi server B (R1-B-0); ghi file SMOKE riêng."""
    f = smoke_file()
    rc = 0
    for ten in ("C-0", "R1-B-0"):
        meta = khoi_dong(ten, Path(a.zip_dir))
        if meta.get("chua_san_sang") or meta["ghim_loi"] or meta["api_version"] != meta["ky_vong"]:
            in_(f"smoke {ten}: phiên bản {meta['api_version']} (kỳ vọng {meta['ky_vong']}), ghim {meta['ghim_loi']}")
            dung_het(Path(a.zip_dir))
            return 5
        t = time.time()
        ok = chay_mot(ten, meta, s3b.oracle_qids()[:2], f, None) == "ok"
        in_(f"smoke {ten} ({meta['api_version']}, exe {meta['exe_sha256'][:12]}…) {'ok' if ok else 'HỎNG'} "
            f"trong {time.time() - t:.0f} s → {f.name}")
        rc = rc or (0 if ok else 1)
    dung_het(Path(a.zip_dir))
    return rc


def plan(a) -> int:
    for i, t in enumerate(s3c.thu_tu_chay()):
        print(i, t, s3c.runtime(t), s3c.bien_the(t).model_local, s3c.bien_the(t).temperature, s3c.bien_the(t).k)
    return 0


def status(a) -> int:
    tt = s3c.trang_thai_lan()
    ds = s3c.thu_tu_chay()
    print(f"xong {sum(tt.get(t) == 'ok' for t in ds)}/{len(ds)}; loại {[t for t in ds if tt.get(t) == 'loai']}; "
          f"còn: {[t + (' (chỉ _r)' if tt.get(t) == 'cho_r' else '') for t in ds if tt.get(t) not in ('ok', 'loai')]}")
    print(f"ổ {s3c.RESULT.anchor} trống {d_trong_gib():.1f} GiB (ngưỡng {s3c.D_TOI_THIEU_GIB:.0f})")
    for f in sorted((HERE / "results").glob("S3C_LUOT_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        print(f"lượt {f.name}: {d['bat_dau']} → hạn {d['han']}; sự cố {len(d['su_co'])}; kết thúc {d.get('ket_thuc')}")
    if s3c.MANIFEST.exists():
        for l in s3c.MANIFEST.read_text(encoding="utf-8").splitlines():
            m = json.loads(l)
            print(m["run"], m.get("trang_thai"), m.get("ts"), m.get("ts_end"), m.get("n_loi"), m.get("api_version"),
                  "VÔ HIỆU (sửa đổi 1 (a))" if m["run"] in s3c.VO_HIEU else "")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("lenh", choices=["plan", "local", "smoke", "status"])
    ap.add_argument("--zip-dir", default=str(ZIP_DIR_MAC_DINH))
    ap.add_argument("--bo-khung-dem", action="store_true",
                    help="sửa đổi 2 (a): chạy ngay, hạn = bắt đầu lượt + 4 h 30 (results/S3C_LUOT_<ngày>.json)")
    ap.add_argument("--luot", default=None, help="file trạng thái lượt (mặc định results/S3C_LUOT_<ngày>.json)")
    a = ap.parse_args()
    return {"plan": plan, "local": local, "smoke": smoke, "status": status}[a.lenh](a)


if __name__ == "__main__":
    raise SystemExit(main())
