r"""Lõi runner M1–M4: chết lúc nào cũng được, sống lại không trùng, không mất.

## Luật (đợt 27b) — mỗi luật là một cơ chế, không phải một lời hứa

1. **Không có state ngoài `plan.json` + các file jsonl.** Tiến độ = plan − bản ghi cuối.
   Mọi quyết định (việc nào xong, mốc nào đến hạn, đã tiêu bao nhiêu tiền, task lỗi được
   thử lại lúc nào) đọc lại từ đĩa ở MỖI vòng. RAM chỉ giữ thứ tạm thời vô hại (cờ "máy
   đang bận, hoãn việc nặng 2 phút").
2. **Kết quả append-only, fsync từng dòng.** Dòng hỏng (chết giữa lúc ghi) bị BỎ QUA và
   log, không sửa file; task của nó coi như chưa làm. Trước khi ghi dòng mới, nếu file
   không kết thúc bằng `\n` thì ghi thêm một `\n` — để dòng mới không dính vào mẩu hỏng
   và cùng hỏng theo. Đó là thao tác NỐI, không đụng byte cũ.
3. **Idempotent:** một `task_id` có tối đa MỘT bản ghi cuối (`ok`/`missed`) trong file
   kết quả. Lỗi tạm thời đi file riêng `<kết quả>.errors.jsonl`, nên thử lại không làm
   file kết quả có hai dòng cùng `task_id`.
4. **Mốc tương đối tính từ `ts` (lúc BẮT ĐẦU gọi) của bản ghi mốc trước trong jsonl,**
   không từ đồng hồ tiến trình. Runner chết 10 phút giữa mốc 180 s thì mốc ấy đến hạn
   đúng `ts_prev + 180`, chạy ngay khi sống lại và ghi `late_by_s`.
5. **Mốc tuyệt đối (M3):** muộn quá `late_missed_s` (2 h) mà chưa có kết quả ⇒ ghi
   `status: missed`, không nội suy, không bù.
6. **Ngân sách cộng dồn từ đĩa** (usage trong bản ghi ok + bản ghi lỗi) × giá trong plan.
   Chạm trần ⇒ task hosted không nhận nữa (`budget_stop` trong `status`), task local
   vẫn chạy. Không ghi bản ghi `budget_stop` vào file kết quả: nâng trần thì task ấy
   chạy tiếp được, không bị đóng dấu vĩnh viễn.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("mrunner")

FINAL = ("ok", "missed")
BACKOFF_S = (60, 120, 240, 480, 960)      # 1-2-4-8-16 phút
RETRY_CYCLE_S = 1800                      # quá 5 lần: quay lại sau 30 phút
BUSY_WAIT_S = 120


# ---------------------------------------------------------------------------
# thời gian: mọi ts là ISO có múi giờ, đọc lại bằng fromisoformat
def to_iso(t: float) -> str:
    return datetime.fromtimestamp(t).astimezone().isoformat(timespec="milliseconds")


def from_iso(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


def ngay_pt(ts_iso: str) -> str:
    """Ngày theo giờ Pacific — hạn grounding miễn phí/ngày của Google tính lại lúc nửa đêm PT.

    Đếm theo ngày giờ máy (+07:00) sẽ lệch 14 h: một "ngày" của ta cắt ngang hai ngày quota.
    """
    from zoneinfo import ZoneInfo
    return datetime.fromisoformat(ts_iso).astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()


# ---------------------------------------------------------------------------
class Store:
    """Một file jsonl append-only. Đọc bỏ dòng hỏng; ghi flush + fsync."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def read(self) -> tuple[list[dict], int]:
        if not self.path.exists():
            return [], 0
        good: list[dict] = []
        bad = 0
        with self.path.open("rb") as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line.decode("utf-8"))
                    if not isinstance(rec, dict) or "task_id" not in rec:
                        raise ValueError("không phải bản ghi task")
                except Exception as exc:             # dòng hỏng: bỏ qua, KHÔNG sửa file
                    bad += 1
                    log.warning("%s:%d dòng hỏng, bỏ qua (%s)", self.path.name, i,
                                type(exc).__name__)
                    continue
                good.append(rec)
        return good, bad

    def append(self, rec: dict) -> None:
        data = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Móc đối chứng dương (gate 2): ghi NỬA dòng, fsync, rồi chết cứng như kill -9.
        crash = os.environ.get("MRUNNER_CRASH_AT_WRITE")
        with self.path.open("ab") as f:
            if f.tell() > 0 and not _ends_with_newline(self.path):
                f.write(b"\n")
            if crash and _dem_ghi() == int(crash):
                f.write(data[: len(data) // 2])
                f.flush()
                os.fsync(f.fileno())
                os._exit(9)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())


_so_lan_ghi = [0]


def _dem_ghi() -> int:
    _so_lan_ghi[0] += 1
    return _so_lan_ghi[0]


def _ends_with_newline(p: Path) -> bool:
    with p.open("rb") as f:
        f.seek(-1, os.SEEK_END)
        return f.read(1) == b"\n"


# ---------------------------------------------------------------------------
class Lock:
    """`LOCK` chứa PID + ts. PID còn sống ⇒ không lấy được. PID chết ⇒ ghi đè."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def holder(self) -> dict | None:
        try:
            info = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return info if pid_song(int(info.get("pid", -1))) else None

    def acquire(self, them: dict | None = None) -> bool:
        """`them`: trường ghi kèm (runner thật ghi `commit` = HEAD lúc khởi động — đợt 27d)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if self.holder() is not None:
                    return False
                try:
                    self.path.unlink()                # khoá của tiến trình đã chết
                except FileNotFoundError:
                    pass
                continue
            os.write(fd, json.dumps({"pid": os.getpid(), "ts": to_iso(time.time()), **(them or {})}).encode())
            os.close(fd)
            return True
        return False

    def release(self) -> None:
        try:
            info = json.loads(self.path.read_text(encoding="utf-8"))
            if int(info.get("pid", -1)) == os.getpid():
                self.path.unlink()
        except Exception:
            pass


def pid_song(pid: int) -> bool:
    """PID còn sống VÀ chính là runner — PID Windows bị tái dùng, một PID trùng số không đủ.

    Chỉ kiểm "là python" thì chưa đủ: chủ nhân chạy pytest (python) trùng PID cũ là runner
    tưởng khoá còn sống và không bao giờ bật lại. Nên đòi cmdline chứa `run_m_all`.
    """
    if pid <= 0:
        return False
    try:
        import psutil
        if not psutil.pid_exists(pid):
            return False
        p = psutil.Process(pid)
        return "python" in p.name().lower() and "run_m_all" in " ".join(p.cmdline())
    except Exception:
        return False


# ---------------------------------------------------------------------------
class RateLimited(Exception):
    def __init__(self, msg: str, retry_after_s: float | None = None) -> None:
        super().__init__(msg)
        self.retry_after_s = retry_after_s


def retry_after_from(exc: BaseException) -> float | None:
    """429 của Gemini mang `retryDelay: '37s'` trong thân lỗi. Không có thì None."""
    m = re.search(r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s", str(exc))
    return float(m.group(1)) if m else None


def la_429(exc: BaseException) -> bool:
    s = str(exc)
    return getattr(exc, "code", None) == 429 or "429" in s[:40] or "RESOURCE_EXHAUSTED" in s


# ---------------------------------------------------------------------------
def gia_usd(usage: dict | None, price: dict) -> float:
    """usage: {in_text, in_audio, out, grounded} theo token/lượt. Giá theo 1M token."""
    if not usage:
        return 0.0
    return (usage.get("in_text", 0) * price["in_text"]
            + usage.get("in_audio", 0) * price["in_audio"]
            + usage.get("out", 0) * price["out"]) / 1_000_000


@dataclass
class Snapshot:
    done: dict[str, dict] = field(default_factory=dict)
    errors: dict[str, list[dict]] = field(default_factory=dict)
    bad_lines: int = 0
    spent_usd: float = 0.0
    grounded_by_day: dict[str, int] = field(default_factory=dict)
    hosted_cooldown_until: float = 0.0


class Runner:
    """Một vòng quyết định = đọc đĩa → chọn MỘT task → chạy → ghi. Lặp."""

    def __init__(self, plan: dict, root: Path, executors: dict[str, Any],
                 clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep,
                 cpu_busy: Callable[[], bool] | None = None) -> None:
        self.plan = plan
        self.root = Path(root)
        self.ex = executors
        self.clock = clock
        self.sleep = sleep
        self.cpu_busy = cpu_busy
        self.busy_until = 0.0                   # RAM, tạm thời, mất đi cũng vô hại
        self.tasks = plan["tasks"]
        self.by_id = {t["id"]: t for t in self.tasks}
        assert len(self.by_id) == len(self.tasks), "task_id trùng trong plan"
        self.stores = {m: Store(self.root / p) for m, p in plan["results"].items()}
        self.err_stores = {m: Store(self.root / p.replace(".jsonl", ".errors.jsonl"))
                           for m, p in plan["results"].items()}
        self.manifest_seen: set[str] = set()

    # -- đọc trạng thái TỪ ĐĨA -----------------------------------------------
    def snapshot(self) -> Snapshot:
        s = Snapshot()
        price = self.plan["price"]
        for m, st in self.stores.items():
            recs, bad = st.read()
            s.bad_lines += bad
            for r in recs:
                if r.get("status") in FINAL and r["task_id"] not in s.done:
                    s.done[r["task_id"]] = r
                self._cong_tien(s, r, price)
            erecs, bad = self.err_stores[m].read()
            s.bad_lines += bad
            for r in erecs:
                s.errors.setdefault(r["task_id"], []).append(r)
                self._cong_tien(s, r, price)
                if r.get("rate_limited") and r.get("hosted"):
                    s.hosted_cooldown_until = max(s.hosted_cooldown_until,
                                                  from_iso(r["ts"]) + float(r.get("retry_after_s") or 60))
        free = int(price.get("grounding_free_per_day") or 0)
        for day, n in s.grounded_by_day.items():
            s.spent_usd += max(0, n - free) * price.get("grounding_per_1000", 0) / 1000
        return s

    @staticmethod
    def _cong_tien(s: Snapshot, r: dict, price: dict) -> None:
        u = r.get("usage")
        if not u:
            return
        s.spent_usd += gia_usd(u, price)
        if u.get("grounded"):
            day = ngay_pt(r["ts"])
            s.grounded_by_day[day] = s.grounded_by_day.get(day, 0) + int(u["grounded"])

    # -- lịch ----------------------------------------------------------------
    def due_of(self, t: dict, s: Snapshot) -> float | None:
        """Thời điểm đến hạn, hoặc None nếu mốc trước chưa có kết quả ok."""
        if t.get("at"):
            return from_iso(t["at"])
        dep = t.get("after")
        if not dep:
            return 0.0
        prev = s.done.get(dep["task"])
        if prev is None or prev.get("status") != "ok":
            return None
        return from_iso(prev["ts"]) + float(dep["delta_s"])

    def retry_at(self, t: dict, s: Snapshot) -> float:
        """Thời điểm được thử lại sau lỗi — tính từ file lỗi, không từ RAM."""
        errs = s.errors.get(t["id"], [])
        if not errs:
            return 0.0
        last = errs[-1]
        t_last = from_iso(last["ts"])
        if last.get("rate_limited"):
            return t_last + float(last.get("retry_after_s") or 60)
        # số lần hỏng liên tiếp trong chu kỳ hiện tại (chu kỳ kết thúc ở bản ghi cycle_end)
        k = 0
        for e in reversed(errs):
            if e.get("cycle_end"):
                break
            k += 1
        if last.get("cycle_end"):
            return t_last + RETRY_CYCLE_S
        return t_last + BACKOFF_S[min(k - 1, len(BACKOFF_S) - 1)]

    def paused(self) -> bool:
        return (self.root / self.plan["runner_dir"] / "PAUSE").exists()

    def pick(self, s: Snapshot, now: float) -> tuple[dict | None, float | None, list[dict]]:
        """(task được chọn, lúc thức dậy gần nhất nếu không có, các task M3 phải ghi missed)."""
        budget_hit = s.spent_usd >= float(self.plan["budget_usd"])
        pause = self.paused()
        late_max = float(self.plan.get("late_missed_s", 7200))
        missed: list[dict] = []
        g0: list[tuple[float, int, dict]] = []
        g1: list[tuple[float, int, dict]] = []
        g2: list[tuple[int, int, dict]] = []
        wake: float | None = None
        for idx, t in enumerate(self.tasks):
            if t["id"] in s.done:
                continue
            due = self.due_of(t, s)
            if due is None:
                continue
            if t.get("at") and not t.get("khong_missed") and now > due + late_max:
                missed.append(t)                       # M3; M6 (A04.3) không có luật missed
                continue
            ready_at = max(due, self.retry_at(t, s))
            if t.get("hosted"):
                if budget_hit:
                    continue
                ready_at = max(ready_at, s.hosted_cooldown_until)
            if ready_at > now:
                wake = ready_at if wake is None else min(wake, ready_at)
                continue
            ex = self.ex.get(t["kind"])
            if ex is not None and hasattr(ex, "ready") and not ex.ready(t):
                continue                               # chờ đầu vào (vd WAV chưa thu)
            if pause and t.get("cho_pause"):
                continue                               # M6: PAUSE chặn cả task có mốc tuyệt đối
            if t.get("at"):
                if t.get("heavy") and not t.get("exempt_busy") and now < self.busy_until:
                    wake = self.busy_until if wake is None else min(wake, self.busy_until)
                    continue
                g0.append((due, idx, t))
                continue
            if pause:
                continue
            if t.get("heavy") and not t.get("exempt_busy") and now < self.busy_until:
                wake = self.busy_until if wake is None else min(wake, self.busy_until)
                continue
            if t.get("after"):
                g1.append((due, idx, t))
            else:
                g2.append((int(t.get("order", 9)), idx, t))
        for g in (g0, g1, g2):
            if g:
                return sorted(g, key=lambda x: (x[0], x[1]))[0][2], None, missed
        return None, wake, missed

    # -- chạy ------------------------------------------------------------------
    def manifest_ref(self, t: dict) -> str | None:
        ex = self.ex.get(t["kind"])
        if ex is None or not hasattr(ex, "manifest"):
            return None
        man = ex.manifest(t)
        blob = json.dumps(man, sort_keys=True, ensure_ascii=False)
        mid = hashlib.sha256(blob.encode()).hexdigest()[:16]
        path = self.plan["results"][t["m"]].replace(".jsonl", ".manifest.jsonl")
        if mid not in self.manifest_seen:
            st = Store(self.root / path)
            recs, _ = st.read()
            if not any(r.get("task_id") == mid for r in recs):
                st.append({"task_id": mid, "ts": to_iso(self.clock()), "manifest": man})
            self.manifest_seen.add(mid)
        return f"{Path(path).name}#{mid}"

    def step(self) -> str:
        """Một vòng. Trả 'ran' | 'missed' | 'idle:<giây ngủ>' | 'busy'."""
        s = self.snapshot()
        now = self.clock()
        t, wake, missed = self.pick(s, now)
        for m in missed:
            due = from_iso(m["at"])
            self.stores[m["m"]].append({"task_id": m["id"], "m": m["m"], "status": "missed",
                                        "ts": to_iso(now), "due": m["at"],
                                        "late_by_s": round(now - due, 1)})
            log.info("MISSED %s (muộn %.0f s)", m["id"], now - due)
        if missed:
            return "missed"
        if t is None:
            return f"idle:{max(1.0, min(60.0, (wake - now) if wake else 60.0)):.1f}"
        if t.get("heavy") and not t.get("exempt_busy") and self.cpu_busy and self.cpu_busy():
            self.busy_until = self.clock() + BUSY_WAIT_S
            log.info("máy bận, hoãn việc nặng %d s", BUSY_WAIT_S)
            return "busy"
        return self.run_task(t, s)

    def run_task(self, t: dict, s: Snapshot) -> str:
        due = self.due_of(t, s)
        ex = self.ex[t["kind"]]
        ref = self.manifest_ref(t)
        start = self.clock()
        base = {"task_id": t["id"], "m": t["m"], "ts": to_iso(start),
                "due": to_iso(due) if due else None,
                "late_by_s": round(start - due, 1) if due else None,
                "manifest_ref": ref,
                # A05: bản ghi KHÔNG có trường này (trước khi đặt offline) được coi là hf_offline=false
                "hf_offline": os.environ.get("HF_HUB_OFFLINE") == "1"}
        try:
            out = ex.run(t) or {}
        except Exception as exc:
            rl = isinstance(exc, RateLimited) or la_429(exc)
            errs = s.errors.get(t["id"], [])
            k = 0
            for e in reversed(errs):
                if e.get("cycle_end"):
                    break
                k += 1
            rec = {**base, "status": "error", "hosted": bool(t.get("hosted")),
                   "error": f"{type(exc).__name__}: {exc}"[:400],
                   "attempt": k + 1, "cycle_end": (k + 1) >= len(BACKOFF_S) and not rl,
                   "rate_limited": rl,
                   "retry_after_s": (getattr(exc, "retry_after_s", None) or retry_after_from(exc))
                   if rl else None,
                   "usage": getattr(exc, "usage", None)}
            self.err_stores[t["m"]].append(rec)
            log.warning("LỖI %s lần %d: %s", t["id"], k + 1, rec["error"][:160])
            return "error"
        rec = {**base, "status": "ok", "ts_end": to_iso(self.clock()),
               "usage": out.pop("usage", None), "payload": out}
        if rec["usage"] and rec["usage"].get("grounded"):
            # Điều kiện chủ nhân (AMENDMENT 02): mỗi bản ghi có grounding mang số lượt đã dùng
            # trong ngày PT, ĐẾM TỪ ĐĨA (mọi bản ghi ok + lỗi đã có) cộng lượt này. API không
            # trả con số ấy; `quota_headers` trong payload giữ header quota nếu API có trả.
            day = ngay_pt(base["ts"])
            rec["grounding_ngay_pt"] = {"ngay": day,
                                        "da_dung_runner_dem": s.grounded_by_day.get(day, 0)
                                        + int(rec["usage"]["grounded"]),
                                        "han_mien_phi": self.plan["price"].get("grounding_free_per_day")}
        # Idempotent ở tầng ghi: đọc lại ngay trước khi ghi (một runner khác không được
        # tồn tại, nhưng rẻ để chắc).
        recs, _ = self.stores[t["m"]].read()
        if any(r["task_id"] == t["id"] and r.get("status") in FINAL for r in recs):
            log.error("BỎ bản ghi trùng %s", t["id"])
            return "dup"
        self.stores[t["m"]].append(rec)
        return "ran"

    def ack_path(self) -> Path:
        return self.root / self.plan["runner_dir"] / "PAUSED_ACK"

    def _ack(self, idle: bool) -> None:
        """`PAUSED_ACK` = runner ĐANG PAUSE và KHÔNG giữa task nào. `commit_safe.ps1` chờ file
        này (mới hơn PAUSE) trước khi chạy pytest — cơ chế, không phải đoán theo log."""
        p = self.ack_path()
        try:
            if idle and self.paused():
                p.write_text(json.dumps({"pid": os.getpid(), "ts": to_iso(self.clock())}), encoding="utf-8")
            elif p.exists():
                p.unlink()
        except OSError:
            pass

    def loop(self, max_steps: int | None = None, stop_when_idle: bool = False) -> None:
        n = 0
        while max_steps is None or n < max_steps:
            n += 1
            if not self.paused():
                self._ack(False)
            r = self.step()
            self._ack(r.startswith("idle:"))
            if r.startswith("idle:"):
                if stop_when_idle:
                    return
                self.sleep(float(r.split(":")[1]) if not self.paused() else 30.0)
            elif r == "busy":
                self.sleep(1.0)

    # -- báo cáo ---------------------------------------------------------------
    def khoang_trong(self, s: Snapshot, now: float, nguong_s: float = 3600.0) -> list[tuple[float, float]]:
        """Các khoảng > `nguong_s` không có bản ghi nào (ok/missed/lỗi) trong lúc có task đến hạn
        chưa xong (việc 27f.1: máy ngủ 17/09 21:41 → 18/09 10:01 không ai thấy). Trả [(từ, tới)];
        khoảng cuối kết thúc ở `now` nếu đang trống. Chỉ để cảnh báo — không đổi lịch."""
        moc: list[float] = []
        xong: dict[str, float] = {}
        for tid, r in s.done.items():
            moc.append(from_iso(r["ts"]))
            if r.get("ts_end"):
                moc.append(from_iso(r["ts_end"]))
            xong[tid] = from_iso(r["ts"])
        for errs in s.errors.values():
            moc.extend(from_iso(e["ts"]) for e in errs)
        if not moc:
            return []
        moc.sort()
        han = [(d, xong.get(t["id"], float("inf"))) for t in self.tasks
               if (d := self.due_of(t, s)) is not None]
        ra = []
        for a, b in zip(moc, moc[1:] + [now]):
            if b - a <= nguong_s:
                continue
            cho = [max(a, d) for d, x in han if d < b and x >= b]   # đến hạn, chưa xong trước b
            if cho and b - min(cho) > nguong_s:
                ra.append((min(cho), b))
        return ra

    def status_rows(self) -> tuple[list[dict], Snapshot]:
        s = self.snapshot()
        now = self.clock()
        budget_hit = s.spent_usd >= float(self.plan["budget_usd"])
        rows = []
        for m in self.plan["results"]:
            ts = [t for t in self.tasks if t["m"] == m]
            done = [t for t in ts if t["id"] in s.done and s.done[t["id"]]["status"] == "ok"]
            missed = [t for t in ts if t["id"] in s.done and s.done[t["id"]]["status"] == "missed"]
            pend = [t for t in ts if t["id"] not in s.done]
            err = [t for t in pend if s.errors.get(t["id"])]
            bstop = [t for t in pend if t.get("hosted") and budget_hit]
            wait_in = [t for t in pend if hasattr(self.ex.get(t["kind"]), "ready")
                       and not self.ex[t["kind"]].ready(t)]
            nxt = None
            for t in pend:
                d = self.due_of(t, s)
                if d is not None and d > now and (nxt is None or d < nxt[0]):
                    nxt = (d, t["id"])
            rows.append({"m": m, "xong": len(done), "tong": len(ts), "error": len(err),
                         "missed": len(missed), "budget_stop": len(bstop),
                         "cho_dau_vao": len(wait_in),
                         "moc_ke": (to_iso(nxt[0]), nxt[1]) if nxt else None})
        return rows, s
