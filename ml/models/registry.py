"""Candidatos de modelo previstos na PI IV (contratos, sem treino)."""

from __future__ import annotations

from sklearn.base import ClassifierMixin
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

MODEL_NAMES = ("logistic_regression", "random_forest", "gradient_boosting")


def build_candidates(random_state: int = 42) -> dict[str, ClassifierMixin]:
    return {
        "logistic_regression": LogisticRegression(max_iter=2000),
        "random_forest": RandomForestClassifier(
            n_estimators=300, random_state=random_state, class_weight="balanced"
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=random_state),
    }
