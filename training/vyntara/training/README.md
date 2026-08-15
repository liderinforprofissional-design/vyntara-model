# Vyntara - Pipeline de treino (Fase 1)

Motor de previsao do app. Roda em Python (no seu PC ou no GitHub Actions),
puxa o historico da API-Football, treina os tres pilares, faz backtest e gera
os arquivos que o app le.

## Os tres pilares (combinados num ensemble)
- **Poisson** (`vyntara/poisson.py`) — forca de ataque/defesa por mando, com
  **decaimento temporal** (os ultimos ~12 meses pesam mais).
- **Elo** (`vyntara/elo.py`) — rating dinamico; quem vence ganha pontos de quem perde.
- **ML** (`vyntara/features.py` + `vyntara/ensemble.py`) — XGBoost (ou RandomForest)
  aprende com forma recente, gols, descanso e diferenca de Elo.
- **Ensemble** — combina os tres. Por padrao usa uma **regressao logistica (stacker)**
  que aprende os pesos; se faltar biblioteca, cai para media ponderada.
- **Backtest** (`vyntara/backtest.py`) — mede acerto, log-loss e brier num conjunto
  de teste que o modelo nao viu. "Robusto" = medido, nao so complexo.

## Rodar no seu PC
```bash
cd training
pip install -r requirements.txt
cp config.example.json config.json        # ajuste suas ligas/temporadas (IDs da API-Football)

# a chave da API-Football vai por variavel de ambiente:
#   Windows (PowerShell):  $env:API_FOOTBALL_KEY="sua_chave"
#   Linux/Mac:             export API_FOOTBALL_KEY=sua_chave
python build_model.py
```
Saidas em `training/output/`:
- `model.json` — forcas Poisson + Elo. **E o que o app ja consome hoje.**
- `predictions.json` — previsoes do ensemble para os proximos jogos (base da proxima fase do app).

O terminal mostra as metricas do backtest, algo como:
`{'n': 120, 'accuracy': 0.52, 'logloss': 0.98, 'brier': 0.62}`

## Ligar no app (agora)
1. Crie um repositorio no GitHub, ex: `vyntara-model`.
2. Suba o `model.json` gerado (ex: em `public/model.json`).
3. No app, edite `ApiConfig.kt` -> `MODEL_URL` para a URL **raw**:
   `https://raw.githubusercontent.com/SEU_USUARIO/vyntara-model/main/public/model.json`
4. Rebuild do app: agora as abas Melhores/Top 10 mostram previsoes reais.

## Automatizar (GitHub Actions - diario)
1. No repo do modelo, copie `github-actions-train.yml` para `.github/workflows/train.yml`
   e copie a pasta `training/` para a raiz do repo.
2. Em **Settings -> Secrets and variables -> Actions**, crie o secret
   `API_FOOTBALL_KEY` (e, se for usar analise, `OPENAI_API_KEY`).
3. Pronto: todo dia o robo re-treina e atualiza o `model.json`/`predictions.json`.

## Notas honestas / limites
- **Plano gratis (100 req/dia + temporadas limitadas):** treinar e barato (1 req por
  liga/temporada). Se uma temporada nao vier no plano gratis, o script avisa e pula.
- **GPT-4o-mini:** so escreve a analise em texto (nunca o numero). Desligado por padrao
  (`useGptAnalysis: false`). A chave OpenAI fica aqui no pipeline, **nunca no app**.
- **Escalacao / lesao / sinergia de jogadores:** proximas fases. Exigem mais requisicoes
  (dados so saem perto do jogo) e provavelmente o plano Pro para escala.
- **Proxima fase do app:** trocar o calculo on-device por leitura do `predictions.json`
  (ai o app passa a exibir o ensemble completo + a analise em texto).
