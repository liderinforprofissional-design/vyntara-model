"""Ensemble - combina os tres pilares (Poisson + Elo + ML) numa probabilidade final.

- ML: XGBoost se instalado, senao RandomForest (scikit-learn).
- Combinacao: por padrao media ponderada; se `use_stacker`, treina uma
  regressao logistica (meta-modelo) que aprende os pesos a partir dos dados.
"""

from __future__ import annotations

import numpy as np

CLASSES = [0, 1, 2]  # casa, empate, fora


# ---- pilar ML ---------------------------------------------------------------
def make_classifier():
    try:
        from xgboost import XGBClassifier
        return XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9,
            objective="multi:softprob", num_class=3, eval_metric="mlogloss",
            verbosity=0,
        )
    except Exception:
        from sklearn.ensemble import RandomForestClassifier
        return RandomForestClassifier(
            n_estimators=400, max_depth=8, min_samples_leaf=5, n_jobs=-1, random_state=42,
        )


def _align(classes, proba_row) -> list[float]:
    """Garante ordem [casa, empate, fora] mesmo se alguma classe faltar no treino."""
    out = [0.0, 0.0, 0.0]
    for c, p in zip(classes, proba_row):
        out[int(c)] = float(p)
    s = sum(out) or 1.0
    return [x / s for x in out]


def train_ml(X: list[list[float]], y: list[int]):
    clf = make_classifier()
    clf.fit(np.array(X, dtype=float), np.array(y, dtype=int))
    return clf


def ml_probs(clf, x: list[float]) -> dict:
    proba = clf.predict_proba(np.array([x], dtype=float))[0]
    p = _align(clf.classes_, proba)
    return {"home": p[0], "draw": p[1], "away": p[2]}


# ---- combinacao -------------------------------------------------------------
def weighted_average(pois: dict, elo: dict, ml: dict | None, weights: dict) -> dict:
    wp, we, wm = weights.get("poisson", 0.34), weights.get("elo", 0.33), weights.get("ml", 0.33)
    if ml is None:
        wm = 0.0
    total_w = wp + we + wm or 1.0
    out = {}
    for k in ("home", "draw", "away"):
        val = wp * pois[k] + we * elo[k] + (wm * ml[k] if ml else 0.0)
        out[k] = val / total_w
    s = sum(out.values()) or 1.0
    return {k: v / s for k, v in out.items()}


def _vec(pois, elo, ml) -> list[float]:
    ml = ml or {"home": 1 / 3, "draw": 1 / 3, "away": 1 / 3}
    return [pois["home"], pois["draw"], pois["away"],
            elo["home"], elo["draw"], elo["away"],
            ml["home"], ml["draw"], ml["away"]]


def fit_stacker(rows: list[tuple[dict, dict, dict | None]], y: list[int]):
    """rows: lista de (pois, elo, ml). Retorna um LogisticRegression treinado ou None."""
    try:
        from sklearn.linear_model import LogisticRegression
    except Exception:
        return None
    P = np.array([_vec(*r) for r in rows], dtype=float)
    yy = np.array(y, dtype=int)
    if len(set(yy.tolist())) < 2:
        return None
    lr = LogisticRegression(max_iter=1000)
    lr.fit(P, yy)
    return lr


def stacker_probs(stacker, pois: dict, elo: dict, ml: dict | None) -> dict:
    proba = stacker.predict_proba(np.array([_vec(pois, elo, ml)], dtype=float))[0]
    p = _align(stacker.classes_, proba)
    return {"home": p[0], "draw": p[1], "away": p[2]}
