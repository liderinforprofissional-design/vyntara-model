"""Orquestrador do pipeline Vyntara (Fase 1).

Passos:
 1. Puxa o historico (por liga/temporada) da API-Football.
 2. Treina os tres pilares: Poisson (decaimento 12m), Elo e ML.
 3. Faz BACKTEST honesto (split cronologico 80/20) e imprime as metricas.
 4. Gera:
      output/model.json       -> forcas Poisson + Elo (o app ja consome hoje)
      output/predictions.json -> previsoes do ensemble para os proximos jogos
                                 (base da proxima fase do app)

Uso:
    export API_FOOTBALL_KEY=xxxx          (Windows: set API_FOOTBALL_KEY=xxxx)
    python build_model.py
"""

from __future__ import annotations

import datetime as dt
import json
import os

from vyntara import backtest, elo, ensemble, features, poisson
from vyntara.analysis_gpt import analyze
from vyntara.apifootball import ApiFootball


def load_config() -> dict:
    path = "config.json" if os.path.exists("config.json") else "config.example.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def best_bet(probs: dict, over25: float, btts: float) -> dict:
    top = max(("home", "draw", "away"), key=lambda k: probs[k])
    label = {"home": "Vitoria Casa", "draw": "Empate", "away": "Vitoria Fora"}[top]
    cands = [(label, "Resultado", probs[top])]
    cands.append(("+2.5 gols", "Gols", over25) if over25 >= 0.5 else ("-2.5 gols", "Gols", 1 - over25))
    cands.append(("Ambos marcam", "Ambos marcam", btts) if btts >= 0.5
                 else ("Nao ambos marcam", "Ambos marcam", 1 - btts))
    b = max(cands, key=lambda c: c[2])
    return {"label": b[0], "market": b[1], "probability": round(b[2], 4)}


def pillar_probs(pois_league, elo_pre, clf, feat):
    """Retorna (pois, elo_p, ml_p, extra) para um jogo."""
    lh, la = poisson.expected_goals(pois_league, feat["homeId"], feat["awayId"])
    sc = poisson.scoreline_probs(lh, la)
    pois_p = {"home": sc["home"], "draw": sc["draw"], "away": sc["away"]}
    elo_p = elo.elo_1x2(elo_pre[0], elo_pre[1], feat["hfa"])
    ml_p = ensemble.ml_probs(clf, feat["x"]) if clf is not None else None
    extra = {"lh": lh, "la": la, "over25": sc["over25"], "btts": sc["btts"], "score": sc["score"]}
    return pois_p, elo_p, ml_p, extra


def main():
    cfg = load_config()
    api = ApiFootball(os.environ.get("API_FOOTBALL_KEY", ""), cfg.get("cacheDir", "cache"))
    half_life = cfg.get("halfLifeDays", 180)
    k = cfg.get("eloK", 24)
    hfa = cfg.get("eloHomeAdvantage", 65)
    weights = cfg.get("ensembleWeights", {"poisson": 0.34, "elo": 0.33, "ml": 0.33})
    use_stacker = cfg.get("useLogisticStacker", True)
    use_odds = cfg.get("useOdds", True)
    odds_weight = cfg.get("oddsWeight", 0.4)
    out_dir = cfg.get("outputDir", "output")
    os.makedirs(out_dir, exist_ok=True)

    model_leagues: dict[str, dict] = {}
    predictions: dict[str, dict] = {}
    bt_all_preds: list[dict] = []
    bt_all_y: list[int] = []

    for lg in cfg["leagues"]:
        lid, seasons = lg["id"], lg["seasons"]
        print(f"\n=== Liga {lid} ({lg.get('name','')}) ===")

        # 1) historico
        matches = []
        for s in seasons:
            try:
                got = api.finished_fixtures(lid, s)
                print(f"  temporada {s}: {len(got)} jogos")
                matches += got
            except Exception as e:
                print(f"  ! temporada {s} falhou: {e}")
        matches = [m for m in matches if m["date"] and m["homeGoals"] is not None]
        matches.sort(key=lambda m: m["date"])
        if len(matches) < 30:
            print("  ! poucos jogos, pulando liga.")
            continue

        # 2) pilares (FULL, para producao)
        pois_full = poisson.fit_league(matches, half_life)
        elo_full, elo_pre_full = elo.run(matches, k, hfa)
        X_full, y_full, fb_full = features.build_training(matches, elo_pre_full)
        clf_full = _try_train_ml(X_full, y_full)

        # 3) backtest (split cronologico 80/20)
        _backtest_league(matches, half_life, k, hfa, weights, use_stacker,
                         bt_all_preds, bt_all_y)

        # 4a) model.json (schema do app)
        teams_out = {}
        for tid, t in pois_full["teams"].items():
            teams_out[str(tid)] = {
                "name": t["name"],
                "attackHome": round(t["attackHome"], 4),
                "defenseHome": round(t["defenseHome"], 4),
                "attackAway": round(t["attackAway"], 4),
                "defenseAway": round(t["defenseAway"], 4),
                "elo": round(elo_full.get(tid, 1500.0), 1),
            }
        model_leagues[str(lid)] = {
            "name": lg.get("name", ""),
            "avgHomeGoals": round(pois_full["avgHomeGoals"], 4),
            "avgAwayGoals": round(pois_full["avgAwayGoals"], 4),
            "teams": teams_out,
        }

        # 4b) predictions.json (ensemble) para os proximos jogos
        stacker = None
        if use_stacker:
            rows = [(pp, ep, mp) for (pp, ep, mp) in _pillars_over(matches, pois_full, elo_pre_full, clf_full, hfa)]
            stacker = ensemble.fit_stacker(rows, y_full)

        # Proximos jogos sao da temporada ATUAL (ano corrente), nao da ultima treinada.
        season = dt.date.today().year
        try:
            upcoming = api.upcoming_fixtures(lid, season, cfg.get("predictAheadDays", 7))
        except Exception as e:
            print(f"  ! nao consegui buscar proximos jogos: {e}")
            upcoming = []

        for u in upcoming:
            feat = {
                "homeId": u["homeId"], "awayId": u["awayId"], "hfa": hfa,
                "x": fb_full.features(u, elo_full.get(u["homeId"], 1500.0),
                                      elo_full.get(u["awayId"], 1500.0)),
            }
            elo_pre = (elo_full.get(u["homeId"], 1500.0), elo_full.get(u["awayId"], 1500.0))
            pois_p, elo_p, ml_p, extra = pillar_probs(pois_full, elo_pre, clf_full, feat)
            if stacker is not None:
                final = ensemble.stacker_probs(stacker, pois_p, elo_p, ml_p)
            else:
                final = ensemble.weighted_average(pois_p, elo_p, ml_p, weights)

            # 4o sinal: odds do mercado (casas de apostas), se disponivel.
            market = api.odds_1x2(u["id"]) if use_odds else None
            if market:
                w = odds_weight
                blended = {k: (1 - w) * final[k] + w * market[k] for k in ("home", "draw", "away")}
                tot = sum(blended.values()) or 1.0
                final = {k: v / tot for k, v in blended.items()}

            bb = best_bet(final, extra["over25"], extra["btts"])
            text = ""
            if cfg.get("useGptAnalysis", False):
                text = analyze(u["homeName"], u["awayName"], final,
                               {"home": extra["lh"], "away": extra["la"]}, bb)

            predictions[str(u["id"])] = {
                "home": u["homeName"], "away": u["awayName"],
                "leagueId": lid,
                "leagueName": u["leagueName"],
                "kickoff": u["date"].isoformat() if u["date"] else None,
                "probs": {kk: round(vv, 4) for kk, vv in final.items()},
                "expected": {"home": round(extra["lh"], 2), "away": round(extra["la"], 2)},
                "over25": round(extra["over25"], 4),
                "btts": round(extra["btts"], 4),
                "mostLikelyScore": extra["score"],
                "bestBet": bb,
                "market": {kk: round(vv, 4) for kk, vv in market.items()} if market else None,
                "analysis": text,
            }

        print(f"  previsoes geradas: {len(upcoming)} jogos")

    # metricas globais do backtest
    if bt_all_y:
        print("\n=== BACKTEST (ensemble, conjunto de teste) ===")
        print(" ", backtest.evaluate(bt_all_preds, bt_all_y))

    today = dt.date.today().isoformat()
    _write(os.path.join(out_dir, "model.json"),
           {"version": today, "generatedAt": today, "leagues": model_leagues})
    _write(os.path.join(out_dir, "predictions.json"),
           {"generatedAt": today, "fixtures": predictions})
    print(f"\nOK! Arquivos em '{out_dir}/'. Suba o model.json no seu repo do GitHub.")


