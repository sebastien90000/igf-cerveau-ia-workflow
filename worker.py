"""Point d'entrée du worker : enregistre le workflow et démarre."""

from __future__ import annotations

import asyncio

import mistralai.workflows as workflows

from igf_cerveau import IgfCerveauDaily


async def main() -> None:
    await workflows.run_worker([IgfCerveauDaily])


if __name__ == "__main__":
    asyncio.run(main())
