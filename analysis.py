"""Analyse des rapports : lecture aveugle, confrontation au codex, vérification d'ancres.

Doctrine §7 (boucle 5 temps) :
1. lecture aveugle (le rapport, sans le codex en contexte de réponse)
2. confrontation : CONFIRME / NUANCE / CONTREDIT / NOUVEAU / ABSENT
3. contradiction
4. vérification source : ancre littérale 10-25 mots + confiance A-D
5. écriture : 1 occurrence par couple Rapport × Pattern
"""

from __future__ import annotations

import json
import re
import unicodedata

from . import config

VERDICTS = {"CONFIRME", "NUANCE", "CONTREDIT", "NOUVEAU", "ABSENT"}
CONFIANCES = {"A", "B", "C", "D"}

SYSTEM_PROMPT = """Tu es l'analyste du « Cerveau IA de l'IGF ».
Tu lis un rapport public (IGF/IGA/CAE/OFCE) converti en Markdown et tu le confrontes
à un codex de patterns de raisonnement (problèmes génériques formulés sans le domaine).

Pour CHAQUE pattern du codex, rends un verdict : CONFIRME, NUANCE, CONTREDIT, NOUVEAU ou ABSENT.
- CONFIRME : le rapport contient un mécanisme conforme au pattern.
- NUANCE : le mécanisme est présent mais avec une variante, une condition, une limite.
- CONTREDIT : le rapport défend explicitement une lecture opposée.
- NOUVEAU : le rapport contient un mécanisme qui ne correspond à aucun pattern listé.
- ABSENT : sans objet (ne génère PAS d'entrée).

Règles strictes :
- Chaque verdict (sauf ABSENT) DOIT être appuyé par une ancre littérale de 10 à 25 mots
  recopiée MOT POUR MOT depuis le texte du rapport.
- Ne reformule pas l'ancre : copie-la exactement.
- Un seul verdict par pattern ; pour NOUVEAU, propose un code provisoire S### et une formule.
- Réponds STRICTEMENT en JSON, sans texte autour.

Format de réponse :
{
  "observations": [
    {
      "pattern_code": "P01",
      "verdict": "CONFIRME|NUANCE|CONTREDIT|NOUVEAU",
      "ancre": "...",
      "confiance": "A|B|C|D",
      "commentaire": "mécanisme constaté, conditions, nuances (2-4 phrases)"
    }
  ]
}
"""


def build_patterns_catalog(patterns: list[dict]) -> str:
    lines = ["CODE | FORMULE | LOGIQUE | CARACTÈRE"]
    for p in patterns:
        lines.append(
            f"{p['code']} | {p['formule']} | {p['logique']} | {p.get('caractere') or '-'}"
        )
    return "\n".join(lines)


def split_windows(text: str, chunk: int = config.CHUNK_CHARS, overlap: int = config.CHUNK_OVERLAP) -> list[str]:
    """Fenêtre glissante (doctrine §7 : ~25k tokens, recouvrement ~2k)."""
    if len(text) <= chunk:
        return [text]
    windows = []
    step = chunk - overlap
    start = 0
    while start < len(text):
        windows.append(text[start : start + chunk])
        if start + chunk >= len(text):
            break
        start += step
    return windows


def normalize_for_anchor(text: str) -> str:
    """Normalisation tolérante pour la vérification des ancres.

    Gère : casse, espaces multiples, apostrophes typographiques, tirets d'incise,
    retours à la ligne, guillemets. Conserve les accents (les variantes
    orthographiques signalées, ex. « n'apparait », doivent passer après
    normalisation des seuls caractères de ponctuation/espace).
    """
    t = unicodedata.normalize("NFC", text)
    t = t.lower()
    t = t.replace("\u2019", "'").replace("\u2018", "'")   # apostrophes typographiques
    t = t.replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")
    t = t.replace("\u00ab", '"').replace("\u00bb", '"').replace("\u201c", '"').replace("\u201d", '"')
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def anchor_confidence(verdict: str, confidence: str, anchor: str, text: str) -> dict:
    """Vérifie mécaniquement que l'ancre existe dans le texte (temps 4 de la boucle).

    Retourne {"verifie": bool, "confiance": "A".."D"} :
    - ancre introuvable → confiance D et vérifié=False (jamais d'occurrence A non vérifiée)
    - ancre trouvée → confiance inchangée si A-C, sinon B
    """
    anchor_n = normalize_for_anchor(anchor)
    text_n = normalize_for_anchor(text)
    word_count = len(anchor_n.split())
    found = 10 <= word_count <= 30 and anchor_n in text_n
    if not found:
        return {"verifie": False, "confiance": "D"}
    return {"verifie": True, "confiance": confidence if confidence in CONFIANCES else "B"}


def merge_observations(observations: list[dict]) -> list[dict]:
    """Fusionne les observations multi-fenêtres : déduplique par (pattern, verdict, ancre)."""
    seen = set()
    merged = []
    for o in observations:
        key = (o.get("pattern_code"), o.get("verdict"), normalize_for_anchor(o.get("ancre", "")))
        if key in seen:
            continue
        seen.add(key)
        merged.append(o)
    return merged


def parse_observations(raw: str) -> list[dict]:
    """Extrait le JSON des observations depuis la réponse du modèle (tolérant aux balises)."""
    raw = raw.strip()
    raw = re.sub(r"^```(json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []
    out = []
    for o in data.get("observations", []):
        verdict = str(o.get("verdict", "")).upper().strip()
        if verdict not in VERDICTS or verdict == "ABSENT":
            continue
        out.append(
            {
                "pattern_code": str(o.get("pattern_code", "")).strip(),
                "verdict": verdict,
                "ancre": str(o.get("ancre", "")).strip(),
                "confiance": str(o.get("confiance", "B")).upper().strip() or "B",
                "commentaire": str(o.get("commentaire", "")).strip(),
                "formula": str(o.get("formule", "")).strip() if verdict == "NOUVEAU" else "",
            }
        )
    return out


async def analyze_window(model: str, text: str, patterns_catalog: str) -> str:
    """Appelle le modèle Mistral sur une fenêtre du rapport (appel brut, mockable)."""
    from mistralai import Mistral

    client = Mistral()
    user = (
        "CODEX DE RÉFÉRENCE (patterns) :\n"
        f"{patterns_catalog}\n\n"
        "TEXTE DU RAPPORT (fenêtre) :\n"
        f"{text}"
    )
    resp = await client.chat.async_complete(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=4000,
    )
    return resp.choices[0].message.content or ""
