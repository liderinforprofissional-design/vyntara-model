# Guia de implementacao do motor Vyntara (Windows)

Siga na ordem. Sao 3 partes: (A) rodar local uma vez, (B) publicar no GitHub
para o app ler, (C) automatizar com GitHub Actions.

---

## PARTE A — Rodar no seu PC (gerar o model.json)

### 1. Instalar o Python
- Baixe em https://www.python.org/downloads/ (versao 3.11 ou 3.12).
- No instalador, **marque "Add python.exe to PATH"** antes de clicar em Install.
- Teste: abra o **PowerShell** e digite:
  ```powershell
  python --version
  ```
  Tem que aparecer algo como `Python 3.12.x`.

### 2. Abrir o PowerShell na pasta training
- No Explorer, entre em `...\App Projeto\training`.
- Clique no campo do caminho, digite `powershell` e Enter (abre o terminal ja na pasta).

### 3. Instalar as dependencias
```powershell
pip install -r requirements.txt
```
(Para ter o XGBoost tambem: `pip install xgboost`. Sem ele, o pipeline usa RandomForest.)

### 4. Criar o config.json com os SEUS campeonatos
```powershell
copy config.example.json config.json
```
Abra `config.json` e ajuste a lista `leagues` com os IDs da API-Football.
IDs uteis do Brasil:
- **71** = Brasileirao Serie A
- **72** = Brasileirao Serie B
- **73** = Copa do Brasil
- **475** = Paulista A1

> Nao sabe o ID de uma liga? Me diga o nome que eu preencho o config.json pra voce.

`seasons` sao os anos que voce quer treinar (ex: `[2024, 2025]` = ~12+ meses).

### 5. Colocar a chave da API e rodar
```powershell
$env:API_FOOTBALL_KEY="29def6517be151427c72d5747a5017b8"
python build_model.py
```
- O terminal mostra o backtest (ex: `{'accuracy': 0.52, 'logloss': 0.98, ...}`).
- Gera `training\output\model.json` e `training\output\predictions.json`.

> A linha do `$env:` vale so para aquela janela do PowerShell. Se fechar, rode de novo.

---

## PARTE B — Publicar no GitHub (para o app ler)

### 1. Criar o repositorio do modelo
- Em https://github.com, crie um repo chamado `vyntara-model`.
- Deixe **Public** (mais simples; o `model.json` nao tem segredo nenhum).

### 2. Subir o model.json
- No repo, **Add file -> Create new file**, nomeie `public/model.json`
  (a barra cria a pasta `public`). Cole o conteudo do seu `output\model.json` e commit.
- (Ou use **Add file -> Upload files** e arraste o arquivo.)

### 3. Pegar a URL raw e apontar o app
- Abra `public/model.json` no GitHub e clique em **Raw**.
- Copie a URL (fica assim):
  `https://raw.githubusercontent.com/SEU_USUARIO/vyntara-model/main/public/model.json`
- No app, em `ApiConfig.kt`, troque o `MODEL_URL` por essa URL.
- Rebuild do app. Pronto: **as abas Melhores e Top 10 passam a mostrar previsoes reais.**

---

## PARTE C — Automatizar (re-treino diario no GitHub Actions)

### 1. Subir o codigo do pipeline no repo do modelo
- Copie a pasta `training/` inteira para dentro do repo `vyntara-model`.
- Copie o arquivo `training/github-actions-train.yml` para `.github/workflows/train.yml`
  (crie as pastas `.github/workflows` pelo mesmo truque do `Create new file`).

### 2. Guardar a chave como secret
- No repo: **Settings -> Secrets and variables -> Actions -> New repository secret**.
- Nome: `API_FOOTBALL_KEY` | Valor: sua chave. Salve.
- (Se um dia usar a analise em texto, crie tambem `OPENAI_API_KEY`.)

### 3. Rodar
- Aba **Actions -> Treinar modelo Vyntara -> Run workflow** (roda na hora).
- Depois disso ele roda sozinho todo dia e atualiza o `public/model.json`.
- O app sempre le a versao mais recente automaticamente.

---

## Avisos importantes
- **Nao suba o app Android num repo publico** — a sua chave da API esta no `ApiConfig.kt`.
  O repo `vyntara-model` e outra coisa (nao tem chave; a chave la e um "secret").
- Se o Top 10 continuar vazio depois disso, verifique se as ligas do `config.json`
  sao as mesmas que voce escolheu no onboarding do app.
- Duvida em qualquer passo: me manda o print/erro que eu te desbloqueio.
