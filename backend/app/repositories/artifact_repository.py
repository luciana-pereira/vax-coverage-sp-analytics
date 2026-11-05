"""Acesso a artefatos em disco: métricas, GeoJSON e status de arquivos."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ArtifactRepository:
    def __init__(self, root: Path) -> None:
        self.root = root

    def relative(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return path.name

    @staticmethod
    def read_json(path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def size(path: Path) -> int | None:
        if path.is_file():
            return path.stat().st_size
        if path.is_dir():
            return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return None
