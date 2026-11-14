r"""M6 — đặt oracle (AMENDMENT 04 §A04.3). Phần dùng chung cho executor, hai bộ test và phép chấm.

Hai bộ `desktop/tests/oracle_decision/` và `desktop/tests/oracle_artefact/` assert trên CÙNG đầu ra
của một lần chạy (ghép cặp): executor `M6Run` gọi pipeline một lần mỗi input, ghi `obs` ra file,
rồi chạy pytest với
    MICRODUCK_ORACLE_RUN    = file obs của lần này
    MICRODUCK_ORACLE_GOLDEN = file obs của lần chạy 1 (golden, không chọn tay)
Không đặt biến ⇒ `desktop/tests/conftest.py` bỏ hai thư mục khỏi collection (pytest mặc định và
`commit_safe` không chạm API).
"""
from __future__ import annotations

import json
import os
import random
import re
import unicodedata
from pathlib import Path

ENV_RUN = "MICRODUCK_ORACLE_RUN"
ENV_GOLDEN = "MICRODUCK_ORACLE_GOLDEN"
SEED_ROUTING = 20260917
N_ROUTING_MOI_O = 10
LICH_GIO = ("01:30", "05:30", "11:30", "15:30", "19:30")
LICH_NGAY = ("2026-09-18", "2026-09-19", "2026-09-20", "2026-09-21")


def chuan_hoa(s: str | None) -> str:
    """Luật artefact A04.3: lower, bỏ dấu câu Unicode (category P*), gộp khoảng trắng, strip.
    KHÔNG bỏ dấu thanh tiếng Việt (đó là chữ, không phải dấu câu)."""
    s = unicodedata.normalize("NFC", s or "").lower()
    s = "".join(" " if unicodedata.category(c).startswith("P") else c for c in s)
    return re.sub(r"\s+", " ", s).strip()


def bo_the(s: str | None) -> str:
    """Bỏ thẻ điều khiển kiểu `[lookup]` trước khi nhận diện ngôn ngữ lời trả lời."""
    return re.sub(r"\[[^\]]{1,40}\]", " ", s or "").strip()


def chon_routing(khoi_a: list[dict]) -> list[dict]:
    """40 câu khối A, 10 mỗi ô (needs_lookup × lang), seed 20260917, trên danh sách sắp theo id."""
    rng = random.Random(SEED_ROUTING)
    ra: list[dict] = []
    for need in (True, False):
        for lang in ("vi", "en"):
            o = sorted((r for r in khoi_a if r["needs_lookup"] is need and r["lang"] == lang),
                       key=lambda r: r["id"])
            ra += rng.sample(o, N_ROUTING_MOI_O)
    return ra


def chon_stt(s3_files: list[dict]) -> tuple[list[dict], list[str]]:
    """23 WAV S3: câu s lấy giọng ((s-1) mod 3)+1, render 1. Render 1 bị VAD loại ⇒ render nhận
    nhỏ nhất của cùng (câu, giọng), và trả kèm ghi chú lệch để in vào plan."""
    ok = [f for f in s3_files if f["accepted"]]
    ra, lech = [], []
    for s in sorted({f["s"] for f in s3_files}):
        v = (s - 1) % 3 + 1
        cung = sorted((f for f in ok if f["s"] == s and f["v"] == v), key=lambda f: f["r"])
        if not cung:
            raise ValueError(f"S3 câu {s} giọng {v}: không có render nào được nhận")
        if cung[0]["r"] != 1:
            lech.append(f"câu {s} giọng {v}: render 1 bị loại, dùng render {cung[0]['r']}")
        ra.append(cung[0])
    return ra, lech


def doc_obs(bien: str) -> dict:
    p = os.environ.get(bien)
    if not p:
        raise RuntimeError(f"thiếu biến {bien}")
    return json.loads(Path(p).read_text(encoding="utf-8"))


def cap_test(obs: dict, golden: dict) -> list[tuple[str, str, str, dict, dict]]:
    """(stage, backend, input_id, đầu ra lần này, golden) cho mọi input có trong golden.
    Input thiếu ở lần này ⇒ đầu ra rỗng ⇒ test fail (thiếu là một dạng đổi, không được bỏ qua)."""
    ra = []
    for stage in ("stt", "routing"):
        for be in ("hosted", "local"):
            g = golden.get(stage, {}).get(be, {})
            o = obs.get(stage, {}).get(be, {})
            for iid in sorted(g):
                ra.append((stage, be, iid, o.get(iid) or {}, g[iid]))
    return ra
