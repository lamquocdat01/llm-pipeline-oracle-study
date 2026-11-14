"""Chặn bench/probe có grounding trong cửa sổ M3 (AMENDMENT 02, điều kiện 1b của chủ nhân).

Hạn grounding miễn phí 1 500 lượt/ngày dùng chung cho cả key. Một bench khác chạy giữa
tuần là lượt mà runner KHÔNG đếm — và số "chưa chạm 1 500" trong bản ghi M3 thành sai mà
không ai biết. Ghi vào prereg là lời hứa; hàm này là cơ chế. Vượt rào có chủ ý:
`MICRODUCK_CHO_GROUNDING=1` (và ghi lý do vào prereg).

App desktop KHÔNG bị chặn — chủ nhân dùng nó hằng ngày; prereg ghi nó là threat.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

PLAN = Path(__file__).resolve().parents[2] / "docs" / "benchmark" / "runner" / "plan.json"


def trong_cua_so_m3(now: datetime | None = None, plan_path: Path = PLAN) -> tuple[bool, str]:
    if not plan_path.exists():
        return False, ""
    lich = json.loads(plan_path.read_text(encoding="utf-8")).get("m3_lich") or []
    if not lich:
        return False, ""
    dau = datetime.fromisoformat(lich[0]) - timedelta(hours=1)
    cuoi = datetime.fromisoformat(lich[-1]) + timedelta(hours=3)
    now = now or datetime.now().astimezone()
    return dau <= now <= cuoi, f"{dau.isoformat()} → {cuoi.isoformat()}"


def chan_neu_m3(ten: str) -> None:
    trong, cua_so = trong_cua_so_m3()
    if trong and os.environ.get("MICRODUCK_CHO_GROUNDING") != "1":
        raise SystemExit(
            f"{ten}: DỪNG — đang trong cửa sổ M3 ({cua_so}). Script này gọi grounding, dùng chung "
            "hạn 1 500 lượt/ngày mà runner đếm. Xem PREREG_M1-M4 AMENDMENT 02. "
            "Vượt rào có chủ ý: MICRODUCK_CHO_GROUNDING=1 và ghi lý do vào prereg.")
