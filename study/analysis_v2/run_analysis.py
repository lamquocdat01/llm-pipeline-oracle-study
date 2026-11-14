r"""N4 — chạy toàn bộ phân tích v2 và xuất `out/` (numbers_v2.json + CSV + hình).

    python study\analysis_v2\run_analysis.py                       # dữ liệu thật (study/pipeline2/results)
    python study\analysis_v2\run_analysis.py --data <thư mục giả> --out <thư mục> --B 200

numbers_v2.json tất định: khoá sắp xếp, số thực làm tròn 6 chữ số, không dấu thời gian.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from av2 import analysis  # noqa: E402
from av2.cells import BY_O, CAP_MARGIN  # noqa: E402
from av2.load import DATA_THAT  # noqa: E402


def lam_tron(x):
    if isinstance(x, bool) or x is None or isinstance(x, (int, str)):
        return x
    if isinstance(x, float):
        return None if math.isnan(x) or math.isinf(x) else round(x, 6) + 0.0
    if hasattr(x, "item"):                       # numpy scalar
        return lam_tron(x.item())
    if isinstance(x, dict):
        return {str(k): lam_tron(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [lam_tron(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted(lam_tron(v) for v in x)
    raise TypeError(type(x))


def ghi_csv(p: Path, rows: list[dict]) -> None:
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
                        for k, v in r.items()})


def xuat_csv(N: dict, out: Path) -> None:
    rows = []
    for o, d in sorted(N["don_vi"].items(), key=lambda kv: int(kv[0])):
        r = {"o": int(o), "nguon": d["nguon"], "stage": d["stage"], "be": d["be"], "quan_sat": d["quan_sat"],
             "pin": d["pin"], "ho": d["ho"], "du_doan": d["du_doan"], "tinh_diem": d["tinh_diem"],
             "n_dang_ky": d["n_dang_ky"], "n": d["n"], "k": d["k"], "ty_le": d["ty_le"],
             "wilson_lo": d["wilson"][0], "wilson_hi": d["wilson"][1], "phan_quyet": d["phan_quyet"],
             "thieu_luc": d["thieu_luc"], "vao_mau_so": d["vao_mau_so"], "luat_cap": d["luat_cap"],
             "k_lan_dung": d["k_lan_dung"], "gap_median_h": d["gap"]["median_h"], "gap_min_h": d["gap"]["min_h"],
             "gap_max_h": d["gap"]["max_h"]}
        if "cap_1to5_dang_ky" in d:
            c = d["cap_1to5_dang_ky"]
            r.update(dk_1to5_k=c["k"], dk_1to5_n=c["n"], dk_1to5_phan_quyet=c["phan_quyet"])
        rows.append(r)
    ghi_csv(out / "units_scoring.csv", rows)
    ghi_csv(out / "margins.csv", [{"cap": t, **{k: v for k, v in m.items() if k != "cap_1to5_dang_ky"},
                                   **({"dk_1to5_margin": m["cap_1to5_dang_ky"]["margin"],
                                       "dk_1to5_lo": m["cap_1to5_dang_ky"]["lo"],
                                       "dk_1to5_hi": m["cap_1to5_dang_ky"]["hi"]} if "cap_1to5_dang_ky" in m else {})}
                                  for t, m in N["margin"].items()])
    ghi_csv(out / "oracle_failure.csv", [{"cap": k, **v} for k, v in N["oracle"]["o"].items()])
    ghi_csv(out / "oracle_runs.csv", N["oracle"]["bang_lan"])
    hl = []
    for ten, m in [("chinh", N["h1"]["chinh"]["mo_hinh"])] + [(k, v) for k, v in N["h1"]["kham_pha"].items()
                                                              if isinstance(v, dict)]:
        for j, t in enumerate(m["ten"]):
            r = {"mo_hinh": ten, "he_so": t, "beta": m["beta"][j], "ci_lo": m["ci_lo"][j], "ci_hi": m["ci_hi"][j],
                 "ci_nguon": m["ci_nguon"], "uoc_luong": m["uoc_luong"], "tach_hoan_toan": m["tach_hoan_toan"],
                 "N": m["N"], "G": m["G"]}
            for b in m["bootstrap"]:
                r[f"boot_{b['seed']}_lo"], r[f"boot_{b['seed']}_hi"] = b["lo"][j], b["hi"][j]
            hl.append(r)
    ghi_csv(out / "h1_logit.csv", hl)
    ru = list(N["d7_runtime"]["hang"]) + [{"nguon": "P2O", "stage": s["cap"], "cap": f"{s['task_id']} (đoạn B) vs golden",
                                           "n": s["n"], "dec_doi": s["dec_do"], "art_doi": s["art_do"]}
                                          for s in N["oracle"]["silent_runtime_update"]]
    ghi_csv(out / "runtime_update_exploratory.csv", ru)
    v = N["v206_p3h"]
    if v.get("co_du_lieu"):
        pr = []
        for st in ("route", "generate"):
            for nh in ("p3h", "p3_local_cung_runtime"):
                pr.append({"stage": st, "nhanh": nh, **v[st][nh]})
            pr.append({"stage": st, "nhanh": "delta_r_art (P3H − P3)", **v[st]["delta_r_art"]})
        ghi_csv(out / "p3h_control.csv", pr)
    ghi_csv(out / "probes.csv", N["d10"]["probe"])
    ghi_csv(out / "parse_fail.csv", N["d10"]["parse_fail"])


def ve(N: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    meta = {"Software": None}
    # 1. margin theo stage × họ × pipeline
    ten = list(CAP_MARGIN)
    fig, ax = plt.subplots(figsize=(7.5, 6))
    for i, t in enumerate(ten):
        m = N["margin"][t]
        if m["margin"] is None:
            continue
        mk = "o" if m["pin"] == "delegated" else "s"
        ax.errorbar(m["margin"], i, xerr=[[m["margin"] - m["lo"]], [m["hi"] - m["margin"]]], fmt=mk,
                    color="black", mfc="white" if m["pin"] == "pinnable" else "black", capsize=3)
        ax.text(1.02, i, f"{m['margin']:.3f}", va="center", fontsize=7, transform=ax.get_yaxis_transform())
    ax.axvline(0, ls=":", color="grey")
    ax.set_yticks(range(len(ten)))
    ax.set_yticklabels([f"{t}  [{N['margin'][t]['pin']}]" for t in ten], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("margin = R_art − R_dec (cặp chấm), Newcombe 95 %  ·  ● delegated  □ pinnable")
    fig.tight_layout()
    fig.savefig(out / "fig_margin.png", dpi=150, metadata=meta)
    plt.close(fig)
    # 2. oracle: số test đỏ ≥ 1 lần (luỹ kế) theo lần
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    marks = {"classify": "o", "route": "s", "generate": "^", "retrieve": "D"}
    for ax, nhom in zip(axs, (("hosted", "bm25"), ("local",))):
        for k, v in N["oracle"]["o"].items():
            st, be = k.split("|")
            if be not in nhom:
                continue
            xs = list(range(2, 2 + len(v["luy_ke_art"])))
            ax.plot(xs, [x / v["n_tests"] for x in v["luy_ke_art"]], ls="-", marker=marks[st], ms=3, color="black",
                    label=f"{k} artefact")
            ax.plot(xs, [x / v["n_tests"] for x in v["luy_ke_dec"]], ls="--", marker=marks[st], ms=3, color="grey",
                    mfc="white", label=f"{k} decision")
        ax.set_title("hosted + BM25" if "hosted" in nhom else "local qwen (đoạn A/D)", fontsize=9)
        ax.set_xlabel("lần (so golden)")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend(fontsize=6)
    axs[0].set_ylabel("tỉ lệ test đỏ ≥ 1 lần (luỹ kế)")
    fig.tight_layout()
    fig.savefig(out / "fig_oracle_by_run.png", dpi=150, metadata=meta)
    plt.close(fig)
    # 3. bảng đơn vị
    rows = []
    for o, d in sorted(N["don_vi"].items(), key=lambda kv: int(kv[0])):
        if not d["tinh_diem"]:
            continue
        rows.append([o, d["nguon"], d["stage"], d["quan_sat"], d["pin"], d["du_doan"], f"{d['k']}/{d['n']}",
                     f"{d['wilson'][0]:.3f}–{d['wilson'][1]:.3f}", d["phan_quyet"] + (" (thiếu lực)" if d["thieu_luc"] else "")])
    fig, ax = plt.subplots(figsize=(10, 0.3 * len(rows) + 0.8))
    ax.axis("off")
    tb = ax.table(cellText=rows, colLabels=["ô", "nguồn", "stage", "observable", "pin", "dự đoán", "k/n", "Wilson 95 %",
                                            "phán quyết"], loc="center", cellLoc="left")
    tb.auto_set_font_size(False)
    tb.set_fontsize(7)
    tb.scale(1, 1.2)
    fig.tight_layout()
    fig.savefig(out / "fig_units.png", dpi=150, metadata=meta)
    plt.close(fig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=DATA_THAT)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "out")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, action="append", help="lặp lại ≥ 5 lần; mặc định 5 seed cố định")
    ap.add_argument("--no-fig", action="store_true")
    a = ap.parse_args(argv)
    seeds = a.seed or analysis.SEEDS
    if len(seeds) < 5:
        ap.error("cần ≥ 5 seed (PREREG_V2 §7b, prompt P2B)")
    a.out.mkdir(parents=True, exist_ok=True)
    N = lam_tron(analysis.chay(a.data, a.B, seeds))
    (a.out / "numbers_v2.json").write_text(json.dumps(N, ensure_ascii=False, sort_keys=True, indent=1) + "\n",
                                           encoding="utf-8", newline="\n")
    xuat_csv(N, a.out)
    if not a.no_fig:
        ve(N, a.out)
    print(f"xong: {a.out / 'numbers_v2.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
