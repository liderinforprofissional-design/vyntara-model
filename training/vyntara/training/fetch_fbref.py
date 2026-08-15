"""Captacao de dados do FBref (xG por jogo) via soccerdata.

IMPORTANTE:
 - O FBref BLOQUEIA robos. Rode ESTE script no SEU PC (IP de casa), NAO no GitHub
   Actions (IPs de datacenter sao bloqueados). Depois comite o fbref_data.json
   gerado no repositorio - o pipeline diario so LE esse arquivo.
 - Instale antes:  pip install soccerdata pandas
 - soccerdata respeita o rate limit do FBref -> fica lento, e normal.

Uso:
    cd training
    python fetch_fbref.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys

# Se falhar, rode no terminal:
#   python -c "import soccerdata as sd; print(sd.FBref.available_leagues())"
# e ajuste o codigo da liga abaixo para o que aparecer para o Brasil.
LEAGUE = "BRA-Série A"
SEASONS = ["2024", "2025"]


def main():
    try:
        import pandas as pd
        import soccerdata as sd
    except ImportError:
        print("Instale as dependencias:  pip install soccerdata pandas")
        sys.exit(1)

    with open("fbref_teams.json", encoding="utf-8") as f:
        team_map = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

    print(f"Buscando FBref {LEAGUE} {SEASONS} ... (lento por causa do rate limit)")
    try:
        fbref = sd.FBref(leagues=LEAGUE, seasons=SEASONS)
        sched = fbref.read_schedule().reset_index()
    except Exception as e:
        print("Falhou ao ler o FBref:", e)
        print("Verifique o codigo da liga (available_leagues) e ajuste LEAGUE no topo.")
        sys.exit(1)

    cols = {str(c).lower(): c for c in sched.columns}

    def col(*cands):
        for c in cands:
            if c in cols:
                return cols[c]
        return None

    c_home = col("home_team", "home")
    c_away = col("away_team", "away")
    c_date = col("date")
    c_hxg = col("home_xg")
    c_axg = col("away_xg")

    print("Colunas encontradas:", list(sched.columns))
    if not (c_home and c_away and c_date):
        print("Nao achei colunas de time/data. Me mande a lista de colunas acima.")
        sys.exit(1)

    print("\nTimes no FBref (confira o mapeamento em fbref_teams.json):")
    for t in sorted(set(sched[c_home].dropna().astype(str))):
        print("  -", t, "->", team_map.get(t, "??? NAO MAPEADO"))

    matches, unmapped = [], set()
    for _, row in sched.iterrows():
        home, away = str(row[c_home]), str(row[c_away])
        hid, aid = team_map.get(home), team_map.get(away)
        if hid is None:
            unmapped.add(home)
        if aid is None:
            unmapped.add(away)
        if hid is None or aid is None or not (c_hxg and c_axg):
            continue
        hxg, axg = row.get(c_hxg), row.get(c_axg)
        if pd.isna(hxg) or pd.isna(axg):
            continue
        try:
            d = str(pd.to_datetime(row[c_date]).date())
        except Exception:
            continue
        matches.append({"date": d, "homeId": hid, "awayId": aid,
                        "homeXg": float(hxg), "awayXg": float(axg)})

    with open("fbref_data.json", "w", encoding="utf-8") as f:
        json.dump({"generatedAt": dt.date.today().isoformat(), "matches": matches},
                  f, ensure_ascii=False, indent=2)

    print(f"\nOK: {len(matches)} jogos com xG salvos em fbref_data.json.")
    if unmapped:
        print("Times SEM mapeamento (ajuste fbref_teams.json):", sorted(unmapped))


if __name__ == "__main__":
    main()
