r"""Executor THẬT cho M1–M4. Mỗi executor: `run(task) -> payload`, `manifest(task)`,
tuỳ chọn `ready(task)`.

Các bench cũ là THƯ VIỆN ở đây — import hàm, không chạy script. Lý do giữ đúng đường mã
cũ: số pilot (31/23/30) đo bằng chính các hàm này; đổi đường mã là đổi phép đo.

## Hai thứ runner cần mà các handler cũ không đưa ra

`GeminiLLMHandler` và `GeminiAudioSTT` không trả `usage_metadata`, và NUỐT lỗi API
(STT trả ("", None); LLM trả câu dự phòng). Với một mẻ đo, lượt nuốt lỗi là một bản ghi
"ok" SAI, và thiếu usage thì trần 5 USD không đếm được. Nên mỗi executor gắn một `Tap`
vào `client.models` của handler: đếm token theo modality, giữ text thô model trả về
(artefact M2 — lời thoại sau xử lý thay `[lookup]` bằng câu hằng số, nên KHÔNG dùng được
làm artefact), ghi `model_version`, và giữ lỗi. Lỗi có mặt ⇒ executor ném ⇒ runner ghi
vào file lỗi và thử lại. Không sửa handler.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

DESKTOP = Path(__file__).resolve().parents[1]
REPO = DESKTOP.parent
for p in (DESKTOP, DESKTOP / "scripts", REPO / "study" / "langconf"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

OLLAMA = "http://127.0.0.1:11434"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


_SHA: dict[str, str] = {}


def _sha_cache(p: Path) -> str:
    """model.bin 1,6 GB: băm MỘT lần mỗi tiến trình, không phải mỗi task."""
    k = str(p)
    if k not in _SHA:
        _SHA[k] = sha256_file(p)
    return _SHA[k]


def so_luong() -> int:
    return max(2, (os.cpu_count() or 4) - 2)


def an_cua_so() -> dict:
    """kwargs cho subprocess: runner chạy bằng pythonw (không console), nên MỌI tiến trình con
    kiểu console (git, ollama) tự mở cửa sổ console mới ⇒ màn hình chớp mỗi task. Bắt buộc."""
    if os.name != "nt":
        return {}
    import subprocess
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0                                    # SW_HIDE
    return {"creationflags": subprocess.CREATE_NO_WINDOW, "startupinfo": si}


_COMMIT: list[str] = []


def commit_repo() -> str:
    """Commit lúc tiến trình khởi động — mã đang chạy là mã đã nạp lúc ấy. Gọi git MỘT lần
    mỗi tiến trình, không phải mỗi task."""
    if not _COMMIT:
        try:
            import subprocess
            _COMMIT.append(subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                                          capture_output=True, text=True, timeout=10,
                                          stdin=subprocess.DEVNULL, **an_cua_so()).stdout.strip())
        except Exception:
            return ""
    return _COMMIT[0]


class ApiError(Exception):
    def __init__(self, msg: str, usage: dict | None = None) -> None:
        super().__init__(msg)
        self.usage = usage


# ---------------------------------------------------------------------------
class Tap:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.usage = {"in_text": 0, "in_audio": 0, "out": 0, "grounded": 0}
        self.raw: list[str] = []
        self.versions: set[str] = set()
        self.errors: list[str] = []
        self.calls = 0
        self.quota_headers: dict[str, str] = {}

    def _add(self, um: Any) -> None:
        if um is None:
            return
        prompt = (um.prompt_token_count or 0) + (getattr(um, "tool_use_prompt_token_count", 0) or 0)
        audio = 0
        for d in (getattr(um, "prompt_tokens_details", None) or []):
            if "AUDIO" in str(getattr(d, "modality", "")).upper():
                audio += d.token_count or 0
        self.usage["in_audio"] += audio
        self.usage["in_text"] += prompt - audio
        self.usage["out"] += (um.candidates_token_count or 0) + (getattr(um, "thoughts_token_count", 0) or 0)

    def gan(self, client: Any) -> None:
        models = client.models
        goc_gc, goc_st = models.generate_content, models.generate_content_stream
        tap = self

        def co_search(kw: dict) -> bool:
            cfg = kw.get("config")
            return any(getattr(t, "google_search", None) is not None
                       for t in (getattr(cfg, "tools", None) or []))

        def gc(*a, **kw):
            tap.calls += 1
            try:
                r = goc_gc(*a, **kw)
            except Exception as exc:
                tap.errors.append(f"{type(exc).__name__}: {exc}"[:400])
                raise
            if co_search(kw):
                tap.usage["grounded"] += 1
                h = getattr(getattr(r, "sdk_http_response", None), "headers", None) or {}
                tap.quota_headers = {k: v for k, v in dict(h).items()
                                     if any(x in k.lower() for x in ("quota", "ratelimit", "rate-limit", "limit", "tier"))}
            tap._add(getattr(r, "usage_metadata", None))
            if getattr(r, "model_version", None):
                tap.versions.add(r.model_version)
            return r

        def st(*a, **kw):
            tap.calls += 1
            try:
                it = goc_st(*a, **kw)
            except Exception as exc:
                tap.errors.append(f"{type(exc).__name__}: {exc}"[:400])
                raise

            def gen():
                last = None
                try:
                    for ch in it:
                        last = getattr(ch, "usage_metadata", None) or last
                        if getattr(ch, "model_version", None):
                            tap.versions.add(ch.model_version)
                        try:
                            tap.raw.append(ch.text or "")
                        except Exception:
                            pass
                        yield ch
                except Exception as exc:
                    tap.errors.append(f"{type(exc).__name__}: {exc}"[:400])
                    raise
                finally:
                    tap._add(last)
            return gen()

        models.generate_content = gc
        models.generate_content_stream = st

    def kiem(self) -> None:
        if self.errors:
            raise ApiError(self.errors[0], usage=dict(self.usage))


def _loi_api_tu_chuoi(err: str | None, usage: dict | None = None) -> None:
    if err:
        raise ApiError(err, usage=usage)


# ---------------------------------------------------------------------------
def _cfg():
    from config import Config
    return Config.load()


def _persona_prompt(cfg) -> str:
    from brain.persona import load_persona
    return load_persona(cfg.persona_path).system_prompt()


class M1Hosted:
    """`gemini-2.5-flash` audio. Nhiệt độ theo task (0.0 chính, 1.0 probe)."""

    def __init__(self, dau_vao) -> None:
        self.dau_vao = dau_vao
        self._stt: dict[float, Any] = {}

    def ready(self, t: dict) -> bool:
        return self.dau_vao.wav(t) is not None

    def _get(self, temp: float):
        if temp not in self._stt:
            from handlers.stt_gemini import GeminiAudioSTT
            cfg = _cfg()
            stt = GeminiAudioSTT(api_key=cfg.gemini_api_key, model=cfg.gemini_model, timeout_s=15.0)
            if temp != 0.0:
                goc = stt._config

                def _config(force_language=None, _g=goc, _t=temp):
                    c = _g(force_language)
                    c.temperature = _t
                    return c
                stt._config = _config
            tap = Tap()
            tap.gan(stt.client)
            self._stt[temp] = (stt, tap, cfg.gemini_model)
        return self._stt[temp]

    def manifest(self, t: dict) -> dict:
        cfg = _cfg()
        return {"kind": "m1_hosted", "model_alias_gui": cfg.gemini_model,
                "tham_so_gui": {"temperature": t["params"]["temperature"], "thinking_budget": 0,
                                "response_mime_type": "application/json", "timeout_s": 15.0},
                "prompt_sha256": hashlib.sha256(__import__("handlers.stt_gemini", fromlist=["PROMPT"])
                                                .PROMPT.encode()).hexdigest(),
                "xac_nhan_toi_model": "temperature: probe M1|rv1_*|gemini@t1.0 (xem prereg)",
                "commit": commit_repo()}

    def run(self, t: dict) -> dict:
        from audio_wav import read_wav
        stt, tap, alias = self._get(float(t["params"]["temperature"]))
        wav = self.dau_vao.wav(t)
        audio = read_wav(wav)
        tap.reset()
        t0 = time.perf_counter()
        text, lang = stt.transcribe(audio)
        ms = (time.perf_counter() - t0) * 1000
        _loi_api_tu_chuoi(stt.last_error or (tap.errors[0] if tap.errors else None), dict(tap.usage))
        return {"hypothesis": text, "language": lang, "model_alias": alias,
                "model_version": stt.last_model_version, "response_id": stt.last_response_id,
                "stt_ms": round(ms, 1), "audio_s": round(len(audio) / 16000, 2),
                "wav": wav.name, "wav_sha256": sha256_file(wav), "usage": dict(tap.usage)}


class M1Local:
    """`faster-whisper large-v3-turbo`, CPU int8, temperature ghim (0.8 cho probe)."""

    REPO_ID = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
    SPEC = {"label": "large-v3-turbo", "model": REPO_ID, "vi_model": None, "backend": "base"}

    def __init__(self, dau_vao) -> None:
        self.dau_vao = dau_vao
        self._stt = None

    def ready(self, t: dict) -> bool:
        return self.dau_vao.wav(t) is not None

    def _spec(self) -> dict:
        """A05: nạp bằng ĐƯỜNG DẪN snapshot của revision ghim — không có alias `main`, không mạng."""
        from mrunner import hf_pin
        return {**self.SPEC, "model": str(hf_pin.snapshot(self.REPO_ID))}

    def manifest(self, t: dict) -> dict:
        from mrunner import hf_pin
        snap = hf_pin.snapshot(self.REPO_ID)
        return {"kind": "m1_local", "model": self.SPEC["model"],
                "hf_pin": hf_pin.mo_ta(self.REPO_ID),
                "model_path_nap": str(snap),
                "model_bin_sha256": _sha_cache((snap / "model.bin").resolve()),
                "tham_so_gui": {"temperature": t["params"]["temperature"], "beam_size": 1,
                                "compute_type": "int8", "device": "cpu",
                                "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS")},
                "xac_nhan_toi_model": "temperature: probe M1|rv1_*|whisper@t0.8",
                "commit": commit_repo()}

    def run(self, t: dict) -> dict:
        from audio_wav import read_wav
        if self._stt is None:
            import rescore_utts
            self._stt, _ = rescore_utts.build_candidate(_cfg(), self._spec(), deterministic=True)
        stt = self._stt
        wav = self.dau_vao.wav(t)
        audio = read_wav(wav)
        temp = float(t["params"]["temperature"])
        goc = stt.gen_kwargs
        stt.gen_kwargs = {**goc, "temperature": temp}
        stt.last_language = None
        try:
            t0 = time.perf_counter()
            heard = stt.transcribe_audio(audio, backend="base")
            ms = (time.perf_counter() - t0) * 1000
        finally:
            stt.gen_kwargs = goc
        from mrunner import hf_pin
        model = heard["model"]
        if model == str(hf_pin.snapshot(self.REPO_ID)):        # A05: nhãn repo@revision thay đường dẫn máy
            model = f"{self.REPO_ID}@{hf_pin.PIN[self.REPO_ID]['revision']}"
        return {"hypothesis": heard["text"], "language": heard["language"],
                "language_p": heard.get("language_p"), "model": model,
                "stt_ms": round(ms, 1), "audio_s": round(len(audio) / 16000, 2),
                "wav": wav.name, "wav_sha256": sha256_file(wav)}


class DauVaoM1:
    """WAV của một task M1. Tầng chính (rv1 + rv2 + probe) chỉ sẵn sàng khi ĐỦ 69 WAV rv2
    đúng tên `rv2_sNN_rK.wav` — để n = 100 chạy cùng một đợt, không phải 31 hôm nay 69 tuần sau.
    Tầng in-the-wild chạy ngay."""

    def __init__(self, plan: dict) -> None:
        self.plan = plan
        self._du_rv2_luc = 0.0
        self._du_rv2 = False

    def du_rv2(self) -> bool:
        if not self._du_rv2 and time.time() - self._du_rv2_luc > 30:
            self._du_rv2_luc = time.time()
            self._du_rv2 = all((REPO / w).exists() for w in self.plan["m1"]["rv2_wavs"])
        return self._du_rv2

    def wav(self, t: dict) -> Path | None:
        p = t["params"]
        if p.get("tang") in ("chinh", "probe") and not self.du_rv2():
            return None
        f = REPO / p["wav"]
        return f if f.exists() else None


# ---------------------------------------------------------------------------
class M2Hosted:
    def __init__(self) -> None:
        self._vit: dict[float, Any] = {}

    def _get(self, temp: float):
        if temp not in self._vit:
            import bench_routing
            cfg = _cfg()
            vit = bench_routing.Vit(cfg, _persona_prompt(cfg), temperature=temp)
            tap = Tap()
            tap.gan(vit.handler.client)
            self._vit[temp] = (vit, tap, cfg.gemini_model)
        return self._vit[temp]

    def manifest(self, t: dict) -> dict:
        cfg = _cfg()
        return {"kind": "m2_hosted", "model_alias_gui": cfg.gemini_model,
                "tham_so_gui": {"temperature": t["params"]["temperature"], "thinking_budget": 0,
                                "max_output_tokens": 400, "search_enabled": False,
                                "history": "rỗng mỗi câu"},
                "system_prompt_sha256": hashlib.sha256(_persona_prompt(cfg).encode()).hexdigest(),
                "xac_nhan_toi_model": "temperature: ô 0.8 phải đổi text nhiều hơn ô 0.0",
                "commit": commit_repo()}

    def run(self, t: dict) -> dict:
        vit, tap, alias = self._get(float(t["params"]["temperature"]))
        vit.quen()
        tap.reset()
        ra = vit.hoi(t["params"]["question"], t["params"]["lang"])
        tap.kiem()
        return {"lookup": ra["lookup"], "premise": ra["premise"], "raw_text": "".join(tap.raw),
                "reply": ra["reply"], "llm_ms": ra["llm_ms"], "model_alias": alias,
                "model_versions": sorted(tap.versions), "usage": dict(tap.usage)}


def ollama_song() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA + "/api/version", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def dam_bao_ollama(cho_s: float = 60.0) -> None:
    if ollama_song():
        return
    import subprocess
    kw = an_cua_so()
    if os.name == "nt":
        # CREATE_NO_WINDOW thay DETACHED_PROCESS: ollama có console ẨN, nên runner con của nó
        # thừa hưởng console ấy thay vì tự mở cửa sổ mới. Hai cờ loại trừ nhau.
        kw["creationflags"] |= subprocess.CREATE_NEW_PROCESS_GROUP | 0x00004000
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, **kw)
    han = time.time() + cho_s
    while time.time() < han:
        if ollama_song():
            return
        time.sleep(2)
    raise ApiError("ollama không sống sau khi tự bật `ollama serve`")


def ollama_digest(model: str) -> str | None:
    with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=10) as r:
        for m in json.load(r).get("models", []):
            if m.get("name") == model or m.get("model") == model:
                return m.get("digest")
    return None


def ha_uu_tien_ollama() -> None:
    """Tiến trình ollama chạy model ở BELOW_NORMAL — nhường máy cho chủ nhân."""
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            if (p.info["name"] or "").lower().startswith("ollama"):
                try:
                    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                except Exception:
                    pass
    except Exception:
        pass


def ollama_chat(model: str, messages: list[dict], options: dict, timeout: float) -> dict:
    payload = {"model": model, "messages": messages, "stream": False, "think": False,
               "options": {**options, "num_thread": so_luong()}}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


class OllamaExec:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._digest: dict[str, tuple[float, str | None]] = {}

    def digest(self, model: str) -> str | None:
        c = self._digest.get(model)
        if c is None or time.time() - c[0] > 600:
            dam_bao_ollama()
            c = (time.time(), ollama_digest(model))
            self._digest[model] = c
        return c[1]

    def manifest(self, t: dict) -> dict:
        p = t["params"]
        return {"kind": self.kind, "model_alias_gui": p["model"], "digest": self.digest(p["model"]),
                "tham_so_gui": {**p["options"], "think": False, "num_thread": so_luong()},
                "xac_nhan_toi_model": "seed/temperature: probe @seed1 và @t08 (xem prereg)",
                "commit": commit_repo()}

    def _chat(self, t: dict, messages: list[dict], timeout: float) -> dict:
        p = t["params"]
        dam_bao_ollama()
        ha_uu_tien_ollama()
        d = self.digest(p["model"])
        if d is None:
            raise ApiError(f"ollama không có model {p['model']}")
        t0 = time.perf_counter()
        r = ollama_chat(p["model"], messages, p["options"], timeout)
        return {"text": (r.get("message") or {}).get("content", ""), "digest": d,
                "model_tra_ve": r.get("model"), "done_reason": r.get("done_reason"),
                "in_tokens": r.get("prompt_eval_count"), "out_tokens": r.get("eval_count"),
                "ms": round((time.perf_counter() - t0) * 1000, 1)}


class M2Local(OllamaExec):
    def __init__(self) -> None:
        super().__init__("m2_local")
        self._prompt = None

    def manifest(self, t: dict) -> dict:
        m = super().manifest(t)
        m["system_prompt_sha256"] = hashlib.sha256(self._sp().encode()).hexdigest()
        return m

    def _sp(self) -> str:
        if self._prompt is None:
            self._prompt = _persona_prompt(_cfg())
        return self._prompt

    def run(self, t: dict) -> dict:
        from handlers.llm_gemini import peek_tags
        p = t["params"]
        r = self._chat(t, [{"role": "system", "content": self._sp()},
                           {"role": "user", "content": p["question"]}], timeout=300)
        text = r.pop("text")                  # pop TRƯỚC khi bung r, không thì text ghi hai lần
        tags = peek_tags(text) or (False, False)
        return {**r, "raw_text": text, "lookup": tags[0], "premise": tags[1]}


class M4Local(OllamaExec):
    def __init__(self) -> None:
        super().__init__("m4_local")
        self._lid = None

    def run(self, t: dict) -> dict:
        p = t["params"]
        r = self._chat(t, p["messages"], timeout=900)
        if self._lid is None:
            from langconf.langid import DualLangID
            self._lid = DualLangID(REPO / "study/langconf/data/lid/lid.176.bin")
        text = r.pop("text").strip()          # OllamaBackend strip() — giữ đúng như pilot
        return {**r, "reply_text": text, "lang_label": self._lid.detect(text).fasttext}


# ---------------------------------------------------------------------------
class M3Hosted:
    def __init__(self) -> None:
        self._vit: dict[bool, Any] = {}

    def _get(self, search: bool):
        if search not in self._vit:
            import bench_grounding_stability as bgs
            cfg = _cfg()
            vit = bgs.Vit(cfg, _persona_prompt(cfg))
            if not search:
                vit.handler.set_search_enabled(False)
            tap = Tap()
            tap.gan(vit.handler.client)
            self._vit[search] = (vit, tap, cfg.gemini_model)
        return self._vit[search]

    def manifest(self, t: dict) -> dict:
        cfg = _cfg()
        return {"kind": "m3", "model_alias_gui": cfg.gemini_model,
                "tham_so_gui": {"temperature": 0.8, "thinking_budget": 0, "max_output_tokens": 400,
                                "search_enabled": t["params"]["search"], "search_timeout_s": 6.0,
                                "history": "rỗng mỗi câu"},
                "system_prompt_sha256": hashlib.sha256(_persona_prompt(cfg).encode()).hexdigest(),
                "xac_nhan_toi_model": "search: probe nosearch phải cho n_sources = 0",
                "commit": commit_repo()}

    def run(self, t: dict) -> dict:
        vit, tap, alias = self._get(bool(t["params"]["search"]))
        vit.quen()
        tap.reset()
        ra = vit.hoi(t["params"]["question"], t["params"]["lang"])
        tap.kiem()
        return {**ra, "model_alias": alias, "model_versions": sorted(tap.versions),
                "quota_headers": tap.quota_headers, "usage": dict(tap.usage)}


class _MotWav:
    def __init__(self, wav: Path) -> None:
        self._wav = wav

    def wav(self, t: dict) -> Path:
        return self._wav


class M6Run:
    """M6 (A04.3): một lần chạy = gọi pipeline MỘT lần mỗi input (STT + routing, hosted + local)
    bằng đúng các executor M1/M2, ghi obs, rồi chạy hai bộ pytest oracle trên obs ấy so golden
    (obs của lần chạy 1, đọc từ file kết quả M6). Lỗi API ở bất kỳ input nào ⇒ ném ⇒ runner thử lại
    cả lần chạy (không có obs nửa vời)."""

    def __init__(self, plan: dict, m1h: M1Hosted, m1l: M1Local, m2h: M2Hosted, m2l: M2Local) -> None:
        self.plan, self.m1h, self.m1l, self.m2h, self.m2l = plan, m1h, m1l, m2h, m2l
        self._lid = None

    def _lang(self, text: str) -> str | None:
        if self._lid is None:
            from langconf.langid import DualLangID
            self._lid = DualLangID(REPO / "study/langconf/data/lid/lid.176.bin")
        from mrunner.oracle import bo_the
        t = bo_the(text)
        return self._lid.detect(t).fasttext if t else None

    def manifest(self, t: dict) -> dict:
        p = t["params"]
        return {"kind": "m6_run", "stt_hosted": self.m1h.manifest({"params": {"temperature": 0.0}}),
                "stt_local": self.m1l.manifest({"params": {"temperature": 0.0}}),
                "routing_hosted": self.m2h.manifest({"params": {"temperature": p["routing_hosted_temperature"]}}),
                "routing_local": self.m2l.manifest({"params": {"model": p["routing_local"]["model"],
                                                               "options": p["routing_local"]["options"]}}),
                "stt_inputs_sha256": {i["id"]: i["wav_sha256"] for i in p["stt"]},
                "suites": {s: sha256_file(DESKTOP / f"tests/{s}/test_{s}.py")
                           for s in ("oracle_decision", "oracle_artefact")},
                "oracle_py": sha256_file(DESKTOP / "mrunner/oracle.py"), "commit": commit_repo()}

    def _golden(self, t: dict) -> tuple[str, dict] | None:
        from mrunner.core import Store
        recs, _ = Store(REPO / self.plan["results"]["M6"]).read()
        ok = sorted((r for r in recs if r.get("status") == "ok"), key=lambda r: r["ts"])
        return (ok[0]["task_id"], ok[0]["payload"]["obs"]) if ok else None

    def run(self, t: dict) -> dict:
        import subprocess
        import tempfile
        import xml.etree.ElementTree as ET
        p = t["params"]
        obs: dict = {"stt": {"hosted": {}, "local": {}}, "routing": {"hosted": {}, "local": {}}}
        goc_h, goc_l = self.m1h.dau_vao, self.m1l.dau_vao
        try:
            for i in p["stt"]:
                wav = REPO / i["wav"]
                if sha256_file(wav) != i["wav_sha256"]:
                    raise ApiError(f"S3 {i['id']} lệch SHA-256 — đầu vào không còn byte-cố định")
                sub = {"params": {"wav": i["wav"], "temperature": 0.0}}
                self.m1h.dau_vao = self.m1l.dau_vao = _MotWav(wav)
                h = self.m1h.run(sub)
                obs["stt"]["hosted"][i["id"]] = {"text": h["hypothesis"], "language": h["language"],
                                                "model_version": h.get("model_version")}
                loc = self.m1l.run(sub)
                obs["stt"]["local"][i["id"]] = {"text": loc["hypothesis"], "language": loc["language"]}
        finally:
            self.m1h.dau_vao, self.m1l.dau_vao = goc_h, goc_l
        for q in p["routing"]:
            h = self.m2h.run({"params": {"question": q["question"], "lang": q["lang"],
                                         "temperature": p["routing_hosted_temperature"]}})
            obs["routing"]["hosted"][q["id"]] = {"raw_text": h["raw_text"], "lookup": h["lookup"],
                                                "reply_lang": self._lang(h["raw_text"]),
                                                "model_versions": h.get("model_versions")}
            loc = self.m2l.run({"params": {"question": q["question"], **p["routing_local"]}})
            obs["routing"]["local"][q["id"]] = {"raw_text": loc["raw_text"], "lookup": loc["lookup"],
                                               "reply_lang": self._lang(loc["raw_text"])}
        g = self._golden(t)
        golden_id, golden = g if g else (t["id"], obs)          # chưa có lần ok nào: lần này là golden
        with tempfile.TemporaryDirectory() as d:
            fo, fg, fx = Path(d) / "obs.json", Path(d) / "golden.json", Path(d) / "junit.xml"
            fo.write_text(json.dumps(obs, ensure_ascii=False), encoding="utf-8")
            fg.write_text(json.dumps(golden, ensure_ascii=False), encoding="utf-8")
            from mrunner import hf_pin
            env = {**os.environ, **hf_pin.BIEN, "MICRODUCK_ORACLE_RUN": str(fo),
                   "MICRODUCK_ORACLE_GOLDEN": str(fg), "PYTHONIOENCODING": "utf-8"}
            exe = Path(sys.executable)
            py = exe.with_name("python.exe") if exe.name.lower() == "pythonw.exe" else exe
            r = subprocess.run([str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={fx}",
                                "tests/oracle_decision", "tests/oracle_artefact"],
                               cwd=str(DESKTOP), env=env, capture_output=True, text=True, timeout=600,
                               stdin=subprocess.DEVNULL, **an_cua_so())
            if not fx.exists():
                raise ApiError(f"pytest oracle không ra junit (rc={r.returncode}): {r.stdout[-300:]}")
            tests = {}
            for tc in ET.parse(fx).getroot().iter("testcase"):
                bo = "decision" if "oracle_decision" in tc.get("classname", "") else "artefact"
                kq = "failed" if tc.find("failure") is not None or tc.find("error") is not None else \
                    ("skipped" if tc.find("skipped") is not None else "passed")
                tests[f"{bo}::{tc.get('name')}"] = kq
        n_mong = 2 * sum(len(golden[s][b]) for s in golden for b in golden[s])
        if len(tests) != n_mong:
            raise ApiError(f"pytest oracle ra {len(tests)} test, cần {n_mong}")
        return {"lan": p["lan"], "golden_task": golden_id, "obs": obs, "tests": tests,
                "pytest_rc": r.returncode,
                "n_fail": {b: sum(1 for k, v in tests.items() if k.startswith(b) and v != "passed")
                           for b in ("decision", "artefact")}}


def executors(plan: dict) -> dict[str, Any]:
    dv = DauVaoM1(plan)
    ex = {"m1_hosted": M1Hosted(dv), "m1_local": M1Local(dv), "m2_hosted": M2Hosted(),
          "m2_local": M2Local(), "m3": M3Hosted(), "m4_local": M4Local()}
    if "M6" in plan.get("results", {}):
        # dùng CHUNG executor (một bản model whisper trong RAM); M6Run đổi `dau_vao` trong lần chạy
        # rồi trả lại — runner đơn luồng nên không task nào khác thấy trạng thái tạm ấy
        ex["m6_run"] = M6Run(plan, ex["m1_hosted"], ex["m1_local"], ex["m2_hosted"], ex["m2_local"])
    return ex
