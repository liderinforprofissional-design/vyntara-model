"""Cliente da API-Football com cache em disco.

Objetivo: puxar o historico (jogos ja finalizados) e os proximos jogos por
liga/temporada, gastando o minimo de requisicoes (1 por liga/temporada).
Os dados vem com os IDs nativos da API-Football, entao casam 100% com o app.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time
from typing import Any, Optional

import requests

BASE_URL = "https://v3.football.api-sports.io"
FINISHED = {"FT", "AET", "PEN"}


class ApiFootball:
    def __init__(self, api_key: str, cache_dir: str = "cache"):
        if not api_key:
            raise RuntimeError("Defina a variavel de ambiente API_FOOTBALL_KEY.")
        self.api_key = api_key
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    # ---- baixa (com cache) --------------------------------------------------
    def _get(self, path: str, params: dict, cache: bool = True) -> dict:
        key = hashlib.md5(f"{path}?{json.dumps(params, sort_keys=True)}".encode()).hexdigest()
        cache_file = os.path.join(self.cache_dir, f"{key}.json")
        if cache and os.path.exists(cache_file):
            with open(cache_file, encoding="utf-8") as f:
                return json.load(f)

        resp = requests.get(
            f"{BASE_URL}/{path}",
            headers={"x-apisports-key": self.api_key},
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        errors = data.get("errors")
        if errors:  # API-Football devolve 200 com erro no campo errors
            raise RuntimeError(f"API-Football erro: {errors}")
        if cache:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        time.sleep(0.3)  # respeita o limite por minuto
        return data

    # ---- fixtures -----------------------------------------------------------
    def finished_fixtures(self, league_id: int, season: int) -> list[dict]:
        """Todos os jogos ja finalizados de uma liga/temporada (1 requisicao)."""
        data = self._get("fixtures", {"league": league_id, "season": season})
        return [normalize(x) for x in data.get("response", []) if _is_finished(x)]

    def upcoming_fixtures(self, league_id: int, season: int, days_ahead: int) -> list[dict]:
        """Proximos jogos (nao finalizados) nos proximos N dias. Sem cache (muda sempre)."""
        today = dt.date.today()
        to = today + dt.timedelta(days=days_ahead)
        data = self._get(
            "fixtures",
            {
                "league": league_id,
                "season": season,
                "from": today.isoformat(),
                "to": to.isoformat(),
            },
            cache=False,
        )
        return [normalize(x) for x in data.get("response", []) if not _is_finished(x)]

    def odds_1x2(self, fixture_id: int) -> dict | None:
        """Probabilidades 1X2 do mercado (casas de apostas) para um jogo, ou None.
        Converte a odd decimal em probabilidade e remove a margem da casa."""
        try:
            data = self._get("odds", {"fixture": fixture_id, "bet": 1}, cache=False)
        except Exception:
            return None
        return market_probs_from_odds(data.get("response", []))


def _is_finished(item: dict) -> bool:
    short = (((item.get("fixture") or {}).get("status")) or {}).get("short")
    return short in FINISHED


def normalize(item: dict) -> dict:
    """Converte o item cru da API num dicionario simples."""
    fx = item.get("fixture", {})
    lg = item.get("league", {})
    teams = item.get("teams", {})
    goals = item.get("goals", {})
    home = teams.get("home", {})
    away = teams.get("away", {})
    date_raw = fx.get("date")
    return {
        "id": fx.get("id"),
        "date": _parse_date(date_raw),
        "leagueId": lg.get("id"),
        "leagueName": lg.get("name"),
        "homeId": home.get("id"),
        "homeName": home.get("name"),
        "awayId": away.get("id"),
        "awayName": away.get("name"),
        "homeGoals": goals.get("home"),
        "awayGoals": goals.get("away"),
    }


def _parse_date(s: Optional[str]) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def market_probs_from_odds(resp: list) -> Optional[dict]:
    """Media das odds 1X2 entre as casas -> probabilidade implicita normalizada."""
    home, draw, away = [], [], []
    for item in resp:
        for bk in item.get("bookmakers", []):
            for bet in bk.get("bets", []):
                if bet.get("name") != "Match Winner":
                    continue
                for v in bet.get("values", []):
                    try:
                        o = float(v.get("odd"))
                    except (TypeError, ValueError):
                        continue
                    label = v.get("value")
                    if label == "Home":
                        home.append(o)
                    elif label == "Draw":
                        draw.append(o)
                    elif label == "Away":
                        away.append(o)
    if not (home and draw and away):
        return None
    oh = sum(home) / len(home)
    od = sum(draw) / len(draw)
    oa = sum(away) / len(away)
    ih, idr, ia = 1 / oh, 1 / od, 1 / oa
    s = ih + idr + ia
    if s <= 0:
        return None
    return {"home": ih / s, "draw": idr / s, "away": ia / s}
