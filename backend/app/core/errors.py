"""Erros de domínio traduzidos em respostas HTTP pelo `main`."""

from __future__ import annotations


class NotFoundError(Exception):
    """Recurso inexistente (ex.: município sem registros)."""
