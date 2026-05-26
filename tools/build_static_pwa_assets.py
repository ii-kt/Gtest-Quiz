from __future__ import annotations

import json
import struct
import sys
import zlib
import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gtest_quiz.bank_epoch import current_bank_version

BANK_PATH = ROOT / "bank/question_bank.jsonl"
FRONTEND = ROOT / "frontend/src"
STATIC_BANK_PATH = FRONTEND / "question-bank.json"
SERVICE_WORKER_PATH = FRONTEND / "service-worker.js"
META_PATH = ROOT / "bank/meta.json"


def load_bank_version() -> str:
    if META_PATH.exists():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        version = str(meta.get("bank_version", "")).strip()
        if version:
            return version
    return current_bank_version()


def load_questions() -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []
    for line in BANK_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        questions.append(
            {
                "id": row["id"],
                "bank_version": row.get("bank_version", load_bank_version()),
                "domain": row.get("domain", ""),
                "chapter_group": row.get("chapter_group", ""),
                "chapter_id": row.get("chapter_id", ""),
                "difficulty": row.get("difficulty", "standard"),
                "question": row.get("question", ""),
                "choices": list(row.get("choices", [])),
                "correct_index": int(row.get("correct_index", 0)),
                "explanation": row.get("explanation", ""),
                "syllabus": row.get("syllabus", ""),
            }
        )
    return questions


def _canonical_content(questions: List[Dict[str, Any]], bank_version: str) -> str:
    return json.dumps(
        {"bank_version": bank_version, "questions": questions},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _write_text_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def update_service_worker_cache_name(bank_version: str, content_hash: str) -> str:
    cache_name = f"gtest-quiz-static-{bank_version}-{content_hash[:12]}"
    worker = SERVICE_WORKER_PATH.read_text(encoding="utf-8")
    updated = re.sub(
        r"const CACHE_NAME = '[^']+';",
        f"const CACHE_NAME = '{cache_name}';",
        worker,
        count=1,
    )
    if updated != worker:
        SERVICE_WORKER_PATH.write_text(updated, encoding="utf-8")
    return cache_name


def write_static_bank() -> Dict[str, Any]:
    questions = load_questions()
    bank_version = load_bank_version()
    content_hash = hashlib.sha256(_canonical_content(questions, bank_version).encode("utf-8")).hexdigest()
    payload = {
        "schema_version": "gtest_quiz_static_bank_v1",
        "meta": {
            "source": "bank/question_bank.jsonl",
            "question_count": len(questions),
            "bank_version": bank_version,
            "content_hash": content_hash,
        },
        "questions": questions,
    }
    changed = _write_text_if_changed(
        STATIC_BANK_PATH,
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )
    cache_name = update_service_worker_cache_name(bank_version, content_hash)
    return {
        "questions": len(questions),
        "bank_version": bank_version,
        "content_hash": content_hash,
        "cache_name": cache_name,
        "static_bank_changed": changed,
    }


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_icon(path: Path, size: int) -> None:
    rows = []
    pad = size * 0.12
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            inside = pad <= x < size - pad and pad <= y < size - pad
            if not inside:
                rgba = (247, 248, 250, 0)
            else:
                nx = (x - pad) / max(1, (size - 2 * pad))
                ny = (y - pad) / max(1, (size - 2 * pad))
                rgba = (int(16 + 15 * ny), int(24 + 95 * nx), int(40 + 70 * (1 - ny)), 255)
                cx = size / 2
                cy = size / 2
                if abs(x - cx) < size * 0.18 and abs(y - cy) < size * 0.08:
                    rgba = (255, 255, 255, 255)
                if abs(x - cx) < size * 0.08 and abs(y - cy) < size * 0.22:
                    rgba = (255, 255, 255, 255)
            row.extend(rgba)
        rows.append(bytes(row))

    raw = b"".join(rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += png_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
    png += png_chunk(b"IDAT", zlib.compress(raw, 9))
    png += png_chunk(b"IEND", b"")
    path.write_bytes(png)


def main() -> None:
    result = write_static_bank()
    for size in (180, 192, 512):
        write_icon(FRONTEND / f"pwa-icon-{size}.png", size)
    result["icons"] = [180, 192, 512]
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
