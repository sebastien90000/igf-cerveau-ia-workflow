# Cerveau IA de l'IGF — Workflow Mistral

Pipeline autonome d'analyse des rapports publics IGF / IGA / CAE / OFCE (~1058 fichiers
Markdown sur OneDrive) : lecture, confrontation au codex de patterns, vérification
des ancres, capitalisation dans les bases Notion « Cerveau IGF ».

## Architecture

```
Schedule quotidien (Mistral Workflows)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│ Workflow « igf-cerveau-daily »                            │
│  1. Jeton app Microsoft Graph (client credentials)       │
│  2. Scan OneDrive → fichiers .md non traités             │
│  3. État de lecture depuis Notion (base Rapports)        │
│  4. Analyse Mistral : fenêtres 25k tokens / recoup. 2k   │
│     → verdicts CONFIRME / NUANCE / CONTREDIT / NOUVEAU  │
│  5. Vérification mécanique des ancres (10-25 mots)       │
│  6. Écriture : occurrences Notion + statut Lu            │
└─────────────────────────────────────────────────────────┘
```

## Secrets

Aucun secret n'est committé. Le worker lit son environnement :

| Variable | Rôle | Où la créer |
|---|---|---|
| `MISTRAL_API_KEY` | Connexion worker + appels modèles | locale : `.env` ; managé : auto |
| `MS_CLIENT_ID` | App Entra ID « Cerveau IGF Workflow » | [console.mistral.ai/secrets](https://console.mistral.ai/secrets) |
| `MS_TENANT_ID` | Tenant I-EFFICIENCE | idem |
| `MS_CLIENT_SECRET` | Secret client Azure | idem |
| `NOTION_TOKEN` | Intégration Notion « Cerveau IGF » | idem |

Copie `.env.example` en `.env` pour un usage local ; le déploiement managé lie les
**secrets de workspace** (Secrets Manager) aux variables d'environnement.

## Développement local

```bash
uv sync
make test
make start-worker
```

## Déclenchement

```bash
make execute workflow=igf-cerveau-daily input='{"batch_size": 3, "dry_run": true}'
```

`dry_run: true` analyse sans rien écrire dans Notion (idéal premier run).

## Doctrine (résumé)

Boucle 5 temps (protocole §7) : lecture aveugle → confrontation → contradiction →
vérification source (ancre littérale, confiance A-D) → écriture (1 occurrence par
couple Rapport × Pattern). Une occurrence sans ancre vérifiée est dégradée en
confiance D et non capitalisée.

## Ajustements éventuels

- `src/igf_lib/config.py` : IDs des bases Notion, noms des propriétés, modèle, tailles de fenêtres.
- `src/igf_lib/analysis.py` : prompt de confrontation, normalisation des ancres.
