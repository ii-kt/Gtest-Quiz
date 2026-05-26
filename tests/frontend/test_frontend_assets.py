import json
from pathlib import Path


def test_frontend_page_exists():
    html = Path("frontend/src/index.html")
    assert html.exists()
    text = html.read_text(encoding="utf-8")
    assert "G検定 Quiz Practice" in text
    assert "./offline-app.js" in text
    assert "./manifest.webmanifest" in text
    assert "./pwa-icon-180.png" in text
    assert "apple-mobile-web-app-capable" in text
    assert "完全オフライン" in text
    assert "Performance" in text
    assert "Learning Mode" in text
    assert "@container" in text
    assert "@layer" in text
    assert "backdrop-filter" in text
    assert "startBtn" in text
    assert "nextBtn" in text
    assert "apiState" in text
    assert "dueNow" in text
    assert "trackedItems" in text
    assert "placeholder" not in text
    assert "ユーザー名" not in text
    assert "パスワード" not in text
    assert "authForm" not in text
    assert 'id="sessionState"' in text
    assert 'hidden>端末保存</span>' in text


def test_frontend_is_static_offline_first():
    html = Path("frontend/src/index.html").read_text(encoding="utf-8")
    script = Path("frontend/src/offline-app.js").read_text(encoding="utf-8")
    assert "http://localhost" not in html
    assert "http://localhost" not in script
    assert "/api/v1" not in html
    assert "/api/v1" not in script
    assert "/auth/login" not in html
    assert "/auth/register" not in html
    assert "STATIC_BANK_URL" in script
    assert "./question-bank.json" in script
    assert "localStorage" in script
    assert "selectNextQuestion" in script
    assert "updateSchedule" in script
    assert "exportAccount" in script
    assert "importAccount" in script
    assert "applyBankVersionMigration" in script
    assert "bankResetNoticeSeen" in script
    assert "learnerId" not in script
    assert "ensureLearner" not in script


def test_static_question_bank_asset_matches_source_bank():
    bank = json.loads(Path("frontend/src/question-bank.json").read_text(encoding="utf-8"))
    source_count = len(Path("bank/question_bank.jsonl").read_text(encoding="utf-8").splitlines())
    assert bank["schema_version"] == "gtest_quiz_static_bank_v1"
    assert bank["meta"]["question_count"] == source_count
    assert len(bank["questions"]) == source_count
    assert bank["meta"]["bank_version"] == "gemini35_v1"
    assert bank["meta"]["content_hash"]
    assert "generated_at" not in bank["meta"]
    assert "git_commit" not in bank["meta"]
    if bank["questions"]:
        first = bank["questions"][0]
        assert {"id", "question", "choices", "correct_index", "explanation", "chapter_id", "bank_version"} <= set(first)
        assert len(first["choices"]) == 4


def test_frontend_pwa_assets_exist():
    manifest = Path("frontend/src/manifest.webmanifest")
    worker = Path("frontend/src/service-worker.js")
    icon = Path("frontend/src/pwa-icon.svg")
    assert manifest.exists()
    assert worker.exists()
    assert icon.exists()
    assert Path("frontend/src/pwa-icon-180.png").exists()
    assert Path("frontend/src/pwa-icon-192.png").exists()
    assert Path("frontend/src/pwa-icon-512.png").exists()

    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_data["display"] == "standalone"
    assert manifest_data["start_url"] == "./index.html"
    assert any(icon["src"] == "./pwa-icon-512.png" for icon in manifest_data["icons"])

    worker_text = worker.read_text(encoding="utf-8")
    assert "CACHE_NAME" in worker_text
    assert "gtest-quiz-static-gemini35_v1-" in worker_text
    assert "./offline-app.js" in worker_text
    shell_block = worker_text.split("const SHELL = [", 1)[1].split("];", 1)[0]
    assert "./question-bank.json" not in shell_block
    assert "QUESTION_BANK_URL" in worker_text
    assert "url.pathname.endsWith('/question-bank.json')" in worker_text
    assert "networkFirst(request)" in worker_text
    assert "cacheFirst" in worker_text
