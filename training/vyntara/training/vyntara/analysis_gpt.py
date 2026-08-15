"""Analise em texto com GPT-4o-mini (opcional).

IMPORTANTE:
 - O NUMERO nunca vem do GPT (LLM e ruim para probabilidade). O GPT so escreve
   a explicacao curta do palpite ja calculado pelo ensemble.
 - A chave da OpenAI vem da variavel de ambiente OPENAI_API_KEY. NUNCA coloque
   a chave no app Android.
 - Se a lib/opcao estiver desligada, retorna string vazia (o pipeline segue).
"""

from __future__ import annotations

import os


def analyze(home: str, away: str, probs: dict, expected: dict, best_bet: dict) -> str:
    if os.environ.get("OPENAI_API_KEY", "") == "":
        return ""
    try:
        from openai import OpenAI
    except Exception:
        return ""

    client = OpenAI()
    prompt = (
        "Voce e um analista de futebol. Em 2 frases curtas e objetivas, em portugues, "
        "explique o palpite abaixo SEM inventar dados e SEM mudar os numeros.\n"
        f"Jogo: {home} x {away}\n"
        f"Probabilidades: casa {probs['home']:.0%}, empate {probs['draw']:.0%}, fora {probs['away']:.0%}\n"
        f"Gols esperados: {expected['home']:.2f} x {expected['away']:.2f}\n"
        f"Palpite destacado: {best_bet['label']} ({best_bet['probability']:.0%})"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"(analise indisponivel: {e})"
