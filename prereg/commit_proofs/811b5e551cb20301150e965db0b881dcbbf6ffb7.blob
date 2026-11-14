"""29 ô (§6 + V2-06) và cách dựng cặp chấm (§6, V2-07(b), V2-07(d)). Bảng ô chép từ PREREG_V2, không từ dữ liệu.

"Đổi" (§3): decision khác nhãn (PARSE_FAIL là một nhãn); artefact khác chuỗi sau khi bỏ khoảng trắng đầu/cuối;
tập tên miền so như tập.
"""
from __future__ import annotations

from dataclasses import dataclass

from .load import gio, rd, tach_id
from .stats import KHONG, ON


@dataclass(frozen=True)
class O:
    o: int
    nguon: str          # P2 | P3 | MD3R | P3H
    stage: str          # stage trong task_id (MD3R: M2 | M4)
    be: str             # hosted | local | bm25 | openrouter
    do_sau: int
    obs: str            # dec | art
    quan_sat: str
    pin: str            # delegated | pinnable
    ho: str             # gemini | qwen | llama | bm25
    du_doan: str
    n_dk: int
    tinh_diem: bool
    suy_tu: int | None
    lay: str            # hàm lấy giá trị
    cap: str            # 1to5 | cung_runtime | md3r


O_ALL = [
    O(1, "P2", "classify", "hosted", 1, "dec", "answerable", "delegated", "gemini", ON, 200, True, None, "dec", "1to5"),
    O(2, "P2", "classify", "hosted", 1, "art", "JSON thô", "delegated", "gemini", KHONG, 200, True, None, "art", "1to5"),
    O(3, "P2", "classify", "local", 1, "dec", "answerable", "pinnable", "qwen", ON, 200, False, 4, "dec", "cung_runtime"),
    O(4, "P2", "classify", "local", 1, "art", "JSON thô", "pinnable", "qwen", ON, 200, True, None, "art", "cung_runtime"),
    O(5, "P2", "route", "hosted", 2, "dec", "route", "delegated", "gemini", ON, 200, True, None, "dec", "1to5"),
    O(6, "P2", "route", "hosted", 2, "art", "text thô", "delegated", "gemini", KHONG, 200, True, None, "art", "1to5"),
    O(7, "P2", "route", "local", 2, "dec", "route", "pinnable", "qwen", ON, 200, False, 8, "dec", "cung_runtime"),
    O(8, "P2", "route", "local", 2, "art", "text thô", "pinnable", "qwen", ON, 200, True, None, "art", "cung_runtime"),
    O(9, "P2", "retrieve", "bm25", 3, "dec", "top-5 id", "pinnable", "bm25", ON, 200, True, None, "dec", "1to5"),
    O(10, "P2", "retrieve", "bm25", 3, "art", "đoạn trích", "pinnable", "bm25", ON, 200, False, 9, "art", "1to5"),
    O(11, "P2", "live", "hosted", 3, "dec", "SOURCES", "delegated", "gemini", ON, 50, True, None, "dec", "1to5"),
    O(12, "P2", "live", "hosted", 3, "art", "tập tên miền (A)", "delegated", "gemini", KHONG, 50, True, None, "dom", "1to5"),
    O(13, "P2", "live", "hosted", 3, "art", "văn bản (B)", "delegated", "gemini", KHONG, 50, True, None, "art", "1to5"),
    O(14, "P2", "generate", "hosted", 4, "dec", "kết cục", "delegated", "gemini", ON, 200, True, None, "dec", "1to5"),
    O(15, "P2", "generate", "hosted", 4, "art", "văn bản", "delegated", "gemini", KHONG, 200, True, None, "art", "1to5"),
    O(16, "P2", "generate", "local", 4, "dec", "kết cục", "pinnable", "qwen", ON, 200, False, 17, "dec", "cung_runtime"),
    O(17, "P2", "generate", "local", 4, "art", "văn bản", "pinnable", "qwen", ON, 200, True, None, "art", "cung_runtime"),
    O(18, "P3", "route", "local", 2, "dec", "route", "pinnable", "llama", ON, 200, False, 19, "dec", "cung_runtime"),
    O(19, "P3", "route", "local", 2, "art", "text thô", "pinnable", "llama", ON, 200, True, None, "art", "cung_runtime"),
    O(20, "P3", "generate", "local", 4, "dec", "kết cục", "pinnable", "llama", ON, 200, False, 21, "dec", "cung_runtime"),
    O(21, "P3", "generate", "local", 4, "art", "văn bản", "pinnable", "llama", ON, 200, True, None, "art", "cung_runtime"),
    O(22, "MD3R", "M2", "local", 2, "dec", "lookup", "pinnable", "llama", ON, 100, False, 23, "md_lookup", "md3r"),
    O(23, "MD3R", "M2", "local", 2, "art", "text thô", "pinnable", "llama", ON, 100, True, None, "md_raw", "md3r"),
    O(24, "MD3R", "M4", "local", 4, "dec", "nhãn ngôn ngữ", "pinnable", "llama", ON, 50, False, 25, "md_lang", "md3r"),
    O(25, "MD3R", "M4", "local", 4, "art", "reply_text", "pinnable", "llama", ON, 50, True, None, "md_reply", "md3r"),
    O(26, "P3H", "route", "openrouter", 2, "dec", "route", "delegated", "llama", ON, 200, True, None, "dec", "1to5"),
    O(27, "P3H", "route", "openrouter", 2, "art", "text thô", "delegated", "llama", KHONG, 200, True, None, "art", "1to5"),
    O(28, "P3H", "generate", "openrouter", 4, "dec", "kết cục", "delegated", "llama", ON, 200, True, None, "dec", "1to5"),
    O(29, "P3H", "generate", "openrouter", 4, "art", "văn bản", "delegated", "llama", KHONG, 200, True, None, "art", "1to5"),
]
BY_O = {c.o: c for c in O_ALL}
DV_P2 = [1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 14, 15, 17]          # 13 đơn vị pipeline 2 (H3)
DV_N3 = [19, 21, 23, 25]
DV_P3H = [26, 27, 28, 29]                                      # k = 4 của V2-06
H1_O = [1, 2, 4, 5, 6, 8, 9, 11, 12, 13, 14, 15, 17, 19, 21]   # V2-05 D3

