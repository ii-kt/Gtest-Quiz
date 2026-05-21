"""Environment variable helpers (.env-first loading)."""

from __future__ import annotations

from pathlib import Path
import os

ROOT_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Load .env key-values into os.environ if not already set."""
    env_path = path or (ROOT_DIR / ".env")
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_env(key: str, default: str = "") -> str:
    load_dotenv()
    return os.environ.get(key, default)
