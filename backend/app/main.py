from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse

from .schemas import (
    AnswerRequest,
    AnswerResult,
    LoginRequest,
    LoginResponse,
    QuestionDTO,
    RegisterRequest,
    RegisterResponse,
)
from .services import (
    InvalidAnswerIndexError,
    QuestionNotFoundError,
    QuizService,
    UnauthorizedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)

service = QuizService()


def _extract_token(handler: BaseHTTPRequestHandler) -> str:
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.replace("Bearer ", "", 1).strip()
    raise UnauthorizedError("missing bearer token")


def _json_response(handler: BaseHTTPRequestHandler, status: int, body: Dict[str, Any]) -> None:
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(raw)


class QuizHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            return _json_response(self, HTTPStatus.OK, {"status": "ok"})

        try:
            token = _extract_token(self)
            user = service.user_from_token(token)
        except UnauthorizedError as e:
            return _json_response(self, HTTPStatus.UNAUTHORIZED, {"detail": str(e)})

        if path == "/quiz/next":
            q = service.next_question(user["id"])
            if q is None:
                return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": "No question available"})
            return _json_response(self, HTTPStatus.OK, QuestionDTO(**q.to_dict()).model_dump())

        if path == "/quiz/stats":
            return _json_response(self, HTTPStatus.OK, service.stats(user["id"]))

        return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length) if length > 0 else b"{}"

        if path == "/auth/register":
            try:
                data = RegisterRequest(**json.loads(payload.decode("utf-8")))
                created = service.register(data.username)
                return _json_response(self, HTTPStatus.CREATED, RegisterResponse(**created).model_dump())
            except UserAlreadyExistsError as e:
                return _json_response(self, HTTPStatus.CONFLICT, {"detail": str(e)})
            except Exception as e:  # noqa: BLE001
                return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": f"Invalid request: {e}"})

        if path == "/auth/login":
            try:
                data = LoginRequest(**json.loads(payload.decode("utf-8")))
                created = service.login(data.username)
                return _json_response(self, HTTPStatus.OK, LoginResponse(**created).model_dump())
            except UserNotFoundError as e:
                return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": str(e)})
            except Exception as e:  # noqa: BLE001
                return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": f"Invalid request: {e}"})

        try:
            token = _extract_token(self)
            user = service.user_from_token(token)
        except UnauthorizedError as e:
            return _json_response(self, HTTPStatus.UNAUTHORIZED, {"detail": str(e)})

        if path != "/quiz/answer":
            return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

        try:
            req = AnswerRequest(**json.loads(payload.decode("utf-8")))
            result = service.answer(user["id"], req.question_id, req.selected_index)
            return _json_response(self, HTTPStatus.OK, AnswerResult(**result).model_dump())
        except InvalidAnswerIndexError as e:
            return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": str(e)})
        except QuestionNotFoundError as e:
            return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": str(e)})
        except Exception as e:  # noqa: BLE001
            return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": f"Invalid request: {e}"})


def create_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), QuizHTTPRequestHandler)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = create_server(host=host, port=port)
    print(f"Quiz API server started: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
