from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import urlparse

from pydantic import ValidationError

from .content import chapter_catalog, offline_question_pack, question_bank_summary
from .deployment import configured_host, configured_port, current_profile_name
from .observability import monotonic_ms, new_request_id, route_family
from .schemas import (
    AnswerRequest,
    AnswerResult,
    ImportBundleRequest,
    LogoutResponse,
    PolicyPreferenceRequest,
    PolicyPreferenceResponse,
    QuestionDTO,
    SessionResponse,
    StartSessionRequest,
)
from .services import (
    InvalidAnswerIndexError,
    QuestionNotFoundError,
    QuizService,
    UnauthorizedError,
)


API_PREFIX = "/api/v1"


def _route_path(raw_path: str) -> str:
    path = urlparse(raw_path).path
    if path == API_PREFIX:
        return "/"
    if path.startswith(f"{API_PREFIX}/"):
        return path[len(API_PREFIX):]
    return path

service = QuizService()


def _extract_token(handler: BaseHTTPRequestHandler) -> str:
    auth = handler.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.replace("Bearer ", "", 1).strip()
    raise UnauthorizedError("missing bearer token")


def _begin_request(handler: BaseHTTPRequestHandler, service: QuizService, method: str) -> None:
    handler._request_id = handler.headers.get("X-Request-ID") or new_request_id()  # type: ignore[attr-defined]
    handler._request_started_ms = monotonic_ms()  # type: ignore[attr-defined]
    handler._request_method = method  # type: ignore[attr-defined]
    handler._service = service  # type: ignore[attr-defined]


def _json_response(handler: BaseHTTPRequestHandler, status: int, body: Any) -> None:
    raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    request_id = getattr(handler, "_request_id", new_request_id())
    handler.send_header("X-Request-ID", request_id)
    handler.end_headers()
    handler.wfile.write(raw)
    service = getattr(handler, "_service", None)
    started = getattr(handler, "_request_started_ms", None)
    method = getattr(handler, "_request_method", "")
    if service is not None and started is not None:
        service.record_request(
            request_id=request_id,
            method=method,
            path=urlparse(handler.path).path,
            route_family=route_family(urlparse(handler.path).path),
            status_code=int(status),
            latency_ms=monotonic_ms() - float(started),
        )


def _parse_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    payload = handler.rfile.read(length) if length > 0 else b"{}"
    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON: {e.msg}") from e
    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object")
    return data


