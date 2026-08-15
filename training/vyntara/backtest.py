"""Backtesting - mede se o algoritmo e bom de verdade.

Metricas em cima de um conjunto de teste (jogos que o modelo NAO viu no treino):
 - accuracy: % de acerto do resultado 1X2
 - logloss : penaliza confianca errada (quanto menor, melhor)
 - brier   : erro quadratico das probabilidades (quanto menor, melhor)
"""

from __future__ import annotations

import math


def evaluate(preds: list[dict], y: list[int]) -> dict:
    n = len(y)
    if n == 0:
        return {"n": 0, "accuracy": 0.0, "logloss": 0.0, "brier": 0.0}
    correct = 0
    ll = 0.0
    brier = 0.0
    for p, t in zip(preds, y):
        probs = [p["home"], p["draw"], p["away"]]
        pred = max(range(3), key=lambda i: probs[i])
        if pred == t:
            correct += 1
        pt = min(max(probs[t], 1e-12), 1.0)
        ll += -math.log(pt)
        onehot = [0.0, 0.0, 0.0]
        onehot[t] = 1.0
        brier += sum((probs[i] - onehot[i]) ** 2 for i in range(3))
    return {
        "n": n,
        "accuracy": round(correct / n, 4),
        "logloss": round(ll / n, 4),
        "brier": round(brier / n, 4),
    }
