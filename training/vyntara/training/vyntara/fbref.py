"""Le o fbref_data.json (gerado por fetch_fbref.py) e fornece xG rolante por time.

Usado (na proxima fase) como features do ML: xG feito/sofrido nos ultimos jogos,
sempre ANTES da data do jogo (causal, sem vazamento). Se o arquivo nao existir,
fica indisponivel e o pipeline segue sem esse sinal.
"""

from __future__ import annotations

import json
import os
from typing import Optional


class FbrefStats:
    def __init__(self, path: str = "fbref_data.json"):
        # teamId -> lista ordenada de (date, xg_for, xg_against)
        self.by_team: dict[int, list[tuple[str, float, float]]] = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for m in data.get("matches", []):
                self.by_team.setdefault(m["homeId"], []).append(
                    (m["date"], m["homeXg"], m["awayXg"]))
                self.by_team.setdefault(m["awayId"], []).append(
                    (m["date"], m["awayXg"], m["homeXg"]))
            for tid in self.by_team:
                self.by_team[tid].sort(key=lambda r: r[0])

    @property
    def available(self) -> bool:
        return bool(self.by_team)

    def rolling_xg(self, team_id: int, before_date: str,
                   window: int = 6) -> Optional[tuple[float, float]]:
        """Media de xG feito/sofrido nos ultimos `window` jogos ANTES de before_date."""
        rows = [r for r in self.by_team.get(team_id, []) if r[0] < before_date]
        if not rows:
            return None
        rows = rows[-window:]
        n = len(rows)
        return (sum(r[1] for r in rows) / n, sum(r[2] for r in rows) / n)