def create_handler(service: QuizService) -> type[BaseHTTPRequestHandler]:
    class QuizHTTPRequestHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Request-ID")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            _begin_request(self, service, "GET")
            path = _route_path(self.path)
            if path == "/health":
                return _json_response(
                    self,
                    HTTPStatus.OK,
                    {"status": "ok", "api_version": "v1", "deployment_profile": current_profile_name()},
                )

            if path == "/content/chapters":
                return _json_response(self, HTTPStatus.OK, chapter_catalog())

            if path == "/content/questions/summary":
                return _json_response(self, HTTPStatus.OK, question_bank_summary())

            if path == "/content/offline-pack":
                return _json_response(self, HTTPStatus.OK, offline_question_pack())

            try:
                token = _extract_token(self)
                user = service.user_from_token(token)
            except UnauthorizedError as e:
                return _json_response(self, HTTPStatus.UNAUTHORIZED, {"detail": str(e)})

            if path == "/operations/metrics":
                return _json_response(self, HTTPStatus.OK, service.operations_metrics(user["id"]))

            if path == "/quiz/next":
                selection = service.next_question(user["id"])
                if selection is None:
                    return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": "No question available"})
                q = selection.question
                payload = {
                    "id": q.id,
                    "domain": q.domain,
                    "chapter_group": q.chapter_group,
                    "chapter_id": q.chapter_id,
                    "difficulty": q.difficulty,
                    "question": q.question,
                    "choices": q.choices,
                    "learning": selection.learning,
                }
                return _json_response(self, HTTPStatus.OK, QuestionDTO(**payload).model_dump())

            if path == "/quiz/stats":
                return _json_response(self, HTTPStatus.OK, service.stats(user["id"]))

            if path == "/analytics/summary":
                return _json_response(self, HTTPStatus.OK, service.stats(user["id"])["user"])

            if path == "/learning/plan":
                return _json_response(self, HTTPStatus.OK, service.learning_plan(user["id"]))

            if path == "/learning/policy":
                return _json_response(self, HTTPStatus.OK, PolicyPreferenceResponse(**service.get_policy(user["id"])).model_dump())

            if path == "/auth/me":
                return _json_response(self, HTTPStatus.OK, service.account_profile(user["id"]))

            if path == "/account/export":
                return _json_response(self, HTTPStatus.OK, service.export_account(user["id"]))

            if path == "/account/audit":
                return _json_response(self, HTTPStatus.OK, service.audit_log(user["id"]))

            return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

        def do_POST(self) -> None:  # noqa: N802
            _begin_request(self, service, "POST")
            path = _route_path(self.path)

            if path == "/auth/start":
                try:
                    data = StartSessionRequest(**_parse_json_body(self))
                    created = service.start_session(data.display_name)
                    return _json_response(self, HTTPStatus.OK, SessionResponse(**created).model_dump())
                except (ValueError, ValidationError) as e:
                    return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": f"Invalid request: {e}"})

            if path == "/auth/refresh":
                try:
                    token = _extract_token(self)
                    user = service.user_from_token(token)
                    return _json_response(self, HTTPStatus.OK, SessionResponse(**service.refresh_session(user["id"])).model_dump())
                except UnauthorizedError as e:
                    return _json_response(self, HTTPStatus.UNAUTHORIZED, {"detail": str(e)})

            if path == "/auth/logout":
                try:
                    token = _extract_token(self)
                    return _json_response(self, HTTPStatus.OK, LogoutResponse(**service.logout(token)).model_dump())
                except UnauthorizedError as e:
                    return _json_response(self, HTTPStatus.UNAUTHORIZED, {"detail": str(e)})

            try:
                token = _extract_token(self)
                user = service.user_from_token(token)
            except UnauthorizedError as e:
                return _json_response(self, HTTPStatus.UNAUTHORIZED, {"detail": str(e)})

            if path == "/account/import":
                try:
                    req = ImportBundleRequest(**_parse_json_body(self))
                    return _json_response(self, HTTPStatus.OK, service.import_account(user["id"], req.bundle))
                except (ValueError, ValidationError) as e:
                    return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": f"Invalid request: {e}"})

            if path == "/learning/policy":
                try:
                    req = PolicyPreferenceRequest(**_parse_json_body(self))
                    return _json_response(self, HTTPStatus.OK, PolicyPreferenceResponse(**service.set_policy(user["id"], req.policy_variant)).model_dump())
                except (ValueError, ValidationError) as e:
                    return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": f"Invalid request: {e}"})

            if path != "/quiz/answer":
                return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

            try:
                req = AnswerRequest(**_parse_json_body(self))
                result = service.answer(user["id"], req.question_id, req.selected_index, req.elapsed_ms)
                return _json_response(self, HTTPStatus.OK, AnswerResult(**result).model_dump())
            except InvalidAnswerIndexError as e:
                return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": str(e)})
            except QuestionNotFoundError as e:
                return _json_response(self, HTTPStatus.NOT_FOUND, {"detail": str(e)})
            except (ValueError, ValidationError) as e:
                return _json_response(self, HTTPStatus.BAD_REQUEST, {"detail": f"Invalid request: {e}"})

    return QuizHTTPRequestHandler


def create_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    service: QuizService | None = None,
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), create_handler(service or QuizService()))


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    if host == "127.0.0.1":
        host = configured_host(host)
    if port == 8000:
        port = configured_port(port)
    server = create_server(host=host, port=port)
    print(f"Quiz API server started: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
