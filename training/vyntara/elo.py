"""Pilar 3 - Sistema de rating Elo dinamico (com margem de vitoria).

Percorre os jogos em ordem cronologica: quem vence ganha pontos de quem perde.
Alem do resultado, a MARGEM de gols pesa: golear move mais o rating que ganhar
de 1 (com correcao para nao inflar favoritos que so confirmam o esperado).
Retorna os ratings finais (para o model.json) e o rating de cada time ANTES de
cada jogo (features causais para o ML, sem vazamento de informacao).
"""

from __future__ import annotations

import math


def expected_home(elo_home: float, elo_away: float, hfa: float) -> float:
    return 1.0 / (1.0 + 10 ** ((elo_away - (elo_home + hfa)) / 400.0))


def _mov_multiplier(goal_diff: int, winner_elo: float, loser_elo: float) -> float:
    """Multiplicador de margem de vitoria (estilo FiveThirtyEight).
    Empate (gd=0) -> 1.0. Vitorias maiores -> multiplicador maior, com correcao
    para o favorito ganhar menos pontos ao apenas confirmar o favoritismo."""
    if goal_diff == 0:
        return 1.0
    return math.log(goal_diff + 1) * (2.2 / (0.001 * (winner_elo - loser_elo) + 2.2))


def run(matches_sorted: list[dict], k: float, hfa: float, base: float = 1500.0):
    """matches_sorted: jogos finalizados ordenados por data (mais antigo primeiro)."""
    ratings: dict[int, float] = {}
    prematch: list[tuple[float, float]] = []

    for m in matches_sorted:
        rh = ratings.get(m["homeId"], base)
        ra = ratings.get(m["awayId"], base)
        prematch.append((rh, ra))

        exp_h = expected_home(rh, ra, hfa)
        hg, ag = m["homeGoals"], m["awayGoals"]
        gd = abs(hg - ag)

        if hg > ag:
            score_h = 1.0
            winner_elo, loser_elo = rh + hfa, ra
        elif hg < ag:
            score_h = 0.0
            winner_elo, loser_elo = ra, rh + hfa
        else:
            score_h = 0.5
            winner_elo, loser_elo = rh + hfa, ra  # nao usado (gd=0 -> mult 1.0)

        k_eff = k * _mov_multiplier(gd, winner_elo, loser_elo)
        ratings[m["homeId"]] = rh + k_eff * (score_h - exp_h)
        ratings[m["awayId"]] = ra + k_eff * ((1.0 - score_h) - (1.0 - exp_h))

    return ratings, prematch


def elo_1x2(elo_home: float, elo_away: float, hfa: float) -> dict:
    """Probabilidades 1X2 a partir do Elo, com estimativa de empate."""
    exp_h = expected_home(elo_home, elo_away, hfa)
    draw = max(0.15, min(0.30, 0.30 - 0.20 * abs(exp_h - 0.5)))
    home = exp_h * (1 - draw)
    away = (1 - exp_h) * (1 - draw)
    total = home + draw + away
    return {"home": home / total, "draw": draw / total, "away": away / total}
