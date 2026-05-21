import json
import threading
import urllib.error
import urllib.request

import pytest

from backend.app.main import create_server


def _post(url: str, body: dict, headers: dict | None = None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode('utf-8'),
        headers={**({'Content-Type': 'application/json'}), **(headers or {})},
        method='POST',
    )
    return urllib.request.urlopen(req, timeout=3)


@pytest.mark.e2e
def test_http_quiz_flow_end_to_end():
    server = create_server(host='127.0.0.1', port=18081)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        import time
        with _post('http://127.0.0.1:18081/auth/register', {'username': f'e2e_{int(time.time()*1000)}'}) as r:
            created = json.loads(r.read().decode('utf-8'))
            token = created['token']

        headers = {'Authorization': f'Bearer {token}'}
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18081/quiz/next', headers=headers), timeout=3) as r:
            q = json.loads(r.read().decode('utf-8'))
            assert 'id' in q and len(q.get('choices', [])) == 4

        with _post(
            'http://127.0.0.1:18081/quiz/answer',
            {'question_id': q['id'], 'selected_index': 0},
            headers=headers,
        ) as r:
            ans = json.loads(r.read().decode('utf-8'))
            assert isinstance(ans.get('correct'), bool)
            assert 0 <= int(ans.get('correct_index', -1)) <= 3
            assert isinstance(ans.get('explanation'), str)

        try:
            _post(
                'http://127.0.0.1:18081/quiz/answer',
                {'question_id': q['id'], 'selected_index': 999},
                headers=headers,
            )
            assert False, 'expected HTTP 400'
        except urllib.error.HTTPError as e:
            assert e.code == 400
    finally:
        server.shutdown()
        server.server_close()
