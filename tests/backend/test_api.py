import json
import os
import threading
import urllib.error
import urllib.request

from backend.app.main import create_server


def _post(url: str, body: dict, headers: dict | None = None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers={**({'Content-Type': 'application/json'}), **(headers or {})},
        method='POST',
    )
    return urllib.request.urlopen(req, timeout=3)


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
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 401
    finally:
        server.shutdown()
        server.server_close()
        if os.path.exists(db_path):
            os.remove(db_path)
