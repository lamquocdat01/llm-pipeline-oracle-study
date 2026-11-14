"""Cổng "được phép chạy việc nặng không" — đọc TRẠNG THÁI CỦA RUNNER, không đoán (CLAUDE.md, 19/09).

Sinh ra từ lỗi 19/09: dò runner bằng tên tiến trình `python.exe` ra "không có", trong khi runner
chạy dưới `pythonw.exe` — pytest và đồng bộ mail chạy đè mẻ đo. Luật ở đây:

  - Chỉ đọc file của chính runner: `LOCK` (pid + commit), `PAUSE`, `PAUSED_ACK` — ở REPO CHÍNH
    (`main_runner_dir`), kể cả khi gọi từ worktree phụ; không tìm ra repo chính -> `busy`.
  - FAIL CLOSED: file nào đọc hỏng, psutil nào lỗi, quyền nào bị từ chối -> `busy`.
  - `free`   : không có `LOCK`, hoặc pid trong `LOCK` đã chết / đã bị tiến trình KHÁC tái dùng.
  - `paused` : runner sống, `PAUSE` có, `PAUSED_ACK` cùng pid và mới hơn `PAUSE` (runner xác nhận
               rảnh). Dưới PAUSE runner VẪN nhận task M3 đến hạn -> còn kiểm cửa sổ M3.
  - `busy`   : mọi trường hợp còn lại.

Ai dùng: `tests/conftest.py` (mọi lần pytest), `scripts/mail_cli.py sync`, `server.py`, và
`scripts/runner_safe.py` (lệnh bọc tạo PAUSE rồi chờ tới khi cổng cho qua).
Module này không import gì nặng: conftest nạp nó ở mọi lần pytest.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


def main_repo(start: Path | str | None = None) -> Path | None:
    """Thư mục REPO CHÍNH (chủ của `.git`), kể cả khi gọi từ một worktree phụ, hoặc None.

    19/09: tìm theo `__file__` thì ở worktree `Microduck-panel` ra `…/Microduck-panel/docs/…`
    — không có LOCK ở đó -> cổng trả `free` và pytest chạy đè mẻ đo. Runner chỉ có MỘT, ở repo
    chính; `git rev-parse --git-common-dir` trỏ về `.git` chung của mọi worktree.
    """
    import subprocess

    cwd = Path(start) if start is not None else Path(__file__).resolve().parent
    try:
        out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             cwd=str(cwd), capture_output=True, text=True, timeout=10,
                             stdin=subprocess.DEVNULL)
    except Exception:
        return None
    common = out.stdout.strip()
    if out.returncode != 0 or not common:
        return None
    common_dir = Path(common)
    return common_dir.parent if common_dir.name == ".git" else None


def main_runner_dir(start: Path | str | None = None) -> Path | None:
    repo = main_repo(start)
    return repo / "docs" / "benchmark" / "runner" if repo is not None else None


# Cửa sổ M3, giống commit_safe.ps1: 25 phút trước -> 10 phút sau 09:00 và 21:00 giờ máy.
M3_HOURS = (9, 21)
M3_BEFORE_MIN = 25
M3_AFTER_MIN = 10

# Oracle M6 do CHÍNH runner gọi pytest (mrunner/thuc.py) với biến này: không được tự chặn mình.
ORACLE_ENV = "MICRODUCK_ORACLE_RUN"


@dataclass(frozen=True)
class GateState:
    verdict: str                  # free | paused | busy
    reason: str
    pid: int | None = None


def _alive_runner(pid: int) -> bool | None:
    """True: pid là runner (`run_m_all` trong cmdline). False: pid chết hoặc là tiến trình khác.
    None: không xác định được (psutil thiếu / bị từ chối quyền) -> người gọi coi là busy."""
    try:
        import psutil
    except Exception:
        return None
    try:
        if not psutil.pid_exists(pid):
            return False
        proc = psutil.Process(pid)
        return "run_m_all" in " ".join(proc.cmdline())
    except psutil.NoSuchProcess:
        return False
    except Exception:
        return None


def state(runner_dir: Path | str | None = None, *, alive=_alive_runner) -> GateState:
    if runner_dir is None:
        runner_dir = main_runner_dir()
    if runner_dir is None:                      # không tìm ra repo chính = không biết -> busy
        return GateState("busy", "không tìm ra repo chính (git rev-parse --git-common-dir hỏng)")
    rd = Path(runner_dir)
    lock = rd / "LOCK"
    if not lock.exists():
        return GateState("free", "không có LOCK: runner không sống")
    try:
        info = json.loads(lock.read_text(encoding="utf-8"))
        pid = int(info["pid"])
    except Exception as exc:
        return GateState("busy", f"LOCK đọc hỏng ({type(exc).__name__}) -> coi như runner đang chạy")
    live = alive(pid)
    if live is None:
        return GateState("busy", f"không xác định được pid {pid} -> coi như runner đang chạy", pid)
    if not live:
        return GateState("free", f"LOCK cũ: pid {pid} không còn là runner", pid)
    pause, ack = rd / "PAUSE", rd / "PAUSED_ACK"
    if not pause.exists():
        return GateState("busy", f"runner pid {pid} đang chạy, không có PAUSE", pid)
    try:
        data = json.loads(ack.read_text(encoding="utf-8"))
        ack_pid = int(data["pid"])
        ack_ts = datetime.fromisoformat(data["ts"]).timestamp()
        pause_ts = pause.stat().st_mtime
    except FileNotFoundError:
        return GateState("busy", f"runner pid {pid}: có PAUSE nhưng CHƯA xác nhận rảnh (có thể giữa task)", pid)
    except Exception as exc:
        return GateState("busy", f"PAUSED_ACK đọc hỏng ({type(exc).__name__}) -> coi như đang chạy", pid)
    if ack_pid != pid or ack_ts < pause_ts:
        return GateState("busy", f"PAUSED_ACK không khớp (pid {ack_pid} vs {pid}, hoặc cũ hơn PAUSE)", pid)
    return GateState("paused", f"runner pid {pid} xác nhận rảnh dưới PAUSE", pid)


def m3_conflict(now: datetime, minutes: float) -> datetime | None:
    """Mốc M3 mà khoảng [now, now + minutes] đè lên cửa sổ của nó, hoặc None."""
    end = now + timedelta(minutes=minutes)
    for day in (-1, 0, 1):
        for hour in M3_HOURS:
            mark = (now + timedelta(days=day)).replace(hour=hour, minute=0, second=0, microsecond=0)
            if now <= mark + timedelta(minutes=M3_AFTER_MIN) and end >= mark - timedelta(minutes=M3_BEFORE_MIN):
                return mark
    return None


def check(what: str, *, minutes: float = 5.0, runner_dir: Path | str | None = None,
          now: datetime | None = None, alive=_alive_runner) -> str | None:
    """None = được chạy. Chuỗi = lý do TỪ CHỐI, kèm cách làm đúng."""
    if os.environ.get(ORACLE_ENV):
        return None
    st = state(runner_dir, alive=alive)
    if st.verdict == "busy":
        return (f"{what}: TỪ CHỐI — {st.reason}. Chạy qua: "
                f"python scripts\\runner_safe.py --minutes N -- <lệnh> (CLAUDE.md).")
    if st.verdict == "paused":
        mark = m3_conflict(now or datetime.now(), minutes)
        if mark is not None:
            return (f"{what}: TỪ CHỐI — {minutes:g} phút tới đè cửa sổ M3 quanh {mark:%Y-%m-%d %H:%M} "
                    f"(dưới PAUSE runner vẫn chạy M3).")
    return None
