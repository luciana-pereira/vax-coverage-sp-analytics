from __future__ import annotations

from .discovery import discover_pni_csvs
from .models import IngestionRequest
from .pni import build_pni_source
from .processor import process_pni_files


class IngestionOrchestrator:
    """Orquestra a aquisição dos dados do PNI."""

    def execute(self, request: IngestionRequest) -> str | list[str]:
        if request.mode not in {"auto", "api", "download"}:
            raise ValueError(f"Modo de ingestão inválido: {request.mode}")

        if request.uf != "SP":
            raise ValueError(f"UF não suportada pelo projeto: {request.uf}")

        valid_age_groups = {"0_4", "60_plus"}
        invalid_age_groups = set(request.age_groups) - valid_age_groups

        if invalid_age_groups:
            raise ValueError(f"Faixas etárias não suportadas: {sorted(invalid_age_groups)}")

        valid_vaccines = {"SCR", "INFLUENZA"}
        invalid_vaccines = set(request.vaccines) - valid_vaccines

        if invalid_vaccines:
            raise ValueError(f"Vacinas não suportadas: {sorted(invalid_vaccines)}")

        if request.mode == "download":
            files = discover_pni_csvs(request.year_dir)

            if not files:
                raise FileNotFoundError(f"Nenhum CSV PNI encontrado em {request.year_dir}")

            return process_pni_files(
                files,
                uf=request.uf,
            )

        source = build_pni_source(request.year)

        return source.url
