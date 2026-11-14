r"""Sinh `plan.json` từ prereg — MỘT lần, commit trước khi chạy.

Mọi lựa chọn ngẫu nhiên có seed ghi trong plan; danh sách item ghi tường minh (không
glob lúc chạy), nên hai máy cùng plan chạy đúng một tập task.
"""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from mrunner.thuc import REPO, sha256_file

NGAY = "20260916"
RUNNER_DIR = "docs/benchmark/runner"
RV2_DIR = "desktop/logs/utts_rv2"
RV2_CAU = "docs/benchmark/M1_rv2_sentences.json"


def _m1_items() -> list[dict]:
    rv1 = json.loads((REPO / "docs/benchmark/stt_rescore_20260906_v3_fixed.json")
                     .read_text(encoding="utf-8"))["gemini-audio"]["utterances"]
    items = [{"utt": f"rv1_{i:03d}", "tang": "chinh", "wav": f"desktop/logs/utts/{u['wav']}",
              "reference": u["reference"], "reference_lang": u["reference_lang"]}
             for i, u in enumerate(rv1, 1)]
    assert len(items) == 31
    bo = json.loads((REPO / RV2_CAU).read_text(encoding="utf-8"))
    for c in bo["cau"]:
        for k in range(1, int(bo["lan_doc"]) + 1):
            ten = f"rv2_s{c['so']:02d}_r{k}"
            items.append({"utt": ten, "tang": "chinh", "wav": f"{RV2_DIR}/{ten}.wav",
                          "reference": c["text"], "reference_lang": c["lang"]})
    assert len(items) == 100
    pilot = {Path(i["wav"]).name for i in items if i.get("wav")}
    wild = sorted(p for p in (REPO / "desktop/logs/utts").glob("*.wav") if p.name not in pilot)
    items += [{"utt": f"wild_{p.stem}", "tang": "wild", "wav": f"desktop/logs/utts/{p.name}",
               "wav_sha256": sha256_file(p)} for p in wild]
    return items


