# Plano C — tudo pelo GitHub (sem instalar nada no PC)

O GitHub Actions instala o Python, roda o pipeline e atualiza o `model.json`
sozinho todo dia. Voce so configura uma vez, pelo navegador.

---

## 1. Criar a conta e o repositorio
1. Se ainda nao tem, crie conta em https://github.com.
2. Clique em **New repository**.
3. Nome: `vyntara-model` | Visibilidade: **Public** | clique **Create repository**.
   (Publico e o mais simples; nao ha segredo nenhum no modelo — a chave fica separada.)

## 2. Subir a pasta `training`
1. No repo novo, clique **Add file -> Upload files**.
2. No seu PC, abra `...\App Projeto` e **arraste a pasta `training` inteira** para a
   area de upload do GitHub (ele mantem as subpastas).
3. Escreva uma mensagem qualquer e clique **Commit changes**.

> No fim, o repo deve ter: `training/build_model.py`, `training/config.json`,
> `training/requirements.txt`, `training/vyntara/...`

## 3. Criar o workflow (o "robo" diario)
1. **Add file -> Create new file**.
2. No nome do arquivo, digite exatamente: `.github/workflows/train.yml`
   (as barras criam as pastas automaticamente).
3. Abra o arquivo `training/github-actions-train.yml` (no seu PC), copie TODO o conteudo
   e cole aqui. Clique **Commit changes**.

## 4. Guardar a chave da API como "secret"
1. No repo: **Settings -> Secrets and variables -> Actions**.
2. **New repository secret**.
3. Name: `API_FOOTBALL_KEY` | Secret: sua chave da API-Football. Clique **Add secret**.

## 5. Liberar permissao de escrita (importante)
1. **Settings -> Actions -> General**.
2. Role ate **Workflow permissions**.
3. Marque **Read and write permissions** e salve.
   (Sem isso o robo nao consegue salvar o model.json.)

## 6. Rodar pela primeira vez
1. Aba **Actions**. Se aparecer um aviso, clique em **I understand... enable**.
2. Clique em **Treinar modelo Vyntara -> Run workflow -> Run workflow**.
3. Espere ~1 a 2 min. Bolinha **verde** = deu certo.
4. Confira: o repo agora tem `public/model.json` e `public/predictions.json`.

## 7. Apontar o app para o modelo
1. Abra `public/model.json` no GitHub e clique no botao **Raw**.
2. Copie a URL da barra (fica assim):
   `https://raw.githubusercontent.com/SEU_USUARIO/vyntara-model/main/public/model.json`
3. No app, em `ApiConfig.kt`, troque o `MODEL_URL` por essa URL. Salve e faca **Rebuild**.
4. Pronto: as abas **Melhores** e **Top 10** passam a mostrar previsoes reais.

## Daqui pra frente
- O robo roda **sozinho todo dia** (09:00 UTC / 06:00 Brasilia) e atualiza o modelo.
- Quer rodar na hora? Aba **Actions -> Run workflow**.
- Quer mudar as ligas? Edite `training/config.json` no proprio GitHub (botao do lapis).

## Camada de midia (GPT-4o-mini) - opcional
O robo pode ler as manchetes dos times (Google News, gratis) e usar o GPT-4o-mini
para um pequeno ajuste de contexto (lesao, suspensao, fase) + a analise em texto.

Custa tokens da sua OpenAI (pouco - so nos jogos futuros). Para ligar:
1. **Settings -> Secrets and variables -> Actions -> New repository secret.**
   Nome: `OPENAI_API_KEY` | Valor: sua chave do GPT-4o-mini. Salve.
2. No `.github/workflows/train.yml`, na secao `env:` do passo "Rodar pipeline",
   garanta a linha: `OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}`
3. Em `training/config.json`, deixe `"useNews": true`.
4. Re-suba a pasta `training` e rode o workflow.

> Observacoes honestas:
> - E uma camada **experimental**: nao da pra validar no backtest (nao ha noticia
>   historica alinhada). Por isso entra com peso pequeno (max +-15%).
> - So produz efeito quando o `predictions.json` tem jogos (Pro/pipeline). No plano
>   gratis, com predictions vazio, ela fica pronta mas dormente.

## Se algo falhar
- Bolinha **vermelha** na aba Actions: clique nela e me mande o texto do erro (a etapa
  "Rodar pipeline" costuma dizer o motivo, ex: temporada indisponivel no plano gratis).
- **Top 10 vazio no app:** confirme que as ligas do `config.json` sao as mesmas que
  voce escolheu no onboarding.
