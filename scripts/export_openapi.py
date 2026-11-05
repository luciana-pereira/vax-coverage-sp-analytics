"""Exporta o contrato OpenAPI real da API e gera docs/api a partir dele.

Uso (na raiz): python scripts/export_openapi.py
Escreve docs/api/openapi.json e docs/api/endpoints.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "backend")]

from app.main import create_app  # noqa: E402

OUT = ROOT / "docs" / "api"


def ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def type_of(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return ref_name(schema["$ref"])
    for key in ("anyOf", "oneOf"):
        if key in schema:
            return " | ".join(type_of(s) for s in schema[key])
    if "enum" in schema:
        return " | ".join(f"`{v}`" for v in schema["enum"])
    kind = schema.get("type", "object")
    if kind == "array":
        return f"list[{type_of(schema.get('items', {}))}]"
    if kind == "object" and "additionalProperties" in schema:
        extra = schema["additionalProperties"]
        return f"dict[str, {type_of(extra) if isinstance(extra, dict) else 'any'}]"
    return str(kind)


def escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render(spec: dict[str, Any]) -> str:
    lines = [
        "# Endpoints da API",
        "",
        "> Gerado por `python scripts/export_openapi.py` a partir de `openapi.json`. "
        "Não edite à mão: altere os schemas/routers e regenere.",
        "",
        f"**{spec['info']['title']}** — versão {spec['info']['version']}",
        "",
        "Swagger UI: `/docs` · ReDoc: `/redoc` · Contrato: `/openapi.json`.",
        "",
        "## Endpoints",
        "",
        "| Método | Caminho | Resumo |",
        "|---|---|---|",
    ]
    for path, operations in spec["paths"].items():
        for method, op in operations.items():
            lines.append(f"| {method.upper()} | `{path}` | {escape(op['summary'])} |")

    for path, operations in spec["paths"].items():
        for method, op in operations.items():
            lines += ["", f"### {method.upper()} `{path}`", "", op["description"], ""]
            params = op.get("parameters", [])
            if params:
                lines += [
                    "| Parâmetro | Em | Tipo | Obrigatório | Descrição |",
                    "|---|---|---|---|---|",
                ]
                for p in params:
                    description = escape(p.get("description", ""))
                    required = "sim" if p.get("required") else "não"
                    lines.append(
                        f"| `{p['name']}` | {p['in']} | {escape(type_of(p['schema']))} | "
                        f"{required} | {description} |"
                    )
                lines.append("")
            lines += ["| Código | Corpo |", "|---|---|"]
            for code, response in op["responses"].items():
                content = response.get("content", {}).get("application/json", {})
                body = type_of(content["schema"]) if content else response["description"]
                lines.append(f"| {code} | {escape(body)} |")

    lines += ["", "## Schemas", ""]
    for name, schema in sorted(spec["components"]["schemas"].items()):
        if name in {"HTTPValidationError", "ValidationError"}:
            continue
        lines += [f"### {name}", ""]
        required = set(schema.get("required", []))
        lines += ["| Campo | Tipo | Obrigatório | Descrição |", "|---|---|---|---|"]
        for field, prop in schema.get("properties", {}).items():
            description = escape(prop.get("description", ""))
            flag = "sim" if field in required else "não"
            lines.append(f"| `{field}` | {escape(type_of(prop))} | {flag} | {description} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    spec = create_app().openapi()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "openapi.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUT / "endpoints.md").write_text(render(spec), encoding="utf-8")
    print(f"Escrito em {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
