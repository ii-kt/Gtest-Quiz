from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "bank/question_bank.jsonl"
FRONTEND = ROOT / "frontend/src"
STATIC_BANK_PATH = FRONTEND / "question-bank.json"


def load_questions() -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []
    for line in BANK_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        questions.append(
            {
                "id": row["id"],
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


def write_static_bank() -> int:
    questions = load_questions()
    payload = {
        "schema_version": "gtest_quiz_static_bank_v1",
        "meta": {
            "generated_at": "2026-05-22T00:00:00Z",
            "source": "bank/question_bank.jsonl",
            "question_count": len(questions),
        },
        "questions": questions,
    }
    STATIC_BANK_PATH.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return len(questions)


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
    count = write_static_bank()
    for size in (180, 192, 512):
        write_icon(FRONTEND / f"pwa-icon-{size}.png", size)
    print(json.dumps({"questions": count, "icons": [180, 192, 512]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
