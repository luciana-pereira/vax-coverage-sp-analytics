"""Serviço de dados geográficos (GeoJSON municipal fornecido externamente)."""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas.data_quality import GeoResponse


class GeoService:
    def __init__(self, geojson_path: Path, code_property: str) -> None:
        self.geojson_path = geojson_path
        self.code_property = code_property

    def municipalities(self) -> GeoResponse:
        if not self.geojson_path.is_file():
            return GeoResponse(
                status="data_unavailable",
                message="GeoJSON municipal indisponível. Informe o arquivo em GEOJSON_PATH.",
            )
        data = json.loads(self.geojson_path.read_text(encoding="utf-8"))
        features = data.get("features") if isinstance(data, dict) else None
        if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
            return GeoResponse(
                status="data_unavailable", message="Arquivo não é um GeoJSON FeatureCollection."
            )
        if not isinstance(features, list):
            return GeoResponse(status="data_unavailable", message="GeoJSON sem lista 'features'.")
        return GeoResponse(
            status="ok",
            code_property=self.code_property or None,
            message=None
            if self.code_property
            else "GEOJSON_CODE_PROPERTY não configurada: não é possível ligar dados aos polígonos.",
            feature_count=len(features),
            geojson=data,
        )
