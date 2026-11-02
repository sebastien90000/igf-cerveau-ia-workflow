"""Tests de la logique pure (aucune dépendance externe requise)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from igf_lib import analysis  # noqa: E402

TEXT = (
    "L'évaluation révèle que la subvention versée en 2023 n'apparait pas dans les "
    "comptes de l'opérateur avant 2024 — un décalage que l'analyse confirme sur "
    "trois exercices consécutifs, avec une portée limitée aux seuls crédits délégués."
)


def test_normalize_handles_typographic_marks():
    raw = "L'élément — signalé en « 2023 » —  n'apparait   pas\n\ndans les comptes"
    n = analysis.normalize_for_anchor(raw)
    assert "—" not in n
    assert "«" not in n
    assert "  " not in n
    assert "\n" not in n
    assert "l'élément" in n


def test_anchor_found_exact():
    anchor = "la subvention versée en 2023 n'apparait pas dans les comptes de l'opérateur"
    check = analysis.anchor_confidence("CONFIRME", "A", anchor, TEXT)
    assert check == {"verifie": True, "confiance": "A"}


def test_anchor_found_with_typographic_apostrophe():
    # ancre avec apostrophe typographique ’, texte avec ' : doit passer
    anchor = "la subvention versée en 2023 n’apparait pas dans les comptes de l’opérateur"
    check = analysis.anchor_confidence("CONFIRME", "B", anchor, TEXT)
    assert check["verifie"] is True


def test_anchor_not_found_downgrades_to_D():
    anchor = "cette phrase n'existe absolument pas dans le texte source du rapport"
    check = analysis.anchor_confidence("CONFIRME", "A", anchor, TEXT)
    assert check == {"verifie": False, "confiance": "D"}


def test_anchor_with_punctuation_matches_literal():
    anchor = "un décalage que l'analyse confirme sur trois exercices consécutifs, avec une portée"
    check = analysis.anchor_confidence("CONFIRME", "A", anchor, TEXT)
    assert check["verifie"] is True


def test_anchor_too_short_is_rejected():
    anchor = "la subvention versée"
    check = analysis.anchor_confidence("CONFIRME", "A", anchor, TEXT)
    assert check["verifie"] is False


def test_parse_observations_json_and_filtering():
    raw = (
        "```json\n"
        '{"observations": ['
        '{"pattern_code": "P01", "verdict": "CONFIRME", "ancre": "' + TEXT[20:120] + '", "confiance": "A", "commentaire": "ok"},'
        '{"pattern_code": "P02", "verdict": "ABSENT"},'
        '{"pattern_code": "S18", "verdict": "NUANCE", "ancre": "x", "confiance": "C", "commentaire": "variante"}'
        "]}\n```"
    )
    obs = analysis.parse_observations(raw)
    codes = [o["pattern_code"] for o in obs]
    assert codes == ["P01", "S18"]
    assert obs[1]["confiance"] == "C"


def test_parse_observations_tolerates_prose_around_json():
    raw = 'Voici mon analyse : {"observations": []} — fin.'
    assert analysis.parse_observations(raw) == []


def test_merge_observations_dedupes():
    o1 = {"pattern_code": "P01", "verdict": "CONFIRME", "ancre": "les comptes de l'opérateur avant"}
    o2 = {"pattern_code": "P01", "verdict": "CONFIRME", "ancre": "les comptes de l'opérateur avant"}
    o3 = {"pattern_code": "S40", "verdict": "NUANCE", "ancre": "crédits délégués"}
    merged = analysis.merge_observations([o1, o2, o3])
    assert len(merged) == 2


def test_split_windows_single_short_text():
    assert analysis.split_windows("court", chunk=60_000, overlap=5_000) == ["court"]


def test_split_windows_overlap():
    text = "x" * 150_000
    windows = analysis.split_windows(text, chunk=60_000, overlap=5_000)
    assert len(windows) == 3
    assert all(len(w) <= 60_000 for w in windows)


def test_patterns_catalog_format():
    pats = [
        {
            "code": "P01",
            "formule": "Cause racine ≠ cause apparente",
            "logique": "remonter au mécanisme",
            "caractere": "explicite",
        }
    ]
    cat = analysis.build_patterns_catalog(pats)
    assert "P01 | Cause racine ≠ cause apparente" in cat
