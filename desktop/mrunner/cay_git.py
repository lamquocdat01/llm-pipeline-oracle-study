r"""Cổng "mã đang chạy = một commit" (đợt 27d): LOCK mang commit lúc runner khởi động; cây làm việc
trong PHẠM VI runner phải sạch mới được khởi động.

Vì sao có: 17/09 runner khởi động từ cây chưa commit và 16 bản ghi trỏ manifest `commit = d3e7efd`
trong khi mã chạy là `371ed8a` (A05.6). `commit_repo()` đọc HEAD, không đọc cây làm việc — nên một
HEAD đúng không nói gì về mã đã chạy nếu cây bẩn.

PHẠM VI, không phải toàn repo: `git status --porcelain` toàn repo không bao giờ rỗng ở đây — runner
tự ghi file kết quả chưa track (`docs/benchmark/*.jsonl`), và `Submission TSE/` có sửa của người khác.
Cổng xét đúng phần mã/cấu hình runner nạp: `desktop/` (gitignore đã loại `desktop/logs/`, `.venv`),
`shared/`, `study/langconf/`, và `plan.json`. Tính cả file untracked trong phạm vi (một .py mới chưa
commit cũng là mã chạy được).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

PHAM_VI = ("desktop", "shared", "study/langconf", "docs/benchmark/runner/plan.json")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          encoding="utf-8", timeout=60, stdin=subprocess.DEVNULL, **kw)


def head(root: Path) -> str | None:
    r = _git(root, "rev-parse", "HEAD")
    return r.stdout.strip() if r.returncode == 0 else None


def ban(root: Path) -> list[str]:
    """Dòng porcelain trong phạm vi (rỗng = sạch). Không phải repo git ⇒ một dòng lỗi."""
    r = _git(root, "status", "--porcelain", "--untracked-files=all", "--", *PHAM_VI)
    if r.returncode != 0:
        return [f"git status lỗi: {r.stderr.strip()[:200]}"]
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def ghi_log(runner_dir: Path, muc: str, thong_diep: str) -> None:
    """Một dòng cùng định dạng runner.log, mở–ghi–đóng (tiến trình --ensure không giữ handler)."""
    from datetime import datetime
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    runner_dir.mkdir(parents=True, exist_ok=True)
    with (runner_dir / "runner.log").open("a", encoding="utf-8") as f:
        f.write(f"{t} {muc} ensure {thong_diep}\n")
