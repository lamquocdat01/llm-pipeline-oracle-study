r"""Hai cách vận hành một stage: HOSTED (gemini-2.5-flash, nhà cung cấp vận hành) và LOCAL (Ollama, ghim hash).

Mỗi lời gọi trả `{"text", "usage", "model_version"|"digest", ...}`. `usage` theo đúng khoá của
`mrunner.core.gia_usd` (`in_text`, `in_audio`, `out`, `grounded`) để trần USD của runner đếm được.
Lỗi API ⇒ NÉM (runner ghi vào file lỗi và thử lại) — không trả câu dự phòng thành bản ghi "ok".
"""
from __future__ import annotations

import os
from pathlib import Path

from . import REPO

HOSTED_MODEL = "gemini-2.5-flash"
LOCAL_MODEL = "qwen2.5:3b"
THIRD_MODEL = "llama3.1:8b"          # N3: họ thứ 3 (Meta), quyết định anh Đạt 01-11
MAX_OUT = 400


def _key() -> str:
    """GEMINI_API_KEY từ env, hoặc `.env` gốc repo (dòng có thể mang chú thích sau `#`)."""
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        return k
    for d in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        if d.startswith("GEMINI_API_KEY="):
            v = d.split("=", 1)[1].split("#", 1)[0].strip().strip('"').split()
            if v and v[0].isascii():
                return v[0]
    raise RuntimeError("không có GEMINI_API_KEY")


_CLIENT = None


def _client():
    global _CLIENT
    if _CLIENT is None:
        from google import genai
        _CLIENT = genai.Client(api_key=_key())
    return _CLIENT


def hosted(prompt: str, temperature: float, grounded: bool = False) -> dict:
    from google.genai import types
    tools = [types.Tool(google_search=types.GoogleSearch())] if grounded else None
    cfg = types.GenerateContentConfig(temperature=temperature, max_output_tokens=MAX_OUT, tools=tools,
                                      thinking_config=types.ThinkingConfig(thinking_budget=0))
    r = _client().models.generate_content(model=HOSTED_MODEL, contents=prompt, config=cfg)
    um = r.usage_metadata
    # Token kết quả tìm kiếm (tool_use_prompt) tính giá INPUT; thinking tính giá OUTPUT (trang giá 30-10-2026).
    usage = {"in_text": (um.prompt_token_count or 0) + (getattr(um, "tool_use_prompt_token_count", None) or 0),
             "in_audio": 0, "out": (um.candidates_token_count or 0) + (um.thoughts_token_count or 0),
             "grounded": 1 if grounded else 0}
    ra = {"text": r.text or "", "usage": usage, "model_alias": HOSTED_MODEL, "model_version": r.model_version,
          "finish_reason": str(r.candidates[0].finish_reason) if r.candidates else None}
    if grounded:
        gm = r.candidates[0].grounding_metadata if r.candidates else None
        chunks = (gm.grounding_chunks or []) if gm else []
        ra["sources"] = [{"title": c.web.title, "uri": c.web.uri} for c in chunks if c.web]
        ra["queries"] = list((gm.web_search_queries or []) if gm else [])
    if not ra["text"].strip():
        raise RuntimeError(f"hosted trả rỗng (finish_reason={ra['finish_reason']})")
    return ra


# AMENDMENT V2-06: nhánh đối chứng P3H, cùng model Llama 3.1 8B nhưng delegated (TOGETHER_MODEL_NOTE.md).
HOSTED_LLAMA_MODEL = "meta-llama/llama-3.1-8b-instruct"
HOSTED_LLAMA_SLUG = "deepinfra/fp8"
HOSTED_LLAMA_PROVIDER = "DeepInfra"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def key_openrouter() -> str | None:
    """OPENROUTER_API_KEY từ env hoặc `.env` gốc repo; không có thì None. Không bao giờ in hay ghi giá trị này."""
    k = os.environ.get("OPENROUTER_API_KEY")
    if k and k.strip():
        return k.strip()
    p = REPO / ".env"
    if not p.exists():
        return None
    for d in p.read_text(encoding="utf-8").splitlines():
        if d.strip().startswith("OPENROUTER_API_KEY") and "=" in d:
            v = d.split("=", 1)[1].split("#", 1)[0].strip().strip('"').split()
            if v and v[0].isascii():
                return v[0]
    return None


