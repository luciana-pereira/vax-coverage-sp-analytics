"""Serviço de modelos: expõe o relatório de avaliação do treino."""

from __future__ import annotations

from pathlib import Path

from ..repositories.artifact_repository import ArtifactRepository
from ..schemas.model import (
    BaselineInfo,
    FeatureImportanceItem,
    ModelEntry,
    ModelMetrics,
    ModelResponse,
    SelectionInfo,
    SplitInfo,
)


class ModelService:
    def __init__(self, artifacts: ArtifactRepository, metrics_path: Path) -> None:
        self.artifacts = artifacts
        self.metrics_path = metrics_path

    @staticmethod
    def _validation(entry: dict) -> ModelMetrics | None:
        return ModelMetrics(**entry["validation"]) if entry.get("validation") else None

    def report(self) -> ModelResponse:
        data = self.artifacts.read_json(self.metrics_path)
        if data is None:
            return ModelResponse(
                status="not_trained",
                message="Relatório ausente. Execute 'python -m ml.cli train'.",
            )
            
        best = data.get("best_model", "random_forest")
        baseline = data.get("baseline")

        default_selection = {
            "criterion": "f1_macro",
            "split": "test",
            "note": "Critério de seleção padrão.",
        }
        selection_data = data.get("selection", default_selection)

        default_split = {
            "scheme": "temporal",
            "train_years": [2024],
            "validation_year": None,
            "test_year": 2025,
            "n_train": 0,
            "n_validation": 0,
            "n_test": 0,
        }
        split_data = data.get("split", default_split)

        return ModelResponse(
            status="ok",
            generated_at=data.get("generated_at"),
            target=data.get("target", "deficit_class_next"),
            features=data.get("features", []),
            classes=data.get("classes", ["baixo", "moderado", "alto", "critico"]),
            split=SplitInfo(**split_data),
            selection=SelectionInfo(**selection_data),
            best_model=best,
            models=[
                ModelEntry(
                    name=name,
                    is_best=name == best,
                    validation=self._validation(entry),
                    test=ModelMetrics(**entry["test"]),
                )
                for name, entry in data.get("models", {}).items()
            ],
            baseline=BaselineInfo(
                description=baseline["description"], test=ModelMetrics(**baseline["test"])
            )
            if baseline
            else None,
            feature_importance=[
                FeatureImportanceItem(**item) for item in data.get("feature_importance", [])
            ],
        )