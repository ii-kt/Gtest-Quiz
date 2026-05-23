from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict


def new_request_id() -> str:
    return uuid.uuid4().hex


def monotonic_ms() -> float:
    return time.perf_counter() * 1000


def route_family(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        return f"/api/v1/{parts[2]}"
    if parts:
        return f"/{parts[0]}"
    return "/"


def structured_log(event: str, **fields: Any) -> None:
    payload: Dict[str, Any] = {"event": event, **fields}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
