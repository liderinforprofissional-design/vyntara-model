# Inventário de sinais — o funil de informação do Vyntara

## A regra de ouro
Nem toda informação vale o mesmo. Ordenamos por dois eixos: **IMPACTO** no resultado
× **CONFIABILIDADE** do dado. O funil pega muita coisa da mídia e destila só o que
move o ponteiro. Cada sinal novo só "entra pra valer" quando melhora o backtest
(quando for mensurável).

## Onde cada sinal mora
- **NÚMERO (modelo, backtestável):** já temos força de ataque/defesa (Poisson), Elo
  com margem de vitória, forma recente, gols marcados/sofridos, descanso, H2H e odds.
- **MÍDIA/CONTEXTO (GPT lê manchete → ajuste pequeno):** o que não vira número fácil —
  lesão de última hora, crise, moral, troca de treinador. Peso limitado (±15%).
- **BASES ESTRUTURADAS (FBref/Transfermarkt):** estatística precisa por jogador/time,
  valor de elenco, tempo de treinador — pra virar features numéricas de verdade.

---

## Tiers de prioridade (o que capturar da mídia)

### Tier 1 — alto impacto, capturar sempre
- Lesão/suspensão de **titular importante** (goleiro, zagueiro central, maestro, artilheiro).
- **Troca de treinador** recente (últimas 2-3 semanas) — o efeito "novo treinador" é real e curto.
- Desfalque por **Data Fifa / convocação**.

### Tier 2 — alto impacto, com cuidado
- **Retorno** de peça-chave após lesão/suspensão.
- **Jejum do artilheiro** ou artilheiro embalado.
- **Sequência** (3+ vitórias/derrotas) — a mídia dá a "temperatura" que o Elo já pega em parte.
- **Calendário**: 3º jogo em 7 dias, viagem longa, jogo no meio de semana.

### Tier 3 — médio impacto (institucional / humano)
- **Tempo do treinador no clube** e se a filosofia "pegou" (ideia sua — ótima).
- **Crise**: salários atrasados, protesto de torcida, diretoria/eleição.
- Clima interno (conflito de jogador, "panela").
- **Peso do jogo**: final, briga por título, luta contra o rebaixamento (motivação).

### Tier 4 — contexto fino (peso pequeno)
- Clima/altitude, mando invertido (estádio neutro), gramado.
- Histórico do treinador contra aquele adversário/estilo.

---

## Suas ideias, mapeadas
- "Tempo do treinador + filosofia funcionando" → Tier 3 (mídia) hoje; vira **número** (tempo de casa) via Transfermarkt na fase de bases.
- "Jejum dos atacantes" → Tier 2.
- "Com o jogador X o time rende mais/menos" → é a **SINERGIA**, a mais difícil; precisa de base estruturada (FBref) + muitos dados. Fase avançada.
- "Troca de treinador / entra e sai de jogadores + relevância + idade + rendimento 6m" → Tier 1/2 na mídia **agora**; vira número preciso via FBref/Transfermarkt depois.
- "Aspectos políticos / salários atrasados" → Tier 3.

---

## Fontes de dados (sem API paga em tempo real)

### FBref — melhor caminho grátis (RECOMENDADO como próximo passo)
- Estatística por jogo/jogador rica, **incluindo xG**. Estrutura estável, tolera
  scraping com calma (respeitando o rate limit). Há bibliotecas que ajudam (ex: `soccerdata`).
- É o **maior salto de qualidade sem pagar** API: dá pra treinar o ML com chutes,
  posse, xG — e isso é backtestável.

### Transfermarkt — ótimo para elenco / treinador / transferências
- Valor de mercado, elenco, transferências, **tempo de treinador**, lesões/suspensões.
- Scraping é possível, mas o **Termo de Uso é mais restritivo**; usar com moderação.

### Sofascore — deixar por último
- Ratings/estatística por jogo muito bons, MAS tem **proteção anti-bot forte** (Cloudflare):
  scraping é difícil, frágil e o ToS é restritivo. Baixa prioridade.

> Avisos honestos sobre scraping: os scrapers **quebram** quando o site muda (dá
> manutenção), e há **limites de ToS/legais** — usar com parcimônia, para uso próprio,
> respeitando robots.txt e sem sobrecarregar os servidores.

---

## Roadmap sugerido
1. **(feito, grátis)** Mídia via GPT no **Top-N** (economia de tokens) — pronto.
2. **(próximo, grátis)** **FBref no pipeline**: chutes/posse/xG → features numéricas → backtest. Maior salto sem pagar API.
3. **(depois)** **Transfermarkt**: elenco, valor, tempo de treinador, lesões → mais features.
4. **(avançado)** modelo por **jogador** + **sinergia** (precisa das bases FBref/Transfermarkt maduras).
