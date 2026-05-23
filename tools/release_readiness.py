from __future__ import annotations

import json
import sys
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.experiments import ADAPTIVE_POLICY
from backend.app.services import QuizService, UnauthorizedError
from gtest_quiz.question_bank import get_all_questions
from tools.benchmark_learning_policy import compare_policy_benchmarks
from tools.validate_question_bank import validate_question_bank


def _check(name: str, passed: bool, detail: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {"name": name, "passed": passed, "detail": detail or {}}


def evaluate_release_readiness() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    bank_errors = validate_question_bank()
    questions = get_all_questions()
    chapters = {q.chapter_id for q in questions}
    contract_text = Path("docs/api/openapi_contract_v1.json").read_text(encoding="utf-8")
    schema_source = Path("backend/app/schemas.py").read_text(encoding="utf-8")
    question_dto_source = schema_source.split("class QuestionDTO", 1)[1].split("class AnswerRequest", 1)[0]
    frontend = Path("frontend/src/index.html").read_text(encoding="utf-8")
    offline_app = Path("frontend/src/offline-app.js").read_text(encoding="utf-8")
    service_worker = Path("frontend/src/service-worker.js").read_text(encoding="utf-8")
    static_bank = json.loads(Path("frontend/src/question-bank.json").read_text(encoding="utf-8"))
    pages_workflow = Path(".github/workflows/static-pwa-pages.yml").read_text(encoding="utf-8")
    operations_source = Path("backend/app/api/operations.py").read_text(encoding="utf-8")
    benchmark = compare_policy_benchmarks(seed=11, rounds=120)
    adaptive = benchmark["results"][ADAPTIVE_POLICY]
    service_smoke = _run_service_smoke()

    checks.append(_check("question_bank_valid", not bank_errors, {"errors": bank_errors[:5]}))
    checks.append(
        _check(
            "syllabus_coverage",
            len(questions) >= 100 and len(chapters) >= 20,
            {"questions": len(questions), "chapters": len(chapters)},
        )
    )
    checks.append(
        _check(
            "answer_key_safety",
            "correct_index" not in question_dto_source and "explanation" not in question_dto_source,
            {"contract": "docs/api/openapi_contract_v1.json"},
        )
    )
    checks.append(
        _check(
            "pwa_and_recovery_ui",
            Path("frontend/src/manifest.webmanifest").exists()
            and Path("frontend/src/service-worker.js").exists()
            and Path("frontend/src/question-bank.json").exists()
            and Path("frontend/src/offline-app.js").exists()
            and "exportAccount" in offline_app
            and "importAccount" in offline_app
            and "question-bank.json" in service_worker,
        )
    )
    checks.append(
        _check(
            "static_offline_pwa",
            static_bank.get("schema_version") == "gtest_quiz_static_bank_v1"
            and len(static_bank.get("questions", [])) == len(questions)
            and "http://localhost" not in frontend
            and "http://localhost" not in offline_app
            and "/api/v1" not in frontend
            and "/api/v1" not in offline_app
            and "localStorage" in offline_app
            and "selectNextQuestion" in offline_app
            and "updateSchedule" in offline_app,
            {"static_questions": len(static_bank.get("questions", []))},
        )
    )
    checks.append(
        _check(
            "zero_cost_static_delivery",
            Path("frontend/src/.nojekyll").exists()
            and "actions/upload-pages-artifact" in pages_workflow
            and "actions/deploy-pages" in pages_workflow
            and "path: frontend/src" in pages_workflow,
        )
    )
    checks.append(
        _check(
            "session_auth_model",
            "/api/v1/auth/start" in contract_text
            and "/api/v1/auth/refresh" in contract_text
            and "/api/v1/auth/login" not in contract_text
            and "/api/v1/auth/register" not in contract_text
            and "password" not in frontend.lower()
            and "password" not in offline_app.lower()
            and "LoginRequest" not in schema_source
            and "RegisterRequest" not in schema_source,
        )
    )
    checks.append(
        _check(
            "account_recovery_contract",
            "/api/v1/account/export" in contract_text
            and "/api/v1/account/import" in contract_text
            and "/api/v1/account/audit" in contract_text,
        )
    )
    checks.append(
        _check(
            "observability_contract",
            "/api/v1/operations/metrics" in contract_text
            and "user_from_authorization" in operations_source,
        )
    )
    checks.append(_check("service_smoke", service_smoke["passed"], service_smoke))
    checks.append(
        _check(
            "precision_benchmark",
            adaptive["scheduled_items"] >= 90 and adaptive["covered_chapters"] >= 20,
            {"adaptive": adaptive, "deltas": benchmark["deltas"]},
        )
    )
    checks.append(
        _check(
            "deployment_profiles",
            all((Path("deploy/profiles") / f"{name}.json").exists() for name in ["local", "classroom", "hosted"]),
        )
    )
    passed = all(check["passed"] for check in checks)
    return {"passed": passed, "checks": checks, "benchmark": benchmark}


def _run_service_smoke() -> Dict[str, Any]:
    runtime_root = Path(".runtime/release_readiness").resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=str(runtime_root), ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        service = QuizService(db_path=str(root / "quiz.db"), meta_path=str(root / "meta.json"))
        created = service.start_session()
        user = service.user_from_token(created["token"])
        refreshed = service.refresh_session(int(user["id"]))
        try:
            service.user_from_token(created["token"])
            old_token_revoked = False
        except UnauthorizedError:
            old_token_revoked = True
        user = service.user_from_token(refreshed["token"])
        selection = service.next_question(int(user["id"]))
        if selection is None:
            return {"passed": False, "reason": "no question"}
        wrong_index = next(idx for idx in range(4) if idx != selection.question.correct_index)
        service.import_account(
            int(user["id"]),
            {
                "answers": [
                    {
                        "question_id": selection.question.id,
                        "chapter_id": "forged",
                        "selected_index": wrong_index,
                        "correct": 1,
                    }
                ],
                "learning_items": [],
            },
        )
        stats = service.storage.user_stats(int(user["id"]))
        return {
            "passed": old_token_revoked and stats["correct_answers"] == 0,
            "old_token_revoked": old_token_revoked,
            "import_recomputed_correctness": stats["correct_answers"] == 0,
        }


def main() -> None:
    result = evaluate_release_readiness()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
