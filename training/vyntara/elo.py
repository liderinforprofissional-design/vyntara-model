"""Pilar 3 - Sistema de rating Elo dinamico.

Percorre os jogos em ordem cronologica: quem vence ganha pontos de quem perde.
Retorna os ratings finais (para o model.json) e o rating de cada time ANTES de
cada jogo (features causais para o ML, sem vazamento de informacao).
"""

from __future__ import annotations


def expected_home(elo_home: float, elo_away: float, hfa: float) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_away - (elo_home + hfa)) / 400.0))


def run(matches_sorted: list[dict], k: float, hfa: float, base: float = 1500.0):
    """matches_sorted: jogos finalizados ordenados por data (mais antigo primeiro)."""
    ratings: dict[int, float] = {}
    prematch: list[tuple[float, float]] = []

    for m in matches_sorted:
        rh = ratings.get(m["homeId"], base)
        ra = ratings.get(m["awayId"], base)
        prematch.append((rh, ra))

        exp_h = expected_home(rh, ra, hfa)
        if m["homeGoals"] > m["awayGoals"]:
            score_h = 1.0
        elif m["homeGoals"] < m["awayGoals"]:
            score_h = 0.0
        else:
            score_h = 0.5

        ratings[m["homeId"]] = rh + k * (score_h - exp_h)
        ratings[m["awayId"]] = ra + k * ((1.0 - score_h) - (1.0 - exp_h))

    return ratings, prematch


def elo_1x2(elo_home: float, elo_away: float, hfa: float) -> dict:
    """Probabilidades 1X2 a partir do Elo, com estimativa de empate."""
    exp_h = expected_home(elo_home, elo_away, hfa)
    draw = max(0.15, min(0.30, 0.30 - 0.20 * abs(exp_h - 0.5)))
    home = exp_h * (1 - draw)
    away = (1 - exp_h) * (1 - draw)
    total = home + draw + away
    return {"home": home / total, "draw": draw / total, "away": away / total}
