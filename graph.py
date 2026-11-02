"""Client Microsoft Graph pour OneDrive — lecture seule, sans utilisateur connecté.

Utilise le flux "client credentials" de l'application Entra ID
« Cerveau IGF Workflow » (permissions Files.Read.All / Sites.Read.All).
"""

from __future__ import annotations

import httpx

from . import config


async def get_access_token() -> str:
    """Obtient un jeton d'application via le flux client credentials."""
    data = {
        "client_id": config.MS_CLIENT_ID,
        "client_secret": config.MS_CLIENT_SECRET,
        "scope": config.MS_SCOPE,
        "grant_type": "client_credentials",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(config.MS_TOKEN_URL, data=data)
        resp.raise_for_status()
        return resp.json()["access_token"]


async def list_markdown_files(token: str) -> list[dict]:
    """Liste les fichiers .md du dossier racine (pagination incluse)."""
    files: list[dict] = []
    url = (
        f"https://graph.microsoft.com/v1.0/drives/{config.DRIVE_ID}"
        f"/root:{config.ONEDRIVE_ROOT_PATH}:/children"
    )
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60) as client:
        while url:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            for item in payload.get("value", []):
                if "file" in item and item["file"].get("mimeType") == "text/markdown":
                    files.append(
                        {
                            "file_name": item["name"],
                            "file_id": item["id"],
                            "size_bytes": item.get("size", 0),
                            "web_url": item.get("webUrl"),
                        }
                    )
            url = payload.get("@odata.nextLink")
    return files


async def download_file(token: str, file_id: str) -> str:
    """Télécharge le contenu texte d'un fichier."""
    url = f"https://graph.microsoft.com/v1.0/drives/{config.DRIVE_ID}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text
