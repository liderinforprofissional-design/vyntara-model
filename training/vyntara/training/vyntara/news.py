"""Fonte de noticias (midia especializada brasileira) via Google News RSS.

Gratis e sem chave. O Google News ja AGREGA a midia esportiva brasileira
(ge.globo, UOL, ESPN, Lance, etc.) e ate as noticias oficiais dos clubes -
entao pegamos tudo por um so lugar, sem manter um scraper por site.

Fazemos duas buscas por time: uma geral e uma focada em contexto (desfalque,
lesao, suspensao, escalacao), e juntamos as manchetes sem repetir.
"""

from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET

import requests

_QUERIES = ("futebol", "desfalques lesao suspensao escalacao treinador")


def _search(query: str, limit: int) -> list[str]:
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(query)
        + "&hl=pt-BR&gl=BR&ceid=BR:pt"
    )
    try:
        resp = requests.get(
            url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (VyntaraBot)"}
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        out = []
        for item in root.iter("item"):
            title = item.findtext("title")
            if title:
                out.append(title.strip())
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def fetch_headlines(team_name: str, max_items: int = 8) -> list[str]:
    """Manchetes recentes do time (pt-BR), sem repetir. [] se tudo falhar."""
    seen: set[str] = set()
    out: list[str] = []
    for suffix in _QUERIES:
        for title in _search(f"{team_name} {suffix}", limit=max_items):
            if title not in seen:
                seen.add(title)
                out.append(title)
            if len(out) >= max_items:
                return out
    return out
