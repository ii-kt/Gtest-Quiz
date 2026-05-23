from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


DEFAULT_PROFILE = "local"
PROFILE_DIR = Path("deploy/profiles")


def current_profile_name() -> str:
    return os.getenv("GTEST_DEPLOYMENT_PROFILE", DEFAULT_PROFILE).strip() or DEFAULT_PROFILE


def load_deployment_profile(name: str | None = None) -> Dict[str, Any]:
    profile_name = name or current_profile_name()
    path = PROFILE_DIR / f"{profile_name}.json"
    if not path.exists():
        profile_name = DEFAULT_PROFILE
        path = PROFILE_DIR / f"{profile_name}.json"
    if not path.exists():
        return {"name": profile_name, "mode": "development", "session_ttl_hours": 168}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("name", profile_name)
    return data


def configured_host(default: str = "127.0.0.1") -> str:
    return os.getenv("GTEST_HOST") or str(load_deployment_profile().get("host") or default)


def configured_port(default: int = 8000) -> int:
    value = os.getenv("GTEST_PORT") or load_deployment_profile().get("port") or default
    return int(value)


def configured_db_path(default: str = ".runtime/quiz.db") -> str:
    return os.getenv("GTEST_DB_PATH") or str(load_deployment_profile().get("sqlite_path") or default)


def apply_profile_environment() -> None:
    profile = load_deployment_profile()
    os.environ.setdefault("GTEST_SESSION_TTL_HOURS", str(profile.get("session_ttl_hours", 168)))
