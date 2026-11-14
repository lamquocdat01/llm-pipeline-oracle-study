"""`run_m_all.py doctor` — kiểm mọi điều kiện chạy thật, KHÔNG thu âm, KHÔNG chạy task.

Mỗi dòng: ✅ đạt · ⚠ cần chủ nhân biết · ❌ chặn chạy. rc = 1 nếu có ❌.
Gọi API đúng MỘT lượt (5 token vào, trần 5 token ra) để đọc tier và model_version.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from mrunner.thuc import REPO, dam_bao_ollama, ollama_digest, sha256_file


def doctor(plan: dict | None) -> int:
    kq: list[tuple[str, str, str]] = []

    def them(muc: str, ok: str, chi_tiet: str) -> None:
        kq.append((ok, muc, chi_tiet))

    # --- Ollama + digest ------------------------------------------------------
    try:
        dam_bao_ollama()
        for m in ("qwen2.5:7b", "qwen2.5:3b"):
            d = ollama_digest(m)
            them(f"ollama {m}", "✅" if d else "❌", f"digest {d}" if d else "CHƯA CÀI (`ollama pull`)")
    except Exception as exc:
        them("ollama", "❌", f"{type(exc).__name__}: {exc}")

    # --- Gemini: key, tier, model_version -------------------------------------
    try:
        import sys
        sys.path.insert(0, str(REPO / "desktop"))
        from config import Config
        from google import genai
        from google.genai import types
        cfg = Config.load()
        if not cfg.gemini_api_key:
            them("GEMINI_API_KEY", "❌", "không có")
        else:
            them("GEMINI_API_KEY", "✅", f"có (model {cfg.gemini_model})")
            client = genai.Client(api_key=cfg.gemini_api_key)   # giữ tham chiếu: client tạm bị thu gom giữa lượt gọi
            r = client.models.generate_content(
                model=cfg.gemini_model, contents="Reply with: ok",
                config=types.GenerateContentConfig(max_output_tokens=5,
                                                   thinking_config=types.ThinkingConfig(thinking_budget=0)))
            h = dict(getattr(getattr(r, "sdk_http_response", None), "headers", None) or {})
            them("Gemini 1 lượt gọi", "✅",
                 f"model_version={r.model_version} · x-gemini-service-tier={h.get('x-gemini-service-tier')}"
                 " (header này là lớp suy luận flex/standard/priority, KHÔNG phải gói free/trả phí)")
    except Exception as exc:
        them("Gemini", "❌", f"{type(exc).__name__}: {str(exc)[:200]}")

    # Tier: API không có endpoint đọc gói. Bằng chứng trong repo: khối lượng một ngày của
    # cùng key. Gói free của 2.5 Flash giới hạn vài trăm lượt/ngày.
    try:
        rows = [json.loads(l) for l in (REPO / "study/langconf/results/main_gemini.jsonl")
                .read_text(encoding="utf-8").splitlines() if l.strip()]
        ngay: dict[str, int] = {}
        for x in rows:
            ngay[str(x.get("ts"))[:10]] = ngay.get(str(x.get("ts"))[:10], 0) + 1
        d, n = max(ngay.items(), key=lambda kv: kv[1])
        them("gói Gemini (suy từ dữ liệu)", "⚠",
             f"TRẢ PHÍ: {n:,} lượt trong ngày {d} cùng key (main_gemini.jsonl) — gói free không đạt được. "
             "Luật chủ nhân: trả phí ⇒ dừng, hỏi trước mốc M3")
    except Exception as exc:
        them("gói Gemini", "⚠", f"không suy được: {exc}")

    # --- Mic (chỉ báo) ----------------------------------------------------------
    try:
        import sounddevice as sd
        vao = [d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0]
        them("mic (cho thu 69 câu M1)", "✅" if vao else "⚠", f"{len(vao)} thiết bị vào; mặc định: "
             f"{sd.query_devices(kind='input')['name'] if vao else '—'}")
    except Exception as exc:
        them("mic", "⚠", f"{type(exc).__name__}: {exc}")

    # --- đầu vào ----------------------------------------------------------------
    utts = REPO / "desktop/logs/utts"
    rv1 = sorted(utts.glob("20260906_134002_0*.wav"))
    them("M1 rv1 (31 WAV thật 06/09)", "✅" if len(rv1) == 31 else "❌", f"{len(rv1)}/31")
    if plan:
        wild = [t for t in plan["tasks"] if t["m"] == "M1" and t["params"].get("tang") == "wild"
                and t["id"].endswith("|gemini|t0|1")]
        thieu = [t for t in wild if not (REPO / t["params"]["wav"]).exists()]
        them("M1 wild (in-the-wild)", "✅" if not thieu else "❌", f"{len(wild) - len(thieu)}/{len(wild)} có mặt")
        if plan["m1"]["rv2_wavs"]:
            n = sum(1 for w in plan["m1"]["rv2_wavs"] if (REPO / w).exists())
            them("M1 rv2 (69 câu mới)", "⚠" if n < 69 else "✅",
                 f"{n}/69 file {plan['m1']['rv2_dir']}/rv2_sNN_rK.wav — tầng chính CHỜ tới khi đủ 69")
        else:
            them("M1 rv2", "✅", "huỷ theo AMENDMENT 04 — không chờ đầu vào")
        s3 = [t for t in plan["tasks"] if t["params"].get("tang") == "s3" and t["id"].endswith("|gemini|t0|1")]
        lech = [t for t in s3 if not (REPO / t["params"]["wav"]).exists()
                or sha256_file(REPO / t["params"]["wav"]) != t["params"]["wav_sha256"]]
        if s3:
            them("M1 S3 (tổng hợp)", "✅" if not lech else "❌", f"{len(s3) - len(lech)}/{len(s3)} WAV khớp SHA-256")
    for ten, p in (("whisper large-v3-turbo cache",
                    Path.home() / ".cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo"),
                   ("fastText lid.176", REPO / "study/langconf/data/lid/lid.176.bin"),
                   ("lookup_set_v1", REPO / "docs/benchmark/lookup_set_v1.jsonl"),
                   ("persona duck.md", REPO / "shared/persona/duck.md")):
        them(ten, "✅" if p.exists() else "❌", str(p) if p.exists() else "THIẾU")
    them("duck.md SHA-256", "✅", sha256_file(REPO / "shared/persona/duck.md")[:16])

    # --- Hugging Face: offline + revision ghim (AMENDMENT 05) ---------------------
    from mrunner import hf_pin
    for k, v in hf_pin.BIEN.items():
        import os
        them(f"env {k}", "✅" if os.environ.get(k) == v else "❌", repr(os.environ.get(k)))
    if plan is not None:
        them("plan.hf_pin", "✅" if plan.get("hf_pin") == hf_pin.PIN else "❌",
             "trùng mrunner/hf_pin.PIN" if plan.get("hf_pin") == hf_pin.PIN else "THIẾU hoặc khác mã")
    loi = hf_pin.kiem(plan.get("hf_pin") if plan and plan.get("hf_pin") else hf_pin.PIN)
    for repo, p in hf_pin.PIN.items():
        mine = [x for x in loi if x.startswith(repo)]
        them(f"HF {repo.split('/')[-1]}@{p['revision'][:12]}", "❌" if mine else "✅",
             "; ".join(mine) if mine else f"{len(p['files_sha256'])} file khớp SHA-256 · {p['dung_cho']}")
        ref = hf_pin.HUB / ("models--" + repo.replace("/", "--")) / "refs/main"
        rm = ref.read_text().strip() if ref.exists() else None
        them(f"  refs/main {repo.split('/')[-1]}", "✅" if rm == p["revision"] else "⚠",
             f"{(rm or '—')[:12]} (chỉ tham khảo: runner nạp theo đường dẫn revision, không theo main)")
    for x in loi:
        if not any(x.startswith(r) for r in hf_pin.PIN):
            them("HF offline", "❌", x)

    # --- mã đang chạy = một commit (đợt 27d) --------------------------------------
    from mrunner import cay_git
    from mrunner.core import Lock
    hd, ban_ = cay_git.head(REPO), cay_git.ban(REPO)
    them("cây làm việc (phạm vi runner)", "❌" if ban_ else "✅",
         ("BẨN: " + "; ".join(ban_[:8])) if ban_ else f"sạch trong {', '.join(cay_git.PHAM_VI)} · HEAD {str(hd)[:12]}")
    h = Lock(REPO / "docs/benchmark/runner/LOCK").holder()
    if h is None:
        them("commit trong LOCK", "⚠", "không có runner sống")
    else:
        ok = h.get("commit") == hd
        them("commit trong LOCK", "✅" if ok else "❌",
             f"pid {h['pid']} commit {str(h.get('commit'))[:12]} {'==' if ok else '≠'} HEAD {str(hd)[:12]}"
             + ("" if ok else " — runner chạy mã khác HEAD; --ensure sẽ từ chối"))

    # --- quyền ghi + đĩa --------------------------------------------------------
    rd = REPO / "docs/benchmark/runner"
    try:
        rd.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=rd, delete=True) as f:
            f.write(b"x")
        them("quyền ghi docs/benchmark/runner", "✅", "ghi được")
    except Exception as exc:
        them("quyền ghi", "❌", str(exc))
    free_gb = shutil.disk_usage(REPO).free / 1e9
    them("đĩa trống", "✅" if free_gb > 5 else "⚠", f"{free_gb:.1f} GB")

    for ok, muc, ct in kq:
        print(f"{ok} {muc:34s} {ct}")
    return 1 if any(ok == "❌" for ok, _, _ in kq) else 0
