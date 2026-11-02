"""Point d'entrée du worker : découvre les workflows et démarre le worker."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mistralai.workflows as workflows  # noqa: E402

from workflows.igf_cerveau import IgfCerveauDaily  # noqa: E402


async def main() -> None:
    await workflows.run_worker([IgfCerveauDaily])


if __name__ == "__main__":
    asyncio.run(main())