def openrouter(prompt: str, temperature: float, seed: int = 0) -> dict:
    """Một lời gọi P3H. Ghim đúng endpoint, tắt fallback: endpoint lỗi thì task lỗi, không rơi sang provider khác."""
    import json
    import urllib.error
    import urllib.request
    from mrunner.core import RateLimited
    k = key_openrouter()
    if not k:
        raise RuntimeError("không có OPENROUTER_API_KEY")
    body = {"model": HOSTED_LLAMA_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": temperature,
            "seed": seed, "max_tokens": MAX_OUT,
            "provider": {"order": [HOSTED_LLAMA_SLUG], "allow_fallbacks": False, "require_parameters": True}}
    req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(body).encode("utf-8"), method="POST", headers={
        "Authorization": f"Bearer {k}", "Content-Type": "application/json",
        "User-Agent": "microduck-p3h (noreply@example.org)", "X-OpenRouter-Metadata": "enabled"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        than = e.read(300).decode("utf-8", "replace")
        if e.code == 429:
            ra = e.headers.get("Retry-After")
            raise RateLimited(f"429 {than}", float(ra) if ra and ra.isdigit() else None) from None
        raise RuntimeError(f"HTTP {e.code}: {than}") from None
    if d.get("error"):                                  # OpenRouter có thể trả lỗi trong thân của HTTP 200
        raise RuntimeError(f"openrouter error: {str(d['error'])[:300]}")
    ten = d.get("provider")
    if ten and ten != HOSTED_LLAMA_PROVIDER:
        raise RuntimeError(f"provider {ten} ≠ ghim {HOSTED_LLAMA_PROVIDER}")
    u = d.get("usage")
    if not u:
        raise RuntimeError("openrouter không trả usage")   # trần USD dựa vào usage: không ghi bản ghi ok thiếu nó
    ch = (d.get("choices") or [{}])[0]
    text = (ch.get("message") or {}).get("content") or ""
    if not text.strip():
        raise RuntimeError(f"openrouter trả rỗng (finish_reason={ch.get('finish_reason')})")
    return {"text": text, "model_alias": HOSTED_LLAMA_MODEL, "model_version": d.get("model"), "provider": ten,
            "finish_reason": ch.get("finish_reason"), "native_finish_reason": ch.get("native_finish_reason"),
            "gen_id": d.get("id"), "system_fingerprint": d.get("system_fingerprint"),
            "openrouter_metadata": d.get("openrouter_metadata"),
            "tham_so": {"temperature": temperature, "seed": seed, "max_tokens": MAX_OUT, "slug": HOSTED_LLAMA_SLUG},
            "usage": {"in_text": u.get("prompt_tokens") or 0, "in_audio": 0, "out": u.get("completion_tokens") or 0,
                      "grounded": 0, "nha": "openrouter", "cost": u.get("cost")}}


def local(prompt: str, temperature: float, seed: int = 0, model: str = LOCAL_MODEL) -> dict:
    from mrunner.thuc import dam_bao_ollama, ha_uu_tien_ollama, ollama_chat, ollama_digest, so_luong
    from .pin import kiem
    dam_bao_ollama()
    ha_uu_tien_ollama()
    d = ollama_digest(model)
    loi = kiem(model, d)
    if loi:
        raise RuntimeError("; ".join(loi))
    opt = {"temperature": temperature, "seed": seed, "num_predict": MAX_OUT}
    r = ollama_chat(model, [{"role": "user", "content": prompt}], opt, timeout=900)
    return {"text": (r.get("message") or {}).get("content", ""), "usage": None, "model_alias": model,
            "digest": d, "tham_so": {**opt, "num_thread": so_luong(), "think": False},
            "eval_count": r.get("eval_count"), "prompt_eval_count": r.get("prompt_eval_count")}
