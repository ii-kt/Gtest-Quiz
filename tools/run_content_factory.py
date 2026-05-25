from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gtest_quiz.bank_epoch import current_bank_version, current_model_name
from gtest_quiz.content_factory import ContentFactory, FactoryConfig, GeneratedQuestionSpec
from gtest_quiz.refill_pipeline import GeminiQuestionGenerator
from gtest_quiz.env import get_env, load_dotenv


class DryRunGenerator:
    def generate(self, prompt: str, schema: type[GeneratedQuestionSpec]) -> Dict[str, Any]:
        return {
            "question": "G検定の学習で汎化性能を確認する目的として最も適切なものはどれか。",
            "choices": [
                "未知データに対する性能を見積もるため",
                "訓練データを暗号化するため",
                "モデルの重みを固定するため",
                "入力データを削除するため",
            ],
            "correct_index": 0,
            "explanation": "汎化性能は未知データに対してモデルがどれだけ適切に振る舞うかを示す。訓練データだけの性能では過学習を見逃す可能性があるため、検証データやテストデータで確認する。",
            "difficulty": "standard",
            "syllabus_node": "10. モデルの選択・評価",
            "concepts": ["汎化性能", "過学習", "評価"],
            "source_hint": "dry-run",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Gtest content factory")
    parser.add_argument("--dry-run", action="store_true", help="Use a deterministic local generator")
    parser.add_argument("--target", type=int, default=5, help="Accepted question target")
    parser.add_argument("--model", default=current_model_name())
    args = parser.parse_args()

    if args.dry_run:
        generator = DryRunGenerator()
    else:
        load_dotenv()
        key = get_env("GEMINI_API_KEY")
        if not key:
            raise SystemExit("GEMINI_API_KEY is not set")
        generator = GeminiQuestionGenerator(api_key=key, model_name=args.model)

    factory = ContentFactory(
        FactoryConfig(model_name=args.model, target_accepts=args.target, bank_version=current_bank_version()),
        generator,
    )
    stats = factory.run()
    print(json.dumps(stats.__dict__, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