# cặp (dec, art) cho margin §8 / V2-06: tên -> (ô dec, ô art)
CAP_MARGIN = {
    "P2 classify hosted": (1, 2), "P2 route hosted": (5, 6), "P2 generate hosted": (14, 15),
    "P2 live A (tên miền)": (11, 12), "P2 live B (văn bản)": (11, 13),
    "P2 classify qwen": (3, 4), "P2 route qwen": (7, 8), "P2 generate qwen": (16, 17), "P2 retrieve BM25": (9, 10),
    "P3 route llama": (18, 19), "P3 generate llama": (20, 21),
    "MD3R routing llama": (22, 23), "MD3R reply llama": (24, 25),
    "P3H route llama": (26, 27), "P3H generate llama": (28, 29),
}
H2_I = ["P2 classify hosted", "P2 route hosted", "P2 generate hosted", "P2 live A (tên miền)", "P2 live B (văn bản)"]
H2_II = ["P2 classify qwen", "P2 route qwen", "P2 generate qwen", "P3 route llama", "P3 generate llama",
         "MD3R routing llama", "MD3R reply llama"]


def gia_tri(rec: dict, lay: str):
    p = rec["payload"]
    if lay == "dec":
        return p["decision"]
    if lay == "art":
        return (p.get("artefact") or "").strip()
    if lay == "dom":
        return frozenset(x for x in (p.get("artefact_domains") or "").split(",") if x)
    if lay == "md_lookup":
        return p["lookup"]
    if lay == "md_raw":
        return (p.get("raw_text") or "").strip()
    if lay == "md_lang":
        return p["lang_label"]
    if lay == "md_reply":
        return (p.get("reply_text") or "").strip()
    raise ValueError(lay)


def chi_muc(data: dict) -> tuple[dict, dict]:
    """chuoi[(m, stage, be, q)] = {run: rec}; probe[(m, stage, be, q)] = {tag: rec}. run: int (P2/P3/P3H) hoặc t0/t0p/t24h."""
    chuoi: dict = {}
    probe: dict = {}
    for m in ("P2", "P3", "P3H", "MD3", "MD3R"):
        for tid in sorted(data.get(m, {})):
            r = data[m][tid]
            t = tach_id(tid)
            key = (t["m"], t["stage"], t["be"], t["q"])
            if t["probe"] is not None and t["run"] is None:
                probe.setdefault(key, {})[t["probe"]] = r
            else:
                chuoi.setdefault(key, {})[t["run"]] = r
    return chuoi, probe


def cap_mot(runs: dict, luat: str):
    """Trả (rec1, rec2, nhãn lần) hoặc None (cặp thiếu ⇒ n giảm, §6)."""
    if luat == "1to5":
        a, b = runs.get(1), runs.get(5)
        return (a, b, 5) if a and b else None
    if luat == "cung_runtime":
        k = rd.chon_k({j: r["ts"] for j, r in runs.items() if isinstance(j, int)})
        return (runs[1], runs[k], k) if k is not None else None
    if luat == "md3r":
        a, b = runs.get("t0"), runs.get("t24h")
        return (a, b, "t24h") if a and b else None
    raise ValueError(luat)


def cap_o(chuoi: dict, c: O, luat: str | None = None, nguon: str | None = None) -> list[dict]:
    """Danh sách cặp của ô c (luật mặc định của ô; `luat`/`nguon` để in cặp đăng ký 1→5 hoặc MD3 cũ)."""
    luat = luat or c.cap
    m = nguon or c.nguon
    ra = []
    for (mm, st, be, q), runs in sorted(chuoi.items(), key=lambda kv: kv[0]):
        if mm != m or st != c.stage or be != c.be:
            continue
        cp = cap_mot(runs, luat)
        if cp is None:
            continue
        a, b, k = cp
        ra.append({"q": q, "doi": gia_tri(a, c.lay) != gia_tri(b, c.lay), "k": k, "ts1": a["ts"], "ts2": b["ts"],
                   "gap_h": gio(a["ts"], b["ts"]), "doan": rd.doan(a["ts"]) + rd.doan(b["ts"]),
                   "pf": [gia_tri(a, "dec") == "PARSE_FAIL", gia_tri(b, "dec") == "PARSE_FAIL"]
                   if c.lay in ("dec", "art", "dom") else None})
    return ra
