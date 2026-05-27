from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


def load_result(path: Path) -> Dict[str, Any]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            text = raw.decode(encoding).strip()
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise SystemExit(f"invalid refill result JSON: {path}: {exc}") from exc
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise SystemExit(f"refill result must be a JSON object: {path}")
    return data


def assert_refill_result(result: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    mode = str(result.get("mode", "daily"))
    accepted = int(result.get("accepted", 0) or 0)
    errors_count = int(result.get("errors", 0) or 0)
    rate_limit_errors = int(result.get("rate_limit_errors", 0) or 0)
    target = int(result.get("target", result.get("target_accepts", 0)) or 0)

    if errors_count > 0 and accepted == 0:
        errors.append("errors > 0 and accepted == 0")
    if mode == "reset_and_seed" and accepted == 0:
        errors.append("reset_and_seed requires accepted >= 1")
    if mode in {"seed", "build_to_complete", "build_to_expanded"} and target > 0 and accepted == 0:
        errors.append(f"{mode} with target > 0 requires accepted >= 1")
    if mode == "daily" and accepted == 0 and rate_limit_errors == 0:
        errors.append("daily accepted == 0 without a rate-limit/quota signal")
    if mode == "replace" and target > 0 and accepted == 0 and rate_limit_errors == 0:
        errors.append("replace with target > 0 accepted == 0 without a rate-limit/quota signal")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail CI when a refill run silently generated no accepted content.")
    parser.add_argument("path", nargs="?", default="refill-result.json")
    args = parser.parse_args()

    result = load_result(Path(args.path))
    errors = assert_refill_result(result)
    print(json.dumps({"passed": not errors, "errors": errors, "accepted": result.get("accepted", 0)}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
