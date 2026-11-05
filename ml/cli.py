"""CLI de ML: features -> train -> evaluate -> predict.

Uso: python -m ml.cli <features|train|evaluate|predict>
Depende da saída de `python -m pipeline.cli transform`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys

import pandas as pd

from .config import MlSettings, load_settings
from .evaluation.evaluate import load_metrics
from .features.build_features import (
    DEFICIT_LABELS,
    TARGET_COLUMN,
    build_ml_dataset,
    build_vaccination_features,
    feature_columns,
)
from .inference.predict import load_feature_list, load_model, predict_with_probabilities
from .training.train import train_models

logger = logging.getLogger("ml")


def cmd_features(settings: MlSettings) -> None:
    if not settings.processed_file.exists():
        raise FileNotFoundError(
            f"Dados processados ausentes: {settings.processed_file}. Execute o pipeline."
        )
    df = pd.read_parquet(settings.processed_file)
    required = {"doses", "population", "year"}
    if not required.issubset(df.columns):
        raise RuntimeError(
            f"Colunas ausentes {sorted(required - set(df.columns))}: mapeie as colunas reais "
            "da fonte (docs/data/pipeline.md)."
        )

    features = build_vaccination_features(
        df,
        "doses",
        "population",
        "year",
        meta=settings.coverage_target_default,
        immunizer_col="immunizer" if "immunizer" in df.columns else None,
        targets=settings.targets_by_immunizer or None,
    )
    settings.features_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(settings.features_path, index=False)
    dataset = build_ml_dataset(features)
    dataset.to_parquet(settings.ml_dataset_path, index=False)
    logger.info(
        "features=%s linhas (%s); dataset ML=%s linhas (%s)",
        len(features),
        settings.features_path,
        len(dataset),
        settings.ml_dataset_path,
    )


def cmd_train(settings: MlSettings) -> None:
    if not settings.ml_dataset_path.exists():
        raise FileNotFoundError("Dataset de ML ausente. Execute 'features' primeiro.")
    dataset = pd.read_parquet(settings.ml_dataset_path)
    report = train_models(
        dataset,
        features=feature_columns(dataset),
        target=TARGET_COLUMN,
        year_col="year",
        model_path=settings.model_path,
        metrics_path=settings.metrics_path,
        class_order=DEFICIT_LABELS,
        baseline_col="deficit_class",
        random_state=settings.random_state,
    )
    logger.info("Melhor modelo: %s (%s)", report["best_model"], settings.model_path)


def cmd_evaluate(settings: MlSettings) -> None:
    if not settings.metrics_path.exists():
        raise FileNotFoundError("Relatório de métricas ausente. Execute 'train'.")
    report = load_metrics(settings.metrics_path)
    for name, entry in report["models"].items():
        test = entry["test"]
        logger.info(
            "%s: f1_macro=%.3f precision_macro=%.3f recall_macro=%.3f",
            name,
            test["f1_macro"],
            test["precision_macro"],
            test["recall_macro"],
        )
    logger.info("Melhor modelo: %s", report["best_model"])
    print(json.dumps(report["split"], indent=2, ensure_ascii=False))


def cmd_predict(settings: MlSettings) -> None:
    if not settings.model_path.exists():
        raise FileNotFoundError("Modelo ausente. Execute 'train'.")
    dataset = pd.read_parquet(settings.ml_dataset_path)
    pending = dataset[dataset[TARGET_COLUMN].isna()]
    if pending.empty:
        raise RuntimeError("Sem linhas sem rótulo para inferência (nenhum período futuro).")
    latest = pending[pending["year"] == pending["year"].max()]
    features = load_feature_list(settings.metrics_path)
    result = predict_with_probabilities(load_model(settings.model_path), latest[features])
    logger.info("Predições: %s", result["prediction"].value_counts().to_dict())


COMMANDS = {
    "features": cmd_features,
    "train": cmd_train,
    "evaluate": cmd_evaluate,
    "predict": cmd_predict,
}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="ml")
    parser.add_argument("command", choices=list(COMMANDS))
    args = parser.parse_args(argv)
    try:
        COMMANDS[args.command](load_settings())
    except (FileNotFoundError, RuntimeError, KeyError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