def _m4_items() -> list[dict]:
    lc = REPO / "study/langconf/results"
    rows = [json.loads(l) for l in (lc / "main_qwen2.5-7b.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    rows = [r for r in rows if r.get("reply_text") and not r.get("model_error")]
    pilot = json.loads((lc / "rerun_check_qwen2.5-7b.json").read_text(encoding="utf-8"))
    # Loại 23 prompt pilot theo trial_key bằng cách TÁI LẬP phép lấy mẫu của rerun_check.py
    # (Random(seed).sample trên các dòng hợp lệ theo thứ tự file). Loại theo (probe_id,
    # reply) thì trúng 34 dòng: nhiều điều kiện khác nhau cho ra cùng một câu trả lời.
    mau = random.Random(pilot["seed"]).sample(rows, len(pilot["luot"]))
    assert [r["reply_text"] for r in mau] == [k["cu"] for k in pilot["luot"]], "không tái lập được mẫu pilot"
    pilot_keys = {r["trial_key"] for r in mau}
    con = sorted((r for r in rows if r["trial_key"] not in pilot_keys), key=lambda r: r["trial_key"])
    assert len(rows) - len(con) == 23
    rng = random.Random(20260916)
    chon: list[dict] = []
    for lang, n in (("en", 17), ("vi", 17), ("ko", 16)):
        chon += rng.sample([r for r in con if r["target_lang"] == lang], n)
    return [{"prompt_id": r["trial_key"], "target_lang": r["target_lang"],
             "messages": [{"role": m["role"], "content": m["content"]} for m in r["messages"]]}
            for r in chon]


S3_MANIFEST = "docs/benchmark/M1_s3_manifest.json"
M6_RESULTS = "docs/benchmark/M6_20260918_v1.jsonl"


def _m1_tasks(add, it: dict, extra: dict | None = None) -> None:
    """Bốn mốc × hai backend của một utterance M1 — cùng dạng id/cờ như `build` (luật 3 của core)."""
    src = {"wav": it["wav"], **(extra or {})}
    for be, kind, hosted in (("gemini", "m1_hosted", True), ("whisper", "m1_local", False)):
        base = f"M1|{it['utt']}|{be}"
        p = {**src, "tang": it["tang"], "temperature": 0.0}
        common = dict(m="M1", kind=kind, hosted=hosted, heavy=not hosted, order=4, params=p)
        add(id=f"{base}|t0|1", **common)
        add(id=f"{base}|t0p|1", after={"task": f"{base}|t0|1", "delta_s": 0}, **common)
        add(id=f"{base}|t180|1", after={"task": f"{base}|t0|1", "delta_s": 180},
            exempt_busy=True, **common)
        add(id=f"{base}|t24h|1", after={"task": f"{base}|t0|1", "delta_s": 86400}, **common)


def amend04(plan: dict) -> tuple[dict, list[dict]]:
    """AMENDMENT 04 trên plan ĐANG CHẠY. Trả (plan mới, các task bị huỷ).

    - Giữ NGUYÊN mọi task cũ (id, params, cờ) trừ 552 task rv2 — kể cả task đã có kết quả.
    - rv1 (tầng chính cũ) = S1: bỏ cổng "chờ đủ 69 WAV rv2" bằng `m1.rv2_wavs = []`.
    - Thêm S3 (mọi WAV `accepted` của manifest, SHA-256 ghim trong params) và M6 (20 lần chạy).
    - M7 KHÔNG có task: là phép chấm trên các file kết quả (A04.4).
    """
    if plan.get("amendment") == "04":
        raise ValueError("plan đã ở AMENDMENT 04")
    rv2_dir = plan["m1"]["rv2_dir"]
    huy = [t for t in plan["tasks"] if t["m"] == "M1" and t["params"].get("wav", "").startswith(rv2_dir + "/")]
    assert len(huy) == 552, f"cần đúng 552 task rv2, thấy {len(huy)}"
    huy_id = {t["id"] for t in huy}
    tasks = [t for t in plan["tasks"] if t["id"] not in huy_id]

    def add(**t):
        tasks.append(t)

    man = json.loads((REPO / S3_MANIFEST).read_text(encoding="utf-8"))
    s3 = [f for f in man["files"] if f["accepted"]]
    assert len(s3) >= 200, f"S3 chỉ có {len(s3)} WAV được nhận (< 200)"
    for f in s3:
        _m1_tasks(add, {"utt": Path(f["file"]).stem, "tang": "s3", "wav": f["file"]},
                  {"wav_sha256": f["sha256"]})

    from mrunner.oracle import LICH_GIO, LICH_NGAY, chon_routing, chon_stt
    stt, lech = chon_stt(man["files"])
    bo = [json.loads(l) for l in (REPO / "docs/benchmark/lookup_set_v1.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    routing = chon_routing([r for r in bo if r["block"] == "A"])
    p6 = {"stt": [{"id": Path(f["file"]).stem, "wav": f["file"], "wav_sha256": f["sha256"],
                   "lang": f["lang"], "voice": f["voice"]} for f in stt],
          "routing": [{"id": r["id"], "question": r["question"], "lang": r["lang"],
                       "needs_lookup": r["needs_lookup"]} for r in routing],
          "routing_hosted_temperature": 0.8,
          "routing_local": {"model": "qwen2.5:7b",
                            "options": {"temperature": 0, "seed": 20260912, "num_predict": 160}}}
    lan = 0
    for ngay in LICH_NGAY:
        for gio in LICH_GIO:
            lan += 1
            add(id=f"M6|lan{lan:02d}", m="M6", kind="m6_run", hosted=True, heavy=True, order=0,
                at=f"{ngay}T{gio}:00+07:00", khong_missed=True, cho_pause=True,
                params={**p6, "lan": lan})
    assert lan == 20

    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), "task_id trùng sau amend"
    moi = {**plan, "version": 2, "amendment": "04", "tasks": tasks,
           "results": {**plan["results"], "M6": M6_RESULTS},
           "m1": {**plan["m1"], "rv2_wavs": [],
                  "cho_tang_chinh": "AMENDMENT 04: rv2 huỷ; rv1 = S1 chạy ngay (không chờ)",
                  "s3_manifest": S3_MANIFEST, "s3_manifest_sha256": sha256_file(REPO / S3_MANIFEST)},
           "m6": {"lich": [t["at"] for t in tasks if t["m"] == "M6"], "chon_stt_lech": lech,
                  "n_stt": len(stt), "n_routing": len(routing)},
           "m7": "không có task runner — chấm trên file kết quả theo A04.4/A04.5"}
    return moi, huy


def build(m3_first: datetime) -> dict:
    tasks: list[dict] = []

    def add(**t):
        tasks.append(t)

    # ---- M4 (order 1) -----------------------------------------------------
    m4 = _m4_items()
    for it in m4:
        for model in ("qwen2.5:7b", "qwen2.5:3b"):
            base = f"M4|{it['prompt_id']}|{model}"
            p = {"model": model, "messages": it["messages"],
                 "options": {"temperature": 0.0, "seed": 0, "num_predict": 100}}
            add(id=f"{base}|t0|1", m="M4", kind="m4_local", heavy=True, order=1, params=p)
            add(id=f"{base}|t0p|1", m="M4", kind="m4_local", heavy=True, order=1, params=p,
                after={"task": f"{base}|t0|1", "delta_s": 0})
            add(id=f"{base}|t24h|1", m="M4", kind="m4_local", heavy=True, order=1, params=p,
                after={"task": f"{base}|t0|1", "delta_s": 86400})
    for it in m4[:10]:
        for model in ("qwen2.5:7b", "qwen2.5:3b"):
            for tag, opt in (("seed1", {"temperature": 0.0, "seed": 1, "num_predict": 100}),
                             ("t08", {"temperature": 0.8, "seed": 0, "num_predict": 100})):
                add(id=f"M4|{it['prompt_id']}|{model}@{tag}|probe|1", m="M4", kind="m4_local",
                    heavy=True, order=1,
                    params={"model": model, "messages": it["messages"], "options": opt},
                    after={"task": f"M4|{it['prompt_id']}|{model}|t0|1", "delta_s": 0})

    # ---- M2 (local order 2, hosted order 3) -------------------------------
    bo = [json.loads(l) for l in (REPO / "docs/benchmark/lookup_set_v1.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    khoi_a = sorted((r for r in bo if r["block"] == "A"), key=lambda r: r["id"])
    assert len(khoi_a) == 100
    arms = [("qwen2.5:7b", "m2_local", 2, False,
             {"options": {"temperature": 0, "seed": 20260912, "num_predict": 160}, "model": "qwen2.5:7b"}),
            ("gemini-t0", "m2_hosted", 3, True, {"temperature": 0.0}),
            ("gemini-t08", "m2_hosted", 3, True, {"temperature": 0.8})]
    for r in khoi_a:
        q = {"question": r["question"], "lang": r["lang"], "needs_lookup": r["needs_lookup"],
             "fact_type": r["fact_type"]}
        for name, kind, order, hosted, extra in arms:
            base = f"M2|{r['id']}|{name}"
            p = {**q, **extra}
            common = dict(m="M2", kind=kind, heavy=not hosted, hosted=hosted, order=order, params=p)
            add(id=f"{base}|t0", **common)
            add(id=f"{base}|t0p", after={"task": f"{base}|t0", "delta_s": 0}, **common)
            add(id=f"{base}|t24h", after={"task": f"{base}|t0", "delta_s": 86400}, **common)
        for tag, opt in (("seed1", {"temperature": 0, "seed": 1, "num_predict": 160}),
                         ("t08", {"temperature": 0.8, "seed": 20260912, "num_predict": 160})):
            add(id=f"M2|{r['id']}|qwen2.5:7b@{tag}|probe", m="M2", kind="m2_local", heavy=True,
                order=2, params={**q, "model": "qwen2.5:7b", "options": opt},
                after={"task": f"M2|{r['id']}|qwen2.5:7b|t0", "delta_s": 0})

    # ---- M1 (order 4) -----------------------------------------------------
    m1 = _m1_items()
    for it in m1:
        src = {"wav": it["wav"]}
        for be, kind, hosted in (("gemini", "m1_hosted", True), ("whisper", "m1_local", False)):
            base = f"M1|{it['utt']}|{be}"
            p = {**src, "tang": it["tang"], "temperature": 0.0}
            common = dict(m="M1", kind=kind, hosted=hosted, heavy=not hosted, order=4, params=p)
            add(id=f"{base}|t0|1", **common)
            add(id=f"{base}|t0p|1", after={"task": f"{base}|t0|1", "delta_s": 0}, **common)
            add(id=f"{base}|t180|1", after={"task": f"{base}|t0|1", "delta_s": 180},
                exempt_busy=True, **common)
            add(id=f"{base}|t24h|1", after={"task": f"{base}|t0|1", "delta_s": 86400}, **common)
        if it["utt"].startswith("rv1_"):
            for be, kind, hosted, temp in (("gemini@t1.0", "m1_hosted", True, 1.0),
                                           ("whisper@t0.8", "m1_local", False, 0.8)):
                bgoc = be.split("@")[0]
                add(id=f"M1|{it['utt']}|{be}|probe|1", m="M1", kind=kind, hosted=hosted,
                    heavy=not hosted, order=4,
                    params={**src, "tang": "probe", "temperature": temp},
                    after={"task": f"M1|{it['utt']}|{bgoc}|t0|1", "delta_s": 0})

    # ---- M3 (mốc tuyệt đối) -----------------------------------------------
    import sys
    sys.path.insert(0, str(REPO / "desktop" / "scripts"))
    import bench_grounding_stability as bgs
    m3_bo = bgs.chon_bo(bgs.doc_bo(), None)
    assert len(m3_bo) == 30
    lich = [m3_first + timedelta(hours=12 * k) for k in range(14)]
    for moc in lich:
        mi = moc.isoformat(timespec="minutes")
        for r in m3_bo:
            add(id=f"M3|{mi}|{r['id']}", m="M3", kind="m3", hosted=True, exempt_busy=True, order=0,
                at=moc.isoformat(), params={"question": r["question"], "lang": r["lang"],
                                            "fact_type": r["fact_type"], "search": True})
    for r in m3_bo[:5]:
        mi = lich[0].isoformat(timespec="minutes")
        add(id=f"M3|probe-nosearch|{r['id']}", m="M3", kind="m3", hosted=True, order=0,
            params={"question": r["question"], "lang": r["lang"], "fact_type": r["fact_type"],
                    "search": False},
            after={"task": f"M3|{mi}|{r['id']}", "delta_s": 0})

    return {
        "version": 1,
        "prereg": "docs/benchmark/PREREG_M1-M4_20260916.md",
        "runner_dir": RUNNER_DIR,
        "results": {m: f"docs/benchmark/{m}_{NGAY}_v1.jsonl" for m in ("M1", "M2", "M3", "M4")},
        "m1": {"rv2_dir": RV2_DIR, "rv2_cau": RV2_CAU,
               "rv2_wavs": [i["wav"] for i in m1 if i["utt"].startswith("rv2_")],
               "cho_tang_chinh": "mọi task tầng chính (rv1 + rv2 + probe) chờ đủ 69 WAV rv2"},
        "m3_lich": [d.isoformat() for d in lich],
        "late_missed_s": 7200,
        "budget_usd": 5.0,
        "price": {"model": "gemini-2.5-flash", "nguon": "ai.google.dev/gemini-api/docs/pricing (cập nhật 2026-09-15)",
                  "in_text": 0.30, "in_audio": 1.00, "out": 2.50,
                  "grounding_per_1000": 35.0, "grounding_free_per_day": None},
        "tasks": tasks,
    }


def amend08(plan: dict) -> dict:
    """AMENDMENT 08 (đợt 30 việc 122): M6 theo luật missed như M3 — bỏ cờ `khong_missed` ở mọi task
    M6, ngưỡng dùng chung `late_missed_s`. Mọi thứ khác (id, `at`, params, cờ khác, task M khác)
    giữ nguyên từng byte. Task M6 đã có kết quả không bị đụng tới về nghĩa (đã xong thì không chọn)."""
    if plan.get("amendment_08"):
        raise ValueError("plan đã ở AMENDMENT 08")
    tasks = []
    for t in plan["tasks"]:
        if t["m"] == "M6":
            t = {k: v for k, v in t.items() if k != "khong_missed"}
        tasks.append(t)
    return {**plan, "tasks": tasks,
            "amendment_08": {"m6_late_missed_s": float(plan.get("late_missed_s", 7200)),
                             "prereg": "docs/benchmark/PREREG_M1-M4_20260916.md §AMENDMENT 08"}}
