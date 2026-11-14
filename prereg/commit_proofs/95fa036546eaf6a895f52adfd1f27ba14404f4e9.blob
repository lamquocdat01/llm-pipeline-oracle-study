"""AMENDMENT V2-07: đoạn runtime Ollama và luật chọn cặp cùng runtime. Hàm thuần, chỉ đọc `ts`, không đọc outcome.

Đoạn (bằng chứng: `P2/OLLAMA_RUNTIME_AUDIT_MD.md`):
  A  ts <= 03-11 18:06:27  0.30.10
  B  giữa A và D           0.40.14 (suy luận từ log hệ thống)
  D  ts >= 07-11 10:57:17  0.30.10 (`p2.pin.kiem` xác nhận mỗi lời gọi)
"""
from __future__ import annotations

from datetime import datetime, timedelta

A_HET = datetime.fromisoformat("2026-11-03T18:06:27+07:00")
D_TU = datetime.fromisoformat("2026-11-07T10:57:17+07:00")
CACH_TOI_THIEU = timedelta(hours=24)
K_TOI_THIEU = 5
N_ORACLE = 20


def doan(ts: str) -> str:
    t = datetime.fromisoformat(ts)
    if t <= A_HET:
        return "A"
    return "D" if t >= D_TU else "B"


def cung_runtime(ts: str) -> bool:
    return doan(ts) in ("A", "D")


def chon_k(lan: dict[int, str]) -> int | None:
    """V2-07(b). `lan`: {k: ts} các lần ok của một (câu × stage × nhánh local). Trả k nhỏ nhất ≥ 5 sao cho lần 1 và
    lần k đều ở A/D và cách nhau ≥ 24 h; không có thì None (cặp thiếu, n giảm theo §6)."""
    t1 = lan.get(1)
    if t1 is None or not cung_runtime(t1):
        return None
    goc = datetime.fromisoformat(t1)
    for k in sorted(lan):
        if k >= K_TOI_THIEU and cung_runtime(lan[k]) and datetime.fromisoformat(lan[k]) - goc >= CACH_TOI_THIEU:
            return k
    return None


def lan_oracle_local(hop_le: list[tuple[str, str]], n: int = N_ORACLE) -> list[str]:
    """V2-07(c). `hop_le`: [(task_id, ts)] các lần P2O ok. Trả id của `n` lần đầu theo thời gian thuộc A/D (lần đầu = golden)."""
    return [i for i, ts in sorted(hop_le, key=lambda x: datetime.fromisoformat(x[1])) if cung_runtime(ts)][:n]
