"""Hồi quy logistic H1 (§7b, V2-05 D3): ML + sai số cluster; tách hoàn toàn ⇒ Firth + bootstrap cluster.

Viết tay bằng numpy (không statsmodels) để venv tái lập nhỏ và tất định. Firth: điểm hiệu chỉnh
U* = Xᵀ(y − n·p + h(½ − p)), h = đường chéo ma trận mũ của thiết kế gộp (Firth 1993; Heinze & Schemper 2002).

Thiết kế chỉ có vài tổ hợp biến (depth × pinnable × observable), nên dữ liệu được GỘP thành binomial theo
(tổ hợp × cluster). Log-likelihood, ma trận thông tin, hiệu chỉnh Firth và điểm theo cluster của dạng gộp bằng
đúng dạng từng hàng (tổng theo hàng trong một tổ hợp), nên ước lượng không đổi — chỉ nhanh hơn
(test `test_gop_bang_tung_hang`).
"""
from __future__ import annotations

import numpy as np

Z = 1.959963984540054
NGUONG_TACH_BETA = 15.0      # |β| ML > 15 (OR > 3·10⁶) hoặc không hội tụ ⇒ coi là tách hoàn toàn / gần hoàn toàn


def _p(eta):
    return 1.0 / (1.0 + np.exp(-np.clip(eta, -700, 700)))


def _pll(X, y, n, b, firth):
    eta = X @ b
    ll = float(np.sum(y * eta - n * np.logaddexp(0.0, eta)))
    if firth:
        p = _p(eta)
        W = n * p * (1 - p)
        s, ld = np.linalg.slogdet(X.T @ (X * W[:, None]))
        ll += 0.5 * ld if s > 0 else -1e300
    return ll


def fit(X: np.ndarray, y: np.ndarray, firth: bool = False, n: np.ndarray | None = None, maxit: int = 200,
        tol: float = 1e-10) -> dict:
    """y = số thành công, n = số thử (mặc định 1: dạng từng hàng)."""
    n = np.ones(len(y)) if n is None else n
    b = np.zeros(X.shape[1])
    ok = False
    it = 0
    for it in range(maxit):
        p = _p(X @ b)
        W = n * p * (1 - p)
        info = X.T @ (X * W[:, None])
        try:
            inv = np.linalg.inv(info)
        except np.linalg.LinAlgError:
            break
        if firth:
            h = W * np.sum((X @ inv) * X, axis=1)
            U = X.T @ (y - n * p + h * (0.5 - p))
        else:
            U = X.T @ (y - n * p)
        step = inv @ U
        l0 = _pll(X, y, n, b, firth)
        t = 1.0
        while t > 1e-10 and _pll(X, y, n, b + t * step, firth) < l0 - 1e-12:
            t /= 2
        nb = b + t * step
        if np.max(np.abs(nb - b)) < tol:
            b = nb
            ok = True
            break
        b = nb
        if not firth and np.max(np.abs(b)) > 50:
            break
    p = _p(X @ b)
    info = X.T @ (X * (n * p * (1 - p))[:, None])
    return {"beta": b, "converged": ok, "iter": it + 1, "info": info}


def gom(X: np.ndarray, y: np.ndarray, cl: np.ndarray) -> dict:
    """Xp: các tổ hợp hàng (P × K, sắp xếp); Y, Nn: (G × P) số không đổi / số cặp theo cluster × tổ hợp."""
    Xp, inv_p = np.unique(X, axis=0, return_inverse=True)
    ug, inv_g = np.unique(cl, return_inverse=True)
    Y = np.zeros((len(ug), len(Xp)))
    Nn = np.zeros((len(ug), len(Xp)))
    np.add.at(Y, (inv_g, inv_p.ravel()), y)
    np.add.at(Nn, (inv_g, inv_p.ravel()), 1.0)
    return {"Xp": Xp, "Y": Y, "Nn": Nn, "G": len(ug)}


def tach(X, y, n=None) -> tuple[bool, dict]:
    r = fit(X, y, firth=False, n=n)
    sep = (not r["converged"]) or bool(np.max(np.abs(r["beta"])) > NGUONG_TACH_BETA)
    return sep, r


