"""Serviço de qualidade de dados e lacunas conhecidas do projeto."""

from __future__ import annotations

from ..core.config import Settings
from ..repositories.artifact_repository import ArtifactRepository
from ..repositories.coverage_repository import REQUIRED_COLUMNS, CoverageRepository
from ..schemas.data_quality import (
    ArtifactStatus,
    ColumnQuality,
    DataQualityResponse,
    DatasetQuality,
)

RECOMMENDED_COLUMNS = ("municipality_name",)


class DataQualityService:
    def __init__(
        self, settings: Settings, repo: CoverageRepository, artifacts: ArtifactRepository
    ) -> None:
        self.settings = settings
        self.repo = repo
        self.artifacts = artifacts

    def _artifact_defs(self):
        s = self.settings
        return [
            ("raw", "Dados brutos extraídos da fonte (PNI)", s.raw_dir),
            ("processed", "Dados processados (Parquet)", s.processed_file),
            ("features", "Features de cobertura/déficit", s.features_path),
            ("ml_dataset", "Dataset supervisionado de ML", s.ml_dataset_path),
            ("model", "Modelo treinado", s.model_path),
            ("metrics", "Relatório de avaliação do modelo", s.metrics_path),
            ("column_mapping", "Mapeamento colunas fonte -> canônico", s.column_mapping_path),
            ("target_population", "População-alvo (externa)", s.population_path),
            ("coverage_targets", "Metas de cobertura por imunizante", s.coverage_targets_path),
            ("geojson", "GeoJSON municipal de São Paulo", s.geojson_path),
        ]

    def _artifacts(self) -> list[ArtifactStatus]:
        statuses = []
        for name, description, path in self._artifact_defs():
            exists = path.exists() and (not path.is_dir() or any(path.glob("*.jsonl")))
            statuses.append(
                ArtifactStatus(
                    name=name,
                    description=description,
                    path=self.artifacts.relative(path),
                    exists=exists,
                    size_bytes=self.artifacts.size(path) if exists else None,
                )
            )
        return statuses

    def report(self) -> DataQualityResponse:
        artifacts = self._artifacts()
        gaps = self._gaps({a.name: a.exists for a in artifacts})

        dataset = None
        if self.repo.exists:
            stats = self.repo.quality()
            present = {c["name"] for c in stats["columns"]}
            required_missing = [c for c in REQUIRED_COLUMNS if c not in present]
            missing = [
                *required_missing,
                *(c for c in RECOMMENDED_COLUMNS if c not in present),
            ]
            for column in required_missing:
                gaps.append(f"Coluna obrigatória ausente no dataset: '{column}'.")
            for column in (c for c in RECOMMENDED_COLUMNS if c in missing):
                gaps.append(f"Coluna opcional ausente no dataset: '{column}'.")
            rows = stats["rows"]
            dataset = DatasetQuality(
                rows=rows,
                municipalities=stats["municipalities"],
                year_min=stats["year_min"],
                year_max=stats["year_max"],
                duplicate_rows=stats["duplicate_rows"],
                missing_columns=missing,
                columns=[
                    ColumnQuality(
                        name=c["name"],
                        null_count=c["null_count"],
                        null_ratio=round(c["null_count"] / rows, 4) if rows else 0.0,
                    )
                    for c in stats["columns"]
                ],
            )
        return DataQualityResponse(
            status="ok" if dataset and not required_missing else "data_unavailable",
            artifacts=artifacts,
            dataset=dataset,
            known_gaps=gaps,
        )

    def _gaps(self, exists: dict[str, bool]) -> list[str]:
        gaps = []
        if not exists["raw"]:
            gaps.append("Dados brutos ausentes: execute 'python -m pipeline.cli extract'.")
        if not exists["column_mapping"]:
            gaps.append(
                "Mapeamento de colunas da fonte não definido (schema real da API ainda não "
                "confirmado)."
            )
        if not exists["target_population"]:
            gaps.append(
                "População-alvo externa (IBGE/estimativa por imunizante) não fornecida; sem ela "
                "a cobertura não pode ser calculada."
            )
        if not exists["coverage_targets"]:
            gaps.append("Metas por imunizante não definidas: usando a meta padrão configurada.")
        if not exists["features"]:
            gaps.append("Features ausentes: execute 'python -m ml.cli features'.")
        if not exists["model"] or not exists["metrics"]:
            gaps.append("Modelo não treinado: execute 'python -m ml.cli train'.")
        if not exists["geojson"]:
            gaps.append("GeoJSON municipal ausente: o mapa não pode ser renderizado.")
        elif not self.settings.geojson_code_property:
            gaps.append("GEOJSON_CODE_PROPERTY não configurada: junção mapa x dados indisponível.")
        return gaps
