from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.asgi import create_app


CONTRACT_PATH = Path("docs/api/openapi_contract_v1.json")


def _schema_name(schema: Dict[str, Any]) -> str | None:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        return ref.rsplit("/", 1)[-1]
    return None


def normalize_openapi_contract(openapi: Dict[str, Any]) -> Dict[str, Any]:
    paths: Dict[str, Any] = {}
    for path, operations in openapi.get("paths", {}).items():
        if not path.startswith("/api/v1/"):
            continue
        normalized_ops: Dict[str, Any] = {}
        for method, operation in operations.items():
            responses = operation.get("responses", {})
            success_schema = (
                responses.get("200", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            if method == "post" and "201" in responses:
                success_schema = (
                    responses.get("201", {})
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )

            request_schema = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            spec: Dict[str, Any] = {
                "tag": (operation.get("tags") or [""])[0],
                "status_codes": sorted(responses.keys()),
            }
            req_name = _schema_name(request_schema)
            res_name = _schema_name(success_schema)
            if req_name:
                spec["request_schema"] = req_name
            if res_name:
                spec["response_schema"] = res_name
            normalized_ops[method] = spec
        paths[path] = normalized_ops

    return {
        "version": "v1",
        "paths": dict(sorted(paths.items())),
    }


def main() -> None:
    contract = normalize_openapi_contract(create_app().openapi())
    CONTRACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT_PATH.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
