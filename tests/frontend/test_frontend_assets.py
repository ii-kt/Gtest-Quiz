import json
from pathlib import Path

from gtest_quiz.content_factory import LEGAL_CHAPTER_GROUPS, LEGAL_SOURCE_FIELDS, domain_for_chapter_group
from tools import build_static_pwa_assets


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
    assert 'id="sourcePanel"' in text
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
    assert "renderSourcePanel" in script
    assert "fetch(STATIC_BANK_URL, { cache: 'no-store' })" in script
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


def test_static_question_bank_keeps_legal_sources(tmp_path, monkeypatch):
    group = next(iter(LEGAL_CHAPTER_GROUPS))
    row = {
        "id": "legal-source-test",
        "bank_version": "gemini35_v1",
        "domain": domain_for_chapter_group(group),
        "chapter_group": group,
        "chapter_id": "legal chapter",
        "difficulty": "standard",
        "question": "legal source test",
        "choices": ["a", "b", "c", "d"],
        "correct_index": 0,
        "explanation": "legal source explanation",
        "syllabus": "G2024_v1.3",
        **{field: f"{field}-value" for field in LEGAL_SOURCE_FIELDS},
    }
    bank_path = tmp_path / "question_bank.jsonl"
    meta_path = tmp_path / "meta.json"
    bank_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    meta_path.write_text(json.dumps({"bank_version": "gemini35_v1"}), encoding="utf-8")

    monkeypatch.setattr(build_static_pwa_assets, "BANK_PATH", bank_path)
    monkeypatch.setattr(build_static_pwa_assets, "META_PATH", meta_path)

    [item] = build_static_pwa_assets.load_questions()
    for field in LEGAL_SOURCE_FIELDS:
        assert item[field] == f"{field}-value"


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
    assert "questionBankNetworkFirst(request)" in worker_text
    assert "cache: 'no-store'" in worker_text
    assert "cacheFirst" in worker_text
