from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PNISource:
    year: int
    base_url: str
    endpoint: str

    @property
    def url(self) -> str:
        return f"{self.base_url.rstrip('/')}{self.endpoint}"


def build_pni_source(
    year: int,
    base_url: str = "https://apidadosabertos.saude.gov.br",
) -> PNISource:
    if year < 2020:
        raise ValueError("O PNI possui endpoint anual a partir de 2020.")

    endpoint = f"/vacinacao/doses-aplicadas-pni-{year}"

    return PNISource(
        year=year,
        base_url=base_url,
        endpoint=endpoint,
    )