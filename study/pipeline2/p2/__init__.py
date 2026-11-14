r"""Pipeline 2 (đợt 32, TSE v2.0): RAG văn bản trên SQuAD 2.0 dev, 4 stage ánh xạ 1-1 với Microduck.

    classify  <-> recognition : nhãn ngôn ngữ + loại câu hỏi            (decision) / văn bản thô model trả (artefact)
    route     <-> routing     : RETRIEVE / ANSWER / REFUSE              (decision) / lý do model viết ra   (artefact)
    retrieve  <-> grounding   : BM25 ghim hash: top-k doc id            (decision) / đoạn trích            (artefact)
                                live (Google Search grounding): tập domain (decision) / câu trả lời có nguồn (artefact)
    generate  <-> generation  : trích đúng doc vàng? bỏ trả lời? ngôn ngữ (decision) / văn bản trả lời     (artefact)

Mỗi stage đo trên ĐẦU VÀO CỐ ĐỊNH theo câu hỏi (không nối tầng khi đo): biến thiên của một stage không lẫn
biến thiên của stage trước — giống cách Microduck đo M1/M2/M4 riêng. `smoke.py` mới chạy nối tầng.

Tái dùng runner Microduck qua import (`desktop/mrunner`), không chép: `core.gia_usd`, `thuc.ollama_*`.
"""
from __future__ import annotations

import sys
from pathlib import Path

P2_DIR = Path(__file__).resolve().parents[1]           # study/pipeline2
REPO = P2_DIR.parents[1]                                # Microduck
DESKTOP = REPO / "desktop"
for _p in (DESKTOP, REPO / "study" / "langconf"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