# ---- auxiliares -------------------------------------------------------------
def _try_train_ml(X, y):
    try:
        return ensemble.train_ml(X, y)
    except Exception as e:
        print(f"  ! ML desativado ({e}); usando so Poisson+Elo.")
        return None


def _pillars_over(matches, pois_league, elo_pre, clf, hfa):
    """Gera (pois, elo, ml) para cada jogo do historico (para treinar o stacker)."""
    fb = features.FeatureBuilder()
    out = []
    for m, ep in zip(matches, elo_pre):
        feat = {"homeId": m["homeId"], "awayId": m["awayId"], "hfa": hfa,
                "x": fb.features(m, ep[0], ep[1])}
        pp, epr, mp, _ = pillar_probs(pois_league, ep, clf, feat)
        out.append((pp, epr, mp))
        fb.update(m)
    return out


def _backtest_league(matches, half_life, k, hfa, weights, use_stacker, all_preds, all_y):
    cut = int(len(matches) * 0.8)
    train, test = matches[:cut], matches[cut:]
    if len(test) < 10:
        return
    pois_tr = poisson.fit_league(train, half_life)
    _, elo_pre_all = elo.run(matches, k, hfa)            # causal em toda a sequencia
    X_all, y_all, _ = features.build_training(matches, elo_pre_all)
    clf = _try_train_ml(X_all[:cut], y_all[:cut])

    fb = features.FeatureBuilder()
    # reconstroi features causais alinhadas a `matches`
    feats = []
    for m, ep in zip(matches, elo_pre_all):
        feats.append(fb.features(m, ep[0], ep[1]))
        fb.update(m)

    # stacker treinado so no train
    stacker = None
    if use_stacker:
        rows = []
        for i in range(cut):
            m = matches[i]
            f = {"homeId": m["homeId"], "awayId": m["awayId"], "hfa": hfa, "x": feats[i]}
            pp, ep, mp, _ = pillar_probs(pois_tr, elo_pre_all[i], clf, f)
            rows.append((pp, ep, mp))
        stacker = ensemble.fit_stacker(rows, y_all[:cut])

    for i in range(cut, len(matches)):
        m = matches[i]
        f = {"homeId": m["homeId"], "awayId": m["awayId"], "hfa": hfa, "x": feats[i]}
        pp, ep, mp, _ = pillar_probs(pois_tr, elo_pre_all[i], clf, f)
        final = ensemble.stacker_probs(stacker, pp, ep, mp) if stacker is not None \
            else ensemble.weighted_average(pp, ep, mp, weights)
        all_preds.append(final)
        all_y.append(y_all[i])


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
