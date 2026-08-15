"""Pilar 2 (ML) - engenharia de features causais.

Para cada jogo, monta features usando SO informacao anterior a ele (forma
recente, gols marcados/sofridos, descanso) + o Elo pre-jogo. Isso evita
vazamento de informacao no backtest.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional

FEATURE_NAMES = [
    "elo_home", "elo_away", "elo_diff",
    "form_home", "gf_home", "ga_home",
    "form_away", "gf_away", "ga_away",
    "rest_home", "rest_away",
    # H2H (confronto direto) - calculado dos jogos ja baixados, sem custo extra
    "h2h_home_winrate", "h2h_avg_goals", "h2h_count",
]


class FeatureBuilder:
    def __init__(self, window: int = 5):
        self.window = window
        self.hist: dict[int, list[tuple[float, float, float]]] = {}
        self.last_date: dict[int, Optional[dt.datetime]] = {}
        # historico de confronto direto por par de times (ordenado)
        self.h2h: dict[tuple[int, int], list[tuple[int, int, int]]] = {}

    @staticmethod
    def _pair(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a <= b else (b, a)

    def _h2h_stats(self, home_id: int, away_id: int) -> tuple[float, float, float]:
        """Vitorias do MANDANTE atual, media de gols e nº de jogos no confronto."""
        past = self.h2h.get(self._pair(home_id, away_id), [])
        if not past:
            return (0.5, 2.5, 0.0)  # neutro quando nunca se enfrentaram
        home_wins = 0
        goals_total = 0.0
        for (past_home, hg, ag) in past:
            goals_total += hg + ag
            if past_home == home_id:
                if hg > ag:
                    home_wins += 1
            else:  # o mandante atual jogou fora naquele confronto
                if ag > hg:
                    home_wins += 1
        n = len(past)
        return (home_wins / n, goals_total / n, float(min(n, 10)))

    def _stats(self, tid: int) -> tuple[float, float, float]:
        h = self.hist.get(tid, [])
        if not h:
            return (1.0, 1.2, 1.2)
        n = len(h)
        return (sum(x[0] for x in h) / n, sum(x[1] for x in h) / n, sum(x[2] for x in h) / n)

    def _rest(self, tid: int, date: Optional[dt.datetime]) -> float:
        last = self.last_date.get(tid)
        if last is None or date is None:
            return 7.0
        return float(max(0, min(30, (date - last).days)))

    def features(self, m: dict, elo_home: float, elo_away: float) -> list[float]:
        fh = self._stats(m["homeId"])
        fa = self._stats(m["awayId"])
        wr, avg_g, count = self._h2h_stats(m["homeId"], m["awayId"])
        return [
            elo_home, elo_away, elo_home - elo_away,
            fh[0], fh[1], fh[2],
            fa[0], fa[1], fa[2],
            self._rest(m["homeId"], m["date"]), self._rest(m["awayId"], m["date"]),
            wr, avg_g, count,
        ]

    def update(self, m: dict) -> None:
        hg, ag = m["homeGoals"], m["awayGoals"]
        hp = 3.0 if hg > ag else (1.0 if hg == ag else 0.0)
        ap = 3.0 if ag > hg else (1.0 if hg == ag else 0.0)
        self._push(m["homeId"], hp, hg, ag, m["date"])
        self._push(m["awayId"], ap, ag, hg, m["date"])
        # registra o confronto direto (para os proximos jogos entre eles)
        self.h2h.setdefault(self._pair(m["homeId"], m["awayId"]), []).append(
            (m["homeId"], int(hg), int(ag))
        )

    def _push(self, tid, pts, gf, ga, date):
        lst = self.hist.setdefault(tid, [])
        lst.append((pts, float(gf), float(ga)))
        if len(lst) > self.window:
            lst.pop(0)
        if date is not None:
            self.last_date[tid] = date


def label(m: dict) -> int:
    """0 = casa vence, 1 = empate, 2 = fora vence."""
    if m["homeGoals"] > m["awayGoals"]:
        return 0
    if m["homeGoals"] == m["awayGoals"]:
        return 1
    return 2


def build_training(matches_sorted: list[dict], prematch_elo: list[tuple[float, float]]):
    """Retorna (X, y, fb) onde fb ja contem o estado apos todos os jogos."""
    fb = FeatureBuilder()
    X, y = [], []
    for m, (eh, ea) in zip(matches_sorted, prematch_elo):
        X.append(fb.features(m, eh, ea))
        y.append(label(m))
        fb.update(m)
    return X, y, fb