def se_cluster(g: dict, b) -> np.ndarray:
    """CR1: V = I⁻¹ (Σ_g s_g s_gᵀ) I⁻¹ · G/(G−1) · (N−1)/(N−K)."""
    Xp = g["Xp"]
    p = _p(Xp @ b)
    n = g["Nn"].sum(0)
    inv = np.linalg.inv(Xp.T @ (Xp * (n * p * (1 - p))[:, None]))
    S = (g["Y"] - g["Nn"] * p[None, :]) @ Xp            # G × K điểm theo cluster
    meat = S.T @ S
    N, K, G = n.sum(), Xp.shape[1], g["G"]
    V = inv @ meat @ inv * (G / (G - 1)) * ((N - 1) / (N - K))
    return np.sqrt(np.diag(V))


def bootstrap(g: dict, firth: bool, B: int, seed: int) -> dict:
    """Bootstrap cluster theo câu (lấy lại câu có hoàn lại, kéo theo mọi cặp của câu). Percentile 2,5 / 97,5."""
    rng = np.random.default_rng(seed)
    G = g["G"]
    bs = np.empty((B, g["Xp"].shape[1]))
    fb = 0
    for i in range(B):
        pick = rng.integers(0, G, G)
        y, n = g["Y"][pick].sum(0), g["Nn"][pick].sum(0)
        r = fit(g["Xp"], y, firth=firth, n=n)
        if not firth and (not r["converged"] or np.max(np.abs(r["beta"])) > NGUONG_TACH_BETA):
            r = fit(g["Xp"], y, firth=True, n=n)
            fb += 1
        bs[i] = r["beta"]
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return {"seed": seed, "B": B, "lo": lo.tolist(), "hi": hi.tolist(), "firth_fallback": fb}


def mo_hinh(X, y, cl, ten: list[str], B: int, seeds: list[int], firth_luon: bool = False) -> dict:
    """Ước lượng chính theo D3 + bootstrap 5 seed. CI quyết định: Wald cluster (không tách) hoặc khoảng
    bootstrap rộng nhất qua các seed (tách ⇒ Firth)."""
    g = gom(X, y, cl)
    ys, ns = g["Y"].sum(0), g["Nn"].sum(0)
    sep, ml = tach(g["Xp"], ys, ns)
    firth = sep or firth_luon
    est = fit(g["Xp"], ys, firth=True, n=ns) if firth else ml
    b = est["beta"]
    out = {"ten": ten, "N": int(X.shape[0]), "G": int(g["G"]), "so_to_hop": int(len(g["Xp"])),
           "tach_hoan_toan": bool(sep), "uoc_luong": "Firth" if firth else "ML", "beta": b.tolist(),
           "hoi_tu": bool(est["converged"]), "ml_beta": ml["beta"].tolist(), "ml_hoi_tu": bool(ml["converged"])}
    if not firth:
        se = se_cluster(g, b)
        out["se_cluster"] = se.tolist()
        out["wald_lo"] = (b - Z * se).tolist()
        out["wald_hi"] = (b + Z * se).tolist()
    boots = [bootstrap(g, firth, B, s) for s in seeds]
    out["bootstrap"] = boots
    out["boot_rong_nhat_lo"] = np.min([bb["lo"] for bb in boots], axis=0).tolist()
    out["boot_rong_nhat_hi"] = np.max([bb["hi"] for bb in boots], axis=0).tolist()
    if firth:
        out["ci_lo"], out["ci_hi"] = out["boot_rong_nhat_lo"], out["boot_rong_nhat_hi"]
        out["ci_nguon"] = "bootstrap cluster Firth, khoảng rộng nhất qua seed"
    else:
        out["ci_lo"], out["ci_hi"] = out["wald_lo"], out["wald_hi"]
        out["ci_nguon"] = "Wald, sai số cluster theo câu (CR1)"
    return out


def du_doan_xs(b: list[float], ten: list[str]) -> list[dict]:
    """P(không đổi) dự đoán theo depth 1–4 ở từng tổ hợp (pinnable, observable) — D3: báo theo từng bậc depth."""
    b = np.asarray(b)
    ra = []
    for pin in (0, 1):
        for art in (0, 1):
            ps = []
            for d in (1, 2, 3, 4):
                x = {"const": 1.0, "depth": d, "pinnable": pin, "artefact": art}
                ps.append(float(_p(np.dot(b, [x[t] for t in ten]))))
            ra.append({"pinnable": pin, "artefact": art, "p_depth_1_4": ps,
                       "doi_moi_bac": [ps[i + 1] - ps[i] for i in range(3)]})
    return ra
