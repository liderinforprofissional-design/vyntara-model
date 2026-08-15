"""Camada de contexto com GPT-4o-mini (opcional) - a partir das manchetes.

IMPORTANTE:
 - O NUMERO base vem do ensemble (Poisson+Elo+ML+odds). O GPT so olha as
   MANCHETES e devolve um AJUSTE PEQUENO de contexto (lesao, suspensao, retorno
   de titular, fase/moral) - nunca a probabilidade inteira.
 - A chave da OpenAI vem da variavel de ambiente OPENAI_API_KEY. NUNCA no app.
 - Se a lib/chave nao estiver disponivel, retorna neutro e o pipeline segue.
"""

from __future__ import annotations

import json
import os

_LIMIT = 0.15  # ajuste maximo por time (para nao deixar a noticia dominar)


def _clamp(x: float) -> float:
    return max(-_LIMIT, min(_LIMIT, x))


def assess_context(
    home: str, away: str, home_news: list[str], away_news: list[str]
) -> tuple[str, float, float]:
    """Retorna (analise_texto, home_impact, away_impact).
    impact positivo = boa noticia para o time (favorece). Faixa: [-0.15, 0.15]."""
    if os.environ.get("OPENAI_API_KEY", "") == "":
        return ("", 0.0, 0.0)
    try:
        from openai import OpenAI
    except Exception:
        return ("", 0.0, 0.0)

    def block(news: list[str]) -> str:
        return "\n- ".join(news[:6]) if news else "(sem noticias relevantes)"

    prompt = (
        "Voce e um analista de futebol. Com base SOMENTE nas manchetes abaixo, avalie o "
        "impacto de CONTEXTO para cada time e devolva um ajuste pequeno.\n\n"
        "Priorize os sinais NESTA ordem de importancia:\n"
        "1) Lesao/suspensao de jogador TITULAR e importante (peso alto).\n"
        "2) Troca de treinador recente ou crise entre treinador e elenco.\n"
        "3) Retorno de titular/artilheiro; chegada ou saida de jogador relevante.\n"
        "4) Fase do time (sequencia de vitorias/derrotas) e jejum de gols do atacante.\n"
        "5) Desfalques por Data Fifa/convocacao; calendario apertado (jogos seguidos).\n"
        "6) Crise institucional: salarios atrasados, protesto de torcida, diretoria.\n"
        "7) Peso do jogo: decisao, briga por titulo, risco de rebaixamento.\n\n"
        "Regras: seja CONSERVADOR. Rumor ou manchete irrelevante -> 0. "
        "Nao invente nada que nao esteja nas manchetes.\n\n"
        f"Mandante: {home}\nManchetes:\n- {block(home_news)}\n\n"
        f"Visitante: {away}\nManchetes:\n- {block(away_news)}\n\n"
        "Responda em JSON valido, sem nada fora do JSON:\n"
        '{"analise": "2 frases curtas em portugues", '
        '"home_impact": <numero entre -0.15 e 0.15>, '
        '"away_impact": <numero entre -0.15 e 0.15>}'
    )

    try:
        client = OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        text = str(data.get("analise", ""))[:400]
        return (text, _clamp(float(data.get("home_impact", 0.0))),
                _clamp(float(data.get("away_impact", 0.0))))
    except Exception:
        return ("", 0.0, 0.0)
