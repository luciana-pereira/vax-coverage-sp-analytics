"""Configuração de ML: caminhos de dados/artefatos e metas de cobertura."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")


def _path(name: str, default: Path) -> Path:
    value = Path(os.getenv(name, str(default)))
    return value if value.is_absolute() else ROOT / value


@dataclass(frozen=True)
class MlSettings:
    processed_file: Path
    features_path: Path
    ml_dataset_path: Path
    model_path: Path
    metrics_path: Path
    coverage_target_default: float
    coverage_targets_path: Path
    random_state: int = 42
    targets_by_immunizer: dict[str, float] = field(default_factory=dict)


def load_coverage_targets(path: Path) -> dict[str, float]:
    """Metas por imunizante (`{"<imunizante>": <meta %>}`); opcional."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in raw.items()}


def load_settings() -> MlSettings:
    data_dir = _path("DATA_DIR", ROOT / "data")
    targets_path = _path("COVERAGE_TARGETS_PATH", data_dir / "external" / "coverage_targets.json")
    return MlSettings(
        processed_file=data_dir / "processed" / "vaccination.parquet",
        features_path=_path("FEATURES_PATH", data_dir / "processed" / "features.parquet"),
        ml_dataset_path=_path("ML_DATASET_PATH", data_dir / "processed" / "ml_dataset.parquet"),
        model_path=_path("MODEL_PATH", data_dir / "models" / "vax_deficit_model.joblib"),
        metrics_path=_path("METRICS_PATH", data_dir / "models" / "metrics.json"),
        coverage_target_default=float(os.getenv("COVERAGE_TARGET_DEFAULT", "95")),
        coverage_targets_path=targets_path,
        random_state=int(os.getenv("ML_RANDOM_STATE", "42")),
        targets_by_immunizer=load_coverage_targets(targets_path),
    )
