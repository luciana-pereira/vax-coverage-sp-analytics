"""Serviço de inferência: aplica o modelo treinado a linhas do dataset de ML."""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

from ml.features.build_features import TARGET_COLUMN
from ml.inference.predict import load_feature_list, load_model, predict_with_probabilities

from ..repositories.coverage_repository import PredictionRepository
from ..schemas.prediction import PredictionItem, PredictionResponse


@lru_cache(maxsize=2)
def _cached_model(path: str, mtime_ns: int):
    return load_model(Path(path))


class PredictionService:
    def __init__(self, repo: PredictionRepository, model_path: Path, metrics_path: Path) -> None:
        self.repo = repo
        self.model_path = model_path
        self.metrics_path = metrics_path

    def predict(
        self,
        year: int | None,
        municipality_code: str | None,
        immunizer: str | None,
        predicted_class: str | None,
        limit: int,
        offset: int,
    ) -> PredictionResponse:
        if not (self.model_path.is_file() and self.metrics_path.is_file()):
            return PredictionResponse(
                status="model_unavailable",
                message="Modelo não treinado. Execute 'python -m ml.cli train'.",
            )
        if not self.repo.exists:
            return PredictionResponse(
                status="data_unavailable",
                message="Dataset de ML ausente. Execute 'python -m ml.cli features'.",
            )

        features = load_feature_list(self.metrics_path)
        frame = self.repo.latest_unlabeled(
            TARGET_COLUMN, features, year, municipality_code, immunizer
        )
        model_name = self._model_name()
        if frame.empty:
            return PredictionResponse(
                status="ok",
                message="Sem linhas sem rótulo para os filtros (nenhum período futuro a prever).",
                model_name=model_name,
            )

        model = _cached_model(str(self.model_path), self.model_path.stat().st_mtime_ns)
        result = predict_with_probabilities(model, frame[features])
        proba_cols = [c for c in result.columns if c.startswith("proba_")]

        items: list[PredictionItem] = []
        for position, (_, row) in enumerate(frame.iterrows()):
            label = str(result["prediction"].iloc[position])
            if predicted_class and label != predicted_class:
                continue
            name = row.get("municipality_name")
            items.append(
                PredictionItem(
                    municipality_code=str(row.get("municipality_code")),
                    municipality_name=None if name is None or name != name else str(name),
                    immunizer=_optional_text(row.get("immunizer")),
                    source_year=int(row["year"]),
                    predicted_class=label,
                    probabilities={
                        c.removeprefix("proba_"): float(result[c].iloc[position])
                        for c in proba_cols
                    }
                    or None,
                )
            )

        items.sort(key=lambda i: (i.municipality_code, i.immunizer or ""))
        source_year = int(frame["year"].max())
        return PredictionResponse(
            status="ok",
            model_name=model_name,
            source_year=source_year,
            target_year=source_year + 1,
            total=len(items),
            class_distribution=dict(Counter(i.predicted_class for i in items)),
            items=items[offset : offset + limit],
        )

    def _model_name(self) -> str | None:
        return json.loads(self.metrics_path.read_text(encoding="utf-8")).get("best_model")


def _optional_text(value) -> str | None:
    if value is None or value != value:
        return None
    return str(value)
