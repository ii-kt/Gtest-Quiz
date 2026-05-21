from pathlib import Path


def test_frontend_page_exists():
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
