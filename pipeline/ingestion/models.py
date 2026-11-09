from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class IngestionRequest:
    year: int
    uf: str = "SP"
    age_groups: tuple[str, ...] = ("0_4", "60_plus")
    vaccines: tuple[str, ...] = ("SCR", "INFLUENZA")
    mode: str = "auto"
    incoming_dir: Path = field(default_factory=lambda: Path("data/incoming/pni"))

    @property
    def year_dir(self) -> Path:
        """Diretório de fallback para o ano solicitado."""
        return self.incoming_dir / str(self.year)
