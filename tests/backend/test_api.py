import json
import os
import threading
import urllib.error
import urllib.request

from backend.app.main import create_server
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
from backend.app.services import QuizService
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs


def _post(url: str, body: dict, headers: dict | None = None):
    req = urllib.request.Request(
        url,
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
        data=json.dumps(body).encode("utf-8"),
        headers={**({"Content-Type": "application/json"}), **(headers or {})},
        method="POST",
=======
        data=json.dumps(body).encode('utf-8'),
        headers={**({'Content-Type': 'application/json'}), **(headers or {})},
        method='POST',
>>>>>>> theirs
=======
        data=json.dumps(body).encode('utf-8'),
        headers={**({'Content-Type': 'application/json'}), **(headers or {})},
        method='POST',
>>>>>>> theirs
=======
        data=json.dumps(body).encode('utf-8'),
        headers={**({'Content-Type': 'application/json'}), **(headers or {})},
        method='POST',
>>>>>>> theirs
=======
        data=json.dumps(body).encode('utf-8'),
        headers={**({'Content-Type': 'application/json'}), **(headers or {})},
        method='POST',
>>>>>>> theirs
=======
        data=json.dumps(body).encode('utf-8'),
        headers={**({'Content-Type': 'application/json'}), **(headers or {})},
        method='POST',
>>>>>>> theirs
    )
    return urllib.request.urlopen(req, timeout=3)


<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
def test_http_session_and_quiz_flow():
    db_path = ".runtime/test_quiz.db"
    meta_path = ".runtime/test_meta.json"
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(meta_path):
        os.remove(meta_path)

    service = QuizService(db_path=db_path, meta_path=meta_path)
    server = create_server(host="127.0.0.1", port=18080, service=service)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        with _post("http://127.0.0.1:18080/auth/start", {}) as r:
            created = json.loads(r.read().decode("utf-8"))
            token = created["token"]
            assert created["learner_id"].startswith("L")
            assert created["session_expires_at"]

        old_headers = {"Authorization": f"Bearer {token}"}
        with _post("http://127.0.0.1:18080/api/v1/auth/refresh", {}, headers=old_headers) as r:
            refreshed = json.loads(r.read().decode("utf-8"))
            token = refreshed["token"]
            assert token != created["token"]

        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18080/quiz/stats", headers=old_headers), timeout=3)
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 401

        headers = {"Authorization": f"Bearer {token}"}

        with urllib.request.urlopen("http://127.0.0.1:18080/api/v1/health", timeout=3) as r:
            health = json.loads(r.read().decode("utf-8"))
            assert health["status"] == "ok"
            assert health["api_version"] == "v1"
            assert r.headers.get("X-Request-ID")

        with urllib.request.urlopen("http://127.0.0.1:18080/api/v1/content/questions/summary", timeout=3) as r:
            summary = json.loads(r.read().decode("utf-8"))
            assert summary["total_questions"] > 0

        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18080/quiz/next", headers=headers), timeout=3) as r:
            q = json.loads(r.read().decode("utf-8"))
            assert "id" in q
            assert "correct_index" not in q
            assert "explanation" not in q
            assert q.get("learning", {}).get("strategy")

        with _post("http://127.0.0.1:18080/quiz/answer", {"question_id": q["id"], "selected_index": 0, "elapsed_ms": 1200}, headers=headers) as r:
            ans = json.loads(r.read().decode("utf-8"))
            assert "correct" in ans
            assert "correct_choice" in ans

        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18080/quiz/stats", headers=headers), timeout=3) as r:
            st = json.loads(r.read().decode("utf-8"))
            assert st["user"]["total_answers"] >= 1
            assert st["user"]["learning"]["mastery_model"] == "adaptive_mastery_v2"
            assert st["user"]["learning"]["selection_policy"] == "adaptive_mastery_v2"

        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18080/api/v1/learning/plan", headers=headers), timeout=3) as r:
            plan = json.loads(r.read().decode("utf-8"))
            assert plan["schedule"]["tracked_items"] >= 1

        with _post(
            "http://127.0.0.1:18080/api/v1/learning/policy",
            {"policy_variant": "chapter_balanced_v1"},
            headers=headers,
        ) as r:
            policy = json.loads(r.read().decode("utf-8"))
            assert policy["policy_variant"] == "chapter_balanced_v1"

        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18080/api/v1/account/export", headers=headers), timeout=3) as r:
            exported = json.loads(r.read().decode("utf-8"))
            assert exported["schema_version"] == "gtest_quiz_export_v1"
            assert exported["answers"]

        with _post("http://127.0.0.1:18080/api/v1/account/import", {"bundle": exported}, headers=headers) as r:
            imported = json.loads(r.read().decode("utf-8"))
            assert imported["imported_answers"] >= 1

        try:
            urllib.request.urlopen("http://127.0.0.1:18080/api/v1/operations/metrics", timeout=3)
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 401

        with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18080/api/v1/operations/metrics", headers=headers), timeout=3) as r:
            metrics = json.loads(r.read().decode("utf-8"))
            assert metrics["observability"]["requests"]["total"] >= 1

        bad_headers = {"Authorization": "Bearer invalid"}
        try:
            urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18080/quiz/stats", headers=bad_headers), timeout=3)
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
def test_http_auth_and_quiz_flow():
    db_path = 'backend/app/test_quiz.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    server = create_server(host='127.0.0.1', port=18080)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        import time
        uname = f'tester_{int(time.time()*1000)}'
        with _post('http://127.0.0.1:18080/auth/register', {'username': uname}) as r:
            created = json.loads(r.read().decode('utf-8'))
            token = created['token']
            assert created['username'] == uname

        # login rotates token
        with _post('http://127.0.0.1:18080/auth/login', {'username': uname}) as r:
            logged = json.loads(r.read().decode('utf-8'))
            token = logged['token']
            assert logged['username'] == uname

        headers = {'Authorization': f'Bearer {token}'}

        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18080/quiz/next', headers=headers), timeout=3) as r:
            q = json.loads(r.read().decode('utf-8'))
            assert 'id' in q

        with _post('http://127.0.0.1:18080/quiz/answer', {'question_id': q['id'], 'selected_index': 0}, headers=headers) as r:
            ans = json.loads(r.read().decode('utf-8'))
            assert 'correct' in ans

        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18080/quiz/stats', headers=headers), timeout=3) as r:
            st = json.loads(r.read().decode('utf-8'))
            assert 'global' in st and 'user' in st
            assert st['user']['total_answers'] >= 1

        # duplicate register should conflict
        try:
            _post('http://127.0.0.1:18080/auth/register', {'username': uname})
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 409

        bad_headers = {'Authorization': 'Bearer invalid'}
        try:
            urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18080/quiz/stats', headers=bad_headers), timeout=3)
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 401
    finally:
        server.shutdown()
        server.server_close()
        if os.path.exists(db_path):
            os.remove(db_path)
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
        if os.path.exists(meta_path):
            os.remove(meta_path)
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
