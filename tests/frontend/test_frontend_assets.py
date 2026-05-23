<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
import json
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
from pathlib import Path


def test_frontend_page_exists():
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    html = Path("frontend/src/index.html")
    assert html.exists()
    text = html.read_text(encoding="utf-8")
    assert "G検定 Quiz Practice" in text
    assert "./offline-app.js" in text
    assert "./manifest.webmanifest" in text
    assert "./pwa-icon-180.png" in text
    assert "apple-mobile-web-app-capable" in text
    assert "完全オフライン" in text
    assert "startBtn" in text
    assert "nextBtn" in text
    assert "apiState" in text
    assert "dueNow" in text
    assert "trackedItems" in text
    assert "placeholder" not in text
    assert "ユーザー名" not in text
    assert "パスワード" not in text


def test_frontend_is_static_offline_first():
    html = Path("frontend/src/index.html").read_text(encoding="utf-8")
    script = Path("frontend/src/offline-app.js").read_text(encoding="utf-8")
    assert "http://localhost" not in html
    assert "http://localhost" not in script
    assert "/api/v1" not in html
    assert "/api/v1" not in script
    assert "STATIC_BANK_URL" in script
    assert "./question-bank.json" in script
    assert "localStorage" in script
    assert "selectNextQuestion" in script
    assert "updateSchedule" in script
    assert "exportAccount" in script
    assert "importAccount" in script


def test_static_question_bank_asset_matches_source_bank():
    bank = json.loads(Path("frontend/src/question-bank.json").read_text(encoding="utf-8"))
    source_count = len(Path("bank/question_bank.jsonl").read_text(encoding="utf-8").splitlines())
    assert bank["schema_version"] == "gtest_quiz_static_bank_v1"
    assert bank["meta"]["question_count"] == source_count
    assert len(bank["questions"]) == source_count
    first = bank["questions"][0]
    assert {"id", "question", "choices", "correct_index", "explanation", "chapter_id"} <= set(first)
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
    assert "gtest-quiz-static-v1" in worker_text
    assert "./offline-app.js" in worker_text
    assert "./question-bank.json" in worker_text
    assert "cacheFirst" in worker_text
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
    html = Path('frontend/src/index.html')
    assert html.exists()
    text = html.read_text(encoding='utf-8')
    assert 'G検定クイズ v2' in text
    assert '/quiz/next' in text
    assert '/quiz/answer' in text
    assert '/quiz/stats' in text
    assert '/auth/register' in text
    assert '/auth/login' in text
    assert 'authForm' in text
    assert 'nextBtn' in text


def test_frontend_has_error_handling_text():
    text = Path('frontend/src/index.html').read_text(encoding='utf-8')
    assert '問題を読み込めませんでした。' in text
    assert '回答処理に失敗しました。' in text
    assert '先に認証してください。' in text
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
