r"""Chạy đợt đo bù V2-09 (AMENDMENT V2-09).

    python scripts\run_s3b.py hosted              # MC-goc, MC-P1p, golden, C1–C3, P1p — chạy ngay
    python scripts\run_s3b.py local [--zip-dir D] # chờ 23:00; MC; khởi động lại A; G′ C′ P1′; nạp 7b; D1–D3; R1 lặp
    python scripts\run_s3b.py status

Ghi `results/S3B_20261113_v1.jsonl` (+ manifest), chỉ append. Không đụng file nghiên cứu 2 / 3.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from p2 import s3, s3b  # noqa: E402
from p2.lich_gio import la_dem  # noqa: E402

ZIP_DIR_MAC_DINH = Path(__import__("os").environ.get("OLLAMA_B_DIR", "ollama_0.40.16"))
PHUT_MOI_LAN = 20


def in_(msg: str) -> None:
    print(f"[{s3.bay_gio()}] {msg}", flush=True)


def chay_mot(arm: str, ten: str, meta: dict, goi: s3.Goi | None = None) -> bool:
    goi = goi or s3.Goi()
    q = s3b.qids_cho(ten)
    for ten_ghi in (ten, ten + "_r"):
        bt = s3b.bien_the(ten)
        t0 = s3.bay_gio()
        items, usage = s3.mot_lan(arm, bt, q, goi)
        model = bt.model_hosted if arm == "hosted" else bt.model_local
        usd = s3.usd(model, usage) if arm == "hosted" else 0.0
        for it in items:
            s3.ghi(s3b.RESULT, {"arm": arm, "run": ten_ghi, "bien_the": ten, **it})
        hong = s3.hong(items)
        s3.ghi(s3b.MANIFEST, {"arm": arm, "run": ten_ghi, "bien_the": ten, "ts": t0, "ts_end": s3.bay_gio(),
                              "trang_thai": "hong" if hong else "ok", "n_item": len(items),
                              "n_loi": sum(1 for i in items if not i["ok"]), "model": model,
                              "temperature": bt.temperature, "k": bt.k, "stages": list(bt.stages_chay),
                              "qids": "mc" if ten.startswith("MC-") else "oracle",
                              "prompt_sha256": s3b.sha_prompts(bt), "usage": usage, "usd": round(usd, 6), **meta})
        in_(f"{arm} {ten_ghi}: {len(items)} item, lỗi {sum(1 for i in items if not i['ok'])}, "
            f"{'HỎNG' if hong else 'ok'}, USD {usd:.4f}")
        if not hong:
            return True
    return False


def hosted(a) -> int:
    xong = s3b.da_co()
    for ten in s3b.HOSTED:
        if ("hosted", ten) in xong or ("hosted", ten + "_r") in xong:
            continue
        if s3b.tien() + s3b.DU_PHONG_USD > s3b.TRAN_USD:
            in_(f"DỪNG: trần USD V2-09 ({s3b.tien():.4f} + {s3b.DU_PHONG_USD} > {s3b.TRAN_USD})")
            return 2
        if not chay_mot("hosted", ten, {"nhanh": "hosted"}):
            in_(f"{ten} hỏng hai lần — loại, báo")
    in_(f"hosted xong; USD V2-09 = {s3b.tien():.4f}")
    return 0


def meta_local(ky_vong: str, exe: Path) -> dict:
    v_api = s3.api_version()
    loi = s3.kiem_ghim("qwen2.5:3b")
    if v_api != ky_vong:
        loi.append(f"/api/version {v_api} ≠ {ky_vong}")
    return {"nhanh": "local", "api_version": v_api, "cli_version": s3.cli_version(exe), "exe": str(exe),
            "ghim_loi": loi, "digest": s3.PIN_S3["qwen2.5:3b"]["manifest_digest"],
            "weights_sha256": s3.PIN_S3["qwen2.5:3b"]["weights_sha256"]}


def khoi_dong(exe: Path, ky_vong: str) -> dict:
    da = s3.dung_ollama()
    v = s3.bat_ollama(exe)
    m = meta_local(ky_vong, exe)
    m["da_dung"] = da
    in_(f"khởi động {exe.name} → {v}; ghim {m['ghim_loi'] or 'khớp'}")
    return m


def han_08() -> datetime:
    n = datetime.now()
    h = n.replace(hour=8, minute=0, second=0, microsecond=0)
    return h if n.hour < 8 else h + timedelta(days=1)


def du_gio(han: datetime, so_lan: int = 1) -> bool:
    return datetime.now() + timedelta(minutes=PHUT_MOI_LAN * so_lan) <= han


def su_co(meta: dict) -> int:
    in_("SỰ CỐ: không về được 0.30.10 hoặc ghim lệch — DỪNG mọi việc local (V2-09 (c))")
    s3.ghi(s3b.MANIFEST, {"arm": "local", "run": "R1-SU-CO", "trang_thai": "su_co", "ts": s3.bay_gio(), **meta})
    return 5


def local(a) -> int:
    while not la_dem(datetime.now().hour):
        time.sleep(60)
    in_("bắt đầu đợt đo bù local V2-09 (khung đêm)")
    han = han_08()
    xong = s3b.da_co()
    A, Bexe = s3.INSTALLED, Path(a.zip_dir) / "ollama.exe"

    def chay_ds(ds: list[str], meta: dict) -> bool:
        for ten in ds:
            if ("local", ten) in xong or ("local", ten + "_r") in xong:
                continue
            if not du_gio(han):
                in_(f"bỏ {ten}: không đủ giờ trước 08:00 (V2-09 (d))")
                return False
            chay_mot("local", ten, meta)
        return True

    # 1–2: MC trên server A mới khởi động
    m = khoi_dong(A, s3.OLLAMA_A)
    if m["ghim_loi"]:
        return su_co(m)
    if not chay_ds(s3b.LOCAL_MC, m):
        return 0
    # 3–4: khởi động lại A; G′, C1′–C3′ liền nhau, P1′
    m = khoi_dong(A, s3.OLLAMA_A)
    if m["ghim_loi"]:
        return su_co(m)
    if not chay_ds(s3b.LOCAL_KHOI_A, m):
        return 0
    # 5: nạp 7b (một lời gọi, không ghi dữ liệu), rồi D1–D3 trên 3b
    if not all(("local", d) in xong for d in s3b.LOCAL_D):
        try:
            r = s3.local_goi("Reply OK.", s3.M1_LOCAL, 0.0)
            s3.ghi(s3b.MANIFEST, {"arm": "local", "run": "NAP-7B", "trang_thai": "su_kien", "ts": s3.bay_gio(),
                                  "model": s3.M1_LOCAL, "tra_loi": (r.get("text") or "")[:40]})
            in_("đã nạp qwen2.5:7b (một lời gọi)")
        except Exception as e:  # noqa: BLE001
            in_(f"nạp 7b lỗi: {e} — vẫn chạy D, ghi lại")
            s3.ghi(s3b.MANIFEST, {"arm": "local", "run": "NAP-7B", "trang_thai": "loi", "ts": s3.bay_gio(),
                                  "err": str(e)[:200]})
        m = meta_local(s3.OLLAMA_A, A)
        if m["ghim_loi"]:
            return su_co(m)
        if not chay_ds(s3b.LOCAL_D, m):
            return 0
    # 6: R1 lặp, từng cặp B/A; không chạy B mà thiếu A
    if not Bexe.exists():
        in_(f"DỪNG R1: không có {Bexe}")
        return 4
    for b, a_ in zip(s3b.LOCAL_R1[0::2], s3b.LOCAL_R1[1::2]):
        if ("local", a_) in xong:
            continue
        if not du_gio(han, 2):
            in_(f"bỏ cặp {b}/{a_}: không đủ giờ (V2-09 (d))")
            break
        mb = khoi_dong(Bexe, s3.OLLAMA_B)
        if mb["api_version"] == s3.OLLAMA_B and not mb["ghim_loi"]:
            chay_mot("local", b, mb)
        else:
            in_(f"{b} không chạy: phiên bản hoặc ghim lệch")
        ma = khoi_dong(A, s3.OLLAMA_A)
        if ma["ghim_loi"]:
            return su_co(ma)
        chay_mot("local", a_, ma)
    in_("đợt đo bù local xong")
    return 0


def status(a) -> int:
    if not s3b.MANIFEST.exists():
        print("chưa có lần nào")
        return 0
    for l in s3b.MANIFEST.read_text(encoding="utf-8").splitlines():
        m = json.loads(l)
        print(m["arm"], m["run"], m.get("trang_thai"), m.get("ts"), m.get("ts_end"), m.get("n_loi"), m.get("usd"),
              m.get("api_version"))
    print(f"USD V2-09: {s3b.tien():.4f}")
    return 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("lenh", choices=["hosted", "local", "status"])
    ap.add_argument("--zip-dir", default=str(ZIP_DIR_MAC_DINH))
    a = ap.parse_args()
    return {"hosted": hosted, "local": local, "status": status}[a.lenh](a)


if __name__ == "__main__":
    raise SystemExit(main())
