"""Client Notion (API officielle, intégration « Cerveau IGF »).

Opérations utilisées par le pipeline :
- lister les patterns du codex (base Patterns IGF)
- lister les rapports déjà traités (base Rapports IGF)
- créer une occurrence (base Occurrences IGF)
- mettre à jour le statut de lecture d'un rapport
"""

from __future__ import annotations

import httpx

from . import config


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.NOTION_TOKEN}",
        "Notion-Version": config.NOTION_VERSION,
        "Content-Type": "application/json",
    }


async def query_database(database_id: str, filter_: dict | None = None, page_size: int = 100) -> list[dict]:
    """Interroge une base et retourne la liste des pages (pagination incluse)."""
    pages: list[dict] = []
    body: dict = {"page_size": page_size}
    if filter_:
        body["filter"] = filter_
    url = f"{config.NOTION_API}/databases/{database_id}/query"
    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            resp = await client.post(url, headers=_headers(), json=body)
            resp.raise_for_status()
            payload = resp.json()
            pages.extend(payload.get("results", []))
            if not payload.get("has_more"):
                break
            body["start_cursor"] = payload.get("next_cursor")
    return pages


async def fetch_patterns() -> list[dict]:
    """Charge le codex : code, formule et logique de chaque pattern."""
    pages = await query_database(config.DB_PATTERNS)
    patterns: list[dict] = []
    for p in pages:
        props = p.get("properties", {})
        code = _first_title(props.get("Code"))
        if not code:
            continue
        patterns.append(
            {
                "page_id": p["id"],
                "code": code,
                "formule": _first_rich_text(props.get("Formule")),
                "logique": _first_rich_text(props.get("Logique")),
                "caractere": _first_select(props.get("Caractère")),
            }
        )
    return patterns


async def fetch_report_pages() -> list[dict]:
    """Liste les fiches de la base Rapports (statut Lu / En cours / À lire)."""
    pages = await query_database(config.DB_REPORTS)
    reports = []
    for p in pages:
        props = p.get("properties", {})
        title = _first_any_title(props)
        reports.append(
            {
                "page_id": p["id"],
                "title": title,
                "statut": _first_select(props.get(config.PROP_STATUT_LECTURE)),
            }
        )
    return reports


async def create_occurrence(
    report_title: str,
    pattern_page_id: str,
    statut: str,
    ancre: str,
    confiance: str,
    commentaire: str,
    verifie: bool,
) -> dict:
    """Crée une ligne dans la base Occurrences (Rapport × Pattern)."""
    body = {
        "parent": {"database_id": config.DB_OCCURRENCES},
        "properties": {
            "Name": {"title": [{"text": {"content": f"{report_title} — {statut}"}}]},
            config.PROP_RAPPORT: {"rich_text": [{"text": {"content": report_title}}]},
            config.PROP_PATTERN: {"rich_text": [{"text": {"content": pattern_page_id}}]},
            config.PROP_STATUT: {"select": {"name": statut}},
            config.PROP_ANCRE: {"rich_text": [{"text": {"content": ancre[:2000]}}]},
            config.PROP_VERIFIE: {"checkbox": verifie},
            config.PROP_CONFIANCE: {"select": {"name": confiance}},
            config.PROP_COMMENTAIRE: {"rich_text": [{"text": {"content": commentaire[:2000]}}]},
        },
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{config.NOTION_API}/pages", headers=_headers(), json=body)
        resp.raise_for_status()
        return resp.json()


async def set_report_status(report_page_id: str, statut: str) -> dict:
    """Met à jour le statut de lecture d'un rapport (ex. À lire → En cours → Lu)."""
    body = {"properties": {config.PROP_STATUT_LECTURE: {"select": {"name": statut}}}}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.patch(
            f"{config.NOTION_API}/pages/{report_page_id}", headers=_headers(), json=body
        )
        resp.raise_for_status()
        return resp.json()


# ---- helpers d'extraction ----

def _first_title(prop: dict | None) -> str | None:
    if not prop or prop.get("type") != "title":
        return None
    for t in prop.get("title", []):
        if t.get("plain_text"):
            return t["plain_text"]
    return None


def _first_any_title(props: dict) -> str | None:
    for p in props.values():
        v = _first_title(p)
        if v:
            return v
    return None


def _first_rich_text(prop: dict | None) -> str:
    if not prop or prop.get("type") != "rich_text":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _first_select(prop: dict | None) -> str | None:
    if not prop:
        return None
    sel = prop.get("select")
    return sel.get("name") if sel else None
