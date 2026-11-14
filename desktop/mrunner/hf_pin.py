r"""Ghim model Hugging Face theo REVISION HASH, chạy offline (AMENDMENT 05).

Sự cố 17/09 (catalogue ca #7): `hf_hub_download(repo, file)` không kèm `revision` ⇒ thư viện hỏi
`main` trên mạng mỗi lần nạp và tự tải revision mới nếu có. VieNeu đã tải revision `5f2a3e93…` lúc
07:13:37; faster-whisper hỏi `revision/main` mỗi lần runner nạp model. Một stage "caller-pinnable"
mà revision không ghim thì chỉ pinnable trên giấy.

Cơ chế (không phải lời dặn):
1. `dat_moi_truong()` đặt `HF_HUB_OFFLINE=1` + `HF_HUB_DISABLE_IMPLICIT_TOKEN=1` TRƯỚC khi bất kỳ
   module Hugging Face nào được import (huggingface_hub đọc biến lúc import).
2. Executor nạp model bằng **đường dẫn snapshot của revision ghim** (`snapshot()`), không bằng repo id.
3. `kiem()` — gọi bởi `run_m_all.py run` và `doctor`: offline thật sự có hiệu lực trong
   `huggingface_hub.constants`, snapshot của revision ghim có mặt, SHA-256 từng file khớp plan.
   Lệch bất kỳ ⇒ runner TỪ CHỐI chạy.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

HUB = Path.home() / ".cache/huggingface/hub"
BIEN = {"HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1"}

# Ghim 17/09/2026 (A05). SHA-256 đo lúc ghim; faster-whisper model.bin = A01.7.
PIN: dict[str, dict] = {
    "mobiuslabsgmbh/faster-whisper-large-v3-turbo": {
        "revision": "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
        "dung_cho": "M1 local, M6 STT local (runner)",
        "files_sha256": {
            "config.json": "b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e",
            "model.bin": "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da",
            "preprocessor_config.json": "7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711",
            "tokenizer.json": "297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd",
            "vocabulary.json": "c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1",
        },
    },
    "pnnbao-ump/VieNeu-TTS-v3-Turbo": {
        "revision": "5f2a3e93092efaba9153253ff5f2e6a8e810e4f2",
        "dung_cho": "S3 (m1_sinh_s3.py) — runner không nạp",
        "files_sha256": {
            "config.json": "eee8e032cb936a60312f594a8156c086173a9c0255a545bd11a448f22a7c77ae",
            "denoiser.onnx": "b7621953291cfe05e695a9c0ff4255aa2f93239fc17c26627e18b7b6b8f72f0b",
            "onnx_update/config.json": "17d89d414ee302a82db7b330bf57b4cdf8541569392119c81f552178cafcb79b",
            "onnx_update/tokenizer.json": "6cc6bcbe380b8c37bd9f2514e37c5dfa3e00e122c6e3125dae5c4afe48e39158",
            "onnx_update/vieneu_prefill.onnx": "27f8b064f6b57b5448e95d095f1959588c005d614678045c2b97ecccf3b7a0f7",
            "onnx_update/vieneu_decode_step.onnx": "bedc379cea61ea5d616312750d95ad3924e055856662d19187a889a5edc24ceb",
            "onnx_update/vieneu_acoustic_cached.onnx": "f631e3387c788c3d8b9a5ac5df94952af5bc4c4d1049ff8a751e76a246fff2d4",
            "onnx_update/vieneu_v3_heads.npz": "fb22484baa424bbb775133a6e5f0d00d6299b2b256fbe3312a864b85b9aed01e",
            "onnx_update/vieneu_backbone_shared.data": "c7c072193db33d0542457e2612c7272c44c4279d1cafaf0aa4c379964911db2f",
        },
    },
    # Thêm 17/09 (A05.7): SHA-256 = đúng các giá trị M1_s3_manifest.json ghi lúc sinh S3.
    "hexgrad/Kokoro-82M": {
        "revision": "f3ff3571791e39611d31c381e3a41a3af07b4987",
        "dung_cho": "S3 câu en (m1_sinh_s3.py) — runner không nạp",
        "files_sha256": {
            "config.json": "5abb01e2403b072bf03d04fde160443e209d7a0dad49a423be15196b9b43c17f",
            "kokoro-v1_0.pth": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
            "voices/af_heart.pt": "0ab5709b8ffab19bfd849cd11d98f75b60af7733253ad0d67b12382a102cb4ff",
            "voices/am_michael.pt": "9a443b79a4b22489a5b0ab7c651a0bcd1a30bef675c28333f06971abbd47bd37",
            "voices/bm_fable.pt": "d44935f3135257a9064df99f007fc1342ff1aa767552b4a4fa4c3b2e6e59079c",
        },
    },
}


def dat_moi_truong() -> None:
    for k, v in BIEN.items():
        os.environ[k] = v


def snapshot(repo: str, pin: dict | None = None) -> Path:
    p = (pin or PIN)[repo]
    return HUB / ("models--" + repo.replace("/", "--")) / "snapshots" / p["revision"]


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.resolve().open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


_DA_KIEM: dict[tuple, list[str]] = {}


def kiem(pin: dict | None = None, repos: tuple[str, ...] | None = None, hash_file: bool = True) -> list[str]:
    """Trả danh sách lỗi (rỗng = đạt). Kết quả hash giữ trong tiến trình (model GB, băm một lần)."""
    pin = pin or PIN
    loi: list[str] = []
    for k, v in BIEN.items():
        if os.environ.get(k) != v:
            loi.append(f"biến môi trường {k}={os.environ.get(k)!r}, cần {v!r}")
    try:
        import huggingface_hub.constants as hc
        if not hc.HF_HUB_OFFLINE:
            loi.append("huggingface_hub.constants.HF_HUB_OFFLINE = False — biến đặt SAU khi import (vô hiệu)")
    except Exception as exc:
        loi.append(f"không đọc được huggingface_hub.constants: {exc}")
    for repo in (repos or tuple(pin)):
        khoa = (repo, pin[repo]["revision"], hash_file)
        if khoa in _DA_KIEM:
            loi += _DA_KIEM[khoa]
            continue
        rl: list[str] = []
        s = snapshot(repo, pin)
        if not s.is_dir():
            rl.append(f"{repo}: không có snapshot revision {pin[repo]['revision'][:12]} trong cache")
        else:
            for f, h in pin[repo]["files_sha256"].items():
                p = s / f
                if not p.exists():
                    rl.append(f"{repo}@{pin[repo]['revision'][:12]}: thiếu {f}")
                elif hash_file and _sha(p) != h:
                    rl.append(f"{repo}@{pin[repo]['revision'][:12]}: {f} lệch SHA-256")
        _DA_KIEM[khoa] = rl
        loi += rl
    return loi


def mo_ta(repo: str, pin: dict | None = None) -> dict:
    p = (pin or PIN)[repo]
    return {"repo": repo, "revision": p["revision"], "files_sha256": p["files_sha256"],
            "hf_offline": os.environ.get("HF_HUB_OFFLINE") == "1"}
