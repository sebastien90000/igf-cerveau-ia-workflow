"""Configuration centrale — IDs non sensibles (les secrets restent dans l'environnement)."""

import os

# --- Microsoft Graph (app "Cerveau IGF Workflow") ---
MS_CLIENT_ID = os.environ.get("MS_CLIENT_ID", "")
MS_TENANT_ID = os.environ.get("MS_TENANT_ID", "")
MS_CLIENT_SECRET = os.environ.get("MS_CLIENT_SECRET", "")
MS_SCOPE = "https://graph.microsoft.com/.default"
MS_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token".format(
    tenant=MS_TENANT_ID
)

# --- OneDrive (config non sensible, publique) ---
DRIVE_ID = os.environ.get(
    "DRIVE_ID",
    "b!B24LSp9oFkGai-MjBs0wxXF7gRo5jI5BvXqKgV1yir0H5z-6CyQ9R6QEtn3htHpS",
)
ONEDRIVE_ROOT_PATH = os.environ.get(
    "ONEDRIVE_ROOT_PATH", "/Documents/IGF IGAS CAE/MARKDOWN copie"
)

# --- Notion ---
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_VERSION = "2022-06-28"
NOTION_API = "https://api.notion.com/v1"

# Bases Notion « Cerveau IGF » (IDs publics, non sensibles)
DB_PATTERNS = "2dfc6516-3a5e-4713-a542-36b057595a90"        # Patterns IGF
DB_OCCURRENCES = "cf8bee45-0306-478c-8e5c-d0f7f084832e"     # Occurrences IGF — Rapport × Pattern
DB_REPORTS = "ca21697d-332f-43e7-a516-d750c10cc03b"          # Rapports IGF — lecture
PAGE_CODEX = "3d36ecaa-b30b-815c-8080f03c4b667194"           # IGF Codex

# --- Analyse ---
ANALYSIS_MODEL = os.environ.get("ANALYSIS_MODEL", "mistral-large-latest")
CHUNK_CHARS = 60_000      # fenêtre glissante (~25k tokens), cf. doctrine §7
CHUNK_OVERLAP = 5_000     # recouvrement (~2k tokens)

# Noms des propriétés Notion (à ajuster si le schéma évolue)
PROP_RAPPORT = "Rapport"
PROP_PATTERN = "Pattern"
PROP_STATUT = "Statut"
PROP_ANCRE = "Ancre"
PROP_VERIFIE = "Vérifié source"
PROP_CONFIANCE = "Confiance"
PROP_COMMENTAIRE = "Commentaire"
PROP_STATUT_LECTURE = "Statut"  # base Rapports : Lu / En cours / À lire
