"""Pilar 1 - Poisson com decaimento temporal (ultimos ~12 meses pesam mais).

Calcula, por liga, a media de gols e a forca de ataque/defesa de cada time
(separadas por mando), no mesmo formato que o app usa em model.json.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Optional


def _weight(match_date: Optional[dt.datetime], ref: dt.datetime, half_life_days: float) -> float:
    """Peso exponencial: metade a cada `half_life_days`. Jogo recente pesa mais."""
    if match_date is None:
        return 0.0
    age = (ref - match_date).days
    if age < 0:
        age = 0
    return 0.5 ** (age / half_life_days)


def fit_league(matches: list[dict], half_life_days: float,
               ref: Optional[dt.datetime] = None) -> dict:
    """Ajusta os parametros de Poisson de UMA liga a partir dos jogos finalizados."""
    played = [m for m in matches
              if m["homeGoals"] is not None and m["awayGoals"] is not None and m["date"]]
    if not played:
        return {"avgHomeGoals": 1.4, "avgAwayGoals": 1.1, "teams": {}}

    if ref is None:
        ref = max(m["date"] for m in played)

    # Media da liga (ponderada)
    wsum = sum(_weight(m["date"], ref, half_life_days) for m in played) or 1e-9
    avg_home = sum(_weight(m["date"], ref, half_life_days) * m["homeGoals"] for m in played) / wsum
    avg_away = sum(_weight(m["date"], ref, half_life_days) * m["awayGoals"] for m in played) / wsum
    avg_home = max(avg_home, 0.2)
    avg_away = max(avg_away, 0.2)

    # Acumuladores por time
    acc: dict[int, dict] = {}

    def slot(tid, name):
        if tid not in acc:
            acc[tid] = {"name": name,
                        "hs_w": 0.0, "hs": 0.0,  # home scored
                        "hc_w": 0.0, "hc": 0.0,  # home conceded
                        "as_w": 0.0, "as": 0.0,  # away scored
                        "ac_w": 0.0, "ac": 0.0}  # away conceded
        return acc[tid]

    for m in played:
        w = _weight(m["date"], ref, half_life_days)
        h = slot(m["homeId"], m["homeName"])
        a = slot(m["awayId"], m["awayName"])
        h["hs_w"] += w; h["hs"] += w * m["homeGoals"]
        h["hc_w"] += w; h["hc"] += w * m["awayGoals"]
        a["as_w"] += w; a["as"] += w * m["awayGoals"]
        a["ac_w"] += w; a["ac"] += w * m["homeGoals"]

    teams = {}
    for tid, d in acc.items():
        home_scored = d["hs"] / d["hs_w"] if d["hs_w"] else avg_home
        home_conceded = d["hc"] / d["hc_w"] if d["hc_w"] else avg_away
        away_scored = d["as"] / d["as_w"] if d["as_w"] else avg_away
        away_conceded = d["ac"] / d["ac_w"] if d["ac_w"] else avg_home
        teams[tid] = {
            "name": d["name"],
            "attackHome": _clip(home_scored / avg_home),
            "defenseHome": _clip(home_conceded / avg_away),
            "attackAway": _clip(away_scored / avg_away),
            "defenseAway": _clip(away_conceded / avg_home),
        }

    return {"avgHomeGoals": avg_home, "avgAwayGoals": avg_away, "teams": teams}


def _clip(x: float) -> float:
    return max(0.2, min(3.0, x))


def expected_goals(league: dict, home_id: int, away_id: int) -> tuple[float, float]:
    th = league["teams"].get(home_id)
    ta = league["teams"].get(away_id)
    if not th or not ta:
        return league["avgHomeGoals"], league["avgAwayGoals"]
    lh = league["avgHomeGoals"] * th["attackHome"] * ta["defenseAway"]
    la = league["avgAwayGoals"] * ta["attackAway"] * th["defenseHome"]
    return max(0.15, min(6.0, lh)), max(0.15, min(6.0, la))


def _pois_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def scoreline_probs(lh: float, la: float, max_goals: int = 10) -> dict:
    """Probabilidades 1X2 + mercados a partir dos gols esperados."""
    ph = [_pois_pmf(i, lh) for i in range(max_goals + 1)]
    pa = [_pois_pmf(j, la) for j in range(max_goals + 1)]
    p_home = p_draw = p_away = over25 = btts = 0.0
    best_score, best_p = (0, 0), 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = ph[i] * pa[j]
            if i > j:
                p_home += p
            elif i < j:
                p_away += p
            else:
                p_draw += p
            if i + j >= 3:
                over25 += p
            if i >= 1 and j >= 1:
                btts += p
            if p > best_p:
                best_p, best_score = p, (i, j)
    return {
        "home": p_home, "draw": p_draw, "away": p_away,
        "over25": over25, "btts": btts,
        "score": f"{best_score[0]}-{best_score[1]}", "scoreProb": best_p,
    }
