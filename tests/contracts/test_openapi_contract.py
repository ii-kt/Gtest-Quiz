import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from backend.app.asgi import create_app
from tools.export_openapi_contract import normalize_openapi_contract

pytestmark = pytest.mark.contract


def test_openapi_contract_has_not_drifted():
    expected = json.loads(Path("docs/api/openapi_contract_v1.json").read_text(encoding="utf-8"))
    actual = normalize_openapi_contract(create_app().openapi())
    assert actual == expected


def test_question_payload_does_not_expose_answer_material():
    schema = create_app().openapi()["components"]["schemas"]["QuestionDTO"]
    properties = schema["properties"]
    assert "correct_index" not in properties
    assert "explanation" not in properties
    assert {"id", "question", "choices", "learning"}.issubset(properties)


def test_answer_payload_contains_post_submission_feedback():
    schema = create_app().openapi()["components"]["schemas"]["AnswerResult"]
    properties = schema["properties"]
    assert {"correct", "selected_index", "correct_index", "correct_choice", "explanation", "learning"}.issubset(properties)
