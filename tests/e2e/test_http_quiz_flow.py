import json
import os
import threading
import urllib.error
import urllib.request

import pytest

from backend.app.main import create_server
from backend.app.services import QuizService


def _post(url: str, body: dict, headers: dict | None = None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={**({"Content-Type": "application/json"}), **(headers or {})},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=3)


@pytest.mark.e2e
def test_http_quiz_flow_end_to_end():
    db_path = ".runtime/test_e2e_quiz.db"
    meta_path = ".runtime/test_e2e_meta.json"
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(meta_path):
        os.remove(meta_path)

    service = QuizService(db_path=db_path, meta_path=meta_path)
    server = create_server(host="127.0.0.1", port=18081, service=service)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        with _post("http://127.0.0.1:18081/auth/start", {}) as r:
            created = json.loads(r.read().decode("utf-8"))
            token = created["token"]

        headers = {"Authorization": f"Bearer {token}"}
        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18081/quiz/next", headers=headers), timeout=3) as r:
            q = json.loads(r.read().decode("utf-8"))
            assert "id" in q and len(q.get("choices", [])) == 4
            assert "correct_index" not in q
            assert "explanation" not in q

        with _post(
            "http://127.0.0.1:18081/quiz/answer",
            {"question_id": q["id"], "selected_index": 0, "elapsed_ms": 900},
            headers=headers,
        ) as r:
            ans = json.loads(r.read().decode("utf-8"))
            assert isinstance(ans.get("correct"), bool)
            assert 0 <= int(ans.get("correct_index", -1)) <= 3
            assert isinstance(ans.get("explanation"), str)
            assert isinstance(ans.get("correct_choice"), str)
            assert ans.get("learning", {}).get("schedule", {}).get("due_at")

        try:
            _post(
                "http://127.0.0.1:18081/quiz/answer",
                {"question_id": q["id"], "selected_index": 999},
                headers=headers,
            )
            assert False, "expected HTTP 400"
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        server.shutdown()
        server.server_close()
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)
