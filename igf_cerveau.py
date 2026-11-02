"""Workflow « Cerveau IA de l'IGF » — pipeline quotidien autonome.

Boucle : scan OneDrive → sélection des rapports non traités → analyse Mistral
(confrontation au codex) → vérification des ancres → écriture dans Notion.

Les activités portent les effets de bord ; l'orchestration reste déterministe.
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

import mistralai.workflows as workflows

from igf_lib import analysis, config, graph, notion


class DailyRunInput(BaseModel):
    """Entrée du run quotidien."""

    batch_size: int = Field(default=3, ge=1, le=10)
    dry_run: bool = False  # si True : analyse sans écrire dans Notion


class DailyRunResult(BaseModel):
    files_seen: int = 0
    reports_processed: list[str] = []
    occurrences_written: int = 0
    anchors_verified: int = 0
    errors: list[str] = []


# --------------------------------------------------------------------------
# Activités (effets de bord : HTTP, LLM, écritures)
# --------------------------------------------------------------------------


@workflows.activity()
async def fetch_graph_token() -> str:
    return await graph.get_access_token()


@workflows.activity()
async def list_reports_onedrive(token: str) -> list[dict]:
    return await graph.list_markdown_files(token)


@workflows.activity()
async def fetch_patterns() -> list[dict]:
    return await notion.fetch_patterns()


@workflows.activity()
async def fetch_processed_report_titles() -> list[str]:
    """Titres des rapports déjà 'Lu' ou 'En cours' dans la base Rapports."""
    pages = await notion.fetch_report_pages()
    return [p["title"] for p in pages if p.get("statut") in ("Lu", "En cours")]


@workflows.activity()
async def download_report(token: str, file_id: str) -> str:
    return await graph.download_file(token, file_id)


@workflows.activity()
async def analyze_report(file_name: str, text: str, patterns_catalog: str) -> list[dict]:
    """Analyse toutes les fenêtres du rapport et fusionne les observations."""
    windows = analysis.split_windows(text)
    raws = await asyncio.gather(
        *[
            analysis.analyze_window(config.ANALYSIS_MODEL, w, patterns_catalog)
            for w in windows
        ]
    )
    observations: list[dict] = []
    for raw in raws:
        observations.extend(analysis.parse_observations(raw))
    return analysis.merge_observations(observations)


@workflows.activity()
async def verify_and_write_occurrences(
    file_name: str, text: str, observations: list[dict], dry_run: bool
) -> dict:
    """Temps 4 (vérification d'ancre) + temps 5 (écriture) de la boucle §7."""
    verified = 0
    written = 0
    errors: list[str] = []
    for o in observations:
        check = analysis.anchor_confidence(o.get("verdict", ""), o.get("confiance", "B"), o.get("ancre", ""), text)
        if not check["verifie"]:
            # Ancre introuvable : on garde la trace mais on ne capitalise pas en A-C
            errors.append(f"{file_name} {o.get('pattern_code')}: ancre non retrouvée (confiance D)")
            o["verifie"] = False
            o["confiance"] = "D"
            continue
        verified += 1
        o["verifie"] = True
        o["confiance"] = check["confiance"]
        if not dry_run:
            try:
                await notion.create_occurrence(
                    report_title=file_name.removesuffix(".md"),
                    pattern_page_id=o.get("pattern_code", ""),
                    statut=o["verdict"],
                    ancre=o.get("ancre", ""),
                    confiance=o["confiance"],
                    commentaire=o.get("commentaire", ""),
                    verifie=True,
                )
                written += 1
            except Exception as exc:  # noqa: BLE001 — on ne casse pas le lot pour une ligne
                errors.append(f"{file_name} {o.get('pattern_code')}: écriture Notion échouée ({exc})")
    return {"verified": verified, "written": written, "errors": errors}


@workflows.activity()
async def mark_report_read(file_name: str, dry_run: bool) -> None:
    if dry_run:
        return
    pages = await notion.fetch_report_pages()
    title = file_name.removesuffix(".md")
    for p in pages:
        if p.get("title") and title.lower() in p["title"].lower():
            await notion.set_report_status(p["page_id"], "Lu")
            return


# --------------------------------------------------------------------------
# Orchestration (déterministe)
# --------------------------------------------------------------------------


@workflows.workflow.define(
    name="igf-cerveau-daily",
    workflow_display_name="Cerveau IA IGF — run quotidien",
    workflow_description=(
        "Scan OneDrive, analyse les rapports non traités (confrontation au codex), "
        "vérifie les ancres et capitalise les occurrences dans Notion."
    ),
)
class IgfCerveauDaily:
    @workflows.workflow.entrypoint
    async def run(self, input: DailyRunInput) -> DailyRunResult:
        result = DailyRunResult()

        # 1. Scan OneDrive + état Notion (en parallèle)
        token, processed, patterns = await asyncio.gather(
            fetch_graph_token(),
            fetch_processed_report_titles(),
            fetch_patterns(),
        )
        all_files = await list_reports_onedrive(token)
        result.files_seen = len(all_files)

        processed_lower = {t.lower() for t in processed if t}
        pending = [
            f
            for f in all_files
            if f["file_name"].removesuffix(".md").lower() not in processed_lower
        ]
        batch = pending[: input.batch_size]
        if not batch:
            return result

        catalog = analysis.build_patterns_catalog(patterns)
        patterns_by_code = {p["code"]: p for p in patterns}

        # 2. Lot de rapports, séquentiellement (budget maîtrisé)
        for f in batch:
            file_name = f["file_name"]
            try:
                text = await download_report(token, f["file_id"])
                observations = await analyze_report(file_name, text, catalog)
                for o in observations:
                    p = patterns_by_code.get(o.get("pattern_code"))
                    if p:
                        o["pattern_page_id"] = p["page_id"]
                write_result = await verify_and_write_occurrences(
                    file_name, text, observations, input.dry_run
                )
                result.occurrences_written += write_result["written"]
                result.anchors_verified += write_result["verified"]
                result.errors.extend(write_result["errors"])
                if write_result["verified"] > 0:
                    await mark_report_read(file_name, input.dry_run)
                    result.reports_processed.append(file_name)
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"{file_name}: {exc}")

        return result
