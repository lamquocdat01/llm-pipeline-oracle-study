r"""Prompt của 4 stage — hằng số; SHA-256 từng prompt vào manifest mỗi task (đổi chữ = đổi phép đo).

Cùng một prompt cho nhánh hosted và nhánh local của mỗi stage: khác biệt giữa hai nhánh chỉ còn là
AI vận hành model (caller hay nhà cung cấp), như cặp local/hosted của Microduck.
"""
from __future__ import annotations

import hashlib

# Đợt 32 N2 (quyết định anh Đạt 01-11): decision của classify = answerable/unanswerable so với đoạn văn
# (nhãn vàng SQuAD 2.0 `is_impossible`); ngôn ngữ vẫn hỏi nhưng chỉ ghi log.
CLASSIFY = ("Read the passage and the question. Decide whether the passage contains the answer to the question. "
            "Reply with JSON only, no other text: "
            '{{"language": "<ISO 639-1 code of the question>", "answerable": <true or false>}}\n\n'
            "Passage: {p}\n\nQuestion: {q}")

ROUTE = ("You are the router of a question-answering service that has a document index. Decide one route: "
         "RETRIEVE (the answer needs the index), ANSWER (general knowledge suffices) or REFUSE (unanswerable or unsafe). "
         "Reply exactly in the form: ROUTE: <RETRIEVE|ANSWER|REFUSE>. REASON: <one sentence>.\n"
         "Question: {q}")

GENERATE = ("Answer the question using only the documents below. Cite every claim with its document id in square "
            "brackets, e.g. [d0123]. If the documents do not contain the answer, reply exactly \"NOT IN DOCUMENTS\". "
            "Answer in the language of the question, in at most three sentences.\n\n{docs}\n\nQuestion: {q}")

LIVE = ("Answer the question using a web search. Answer in the language of the question, in at most three "
        "sentences.\nQuestion: {q}")

TAT_CA = {"classify": CLASSIFY, "route": ROUTE, "generate": GENERATE, "live": LIVE}


def sha(stage: str) -> str:
    return hashlib.sha256(TAT_CA[stage].encode("utf-8")).hexdigest()


def khoi_doc(docs: list[dict]) -> str:
    return "\n\n".join(f"[{d['id']}] {d['text']}" for d in docs)
