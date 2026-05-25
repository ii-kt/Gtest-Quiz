"""
config.py
=========

アプリ全体で利用する設定値を一元管理する。
Streamlit、Gemini API、ファイルパス、問題生成モデルなど
すべてこのクラスを通じて取得する。

本ファイルは app.py と現行の問題生成補助CLIの共通設定でもある。
"""

from dataclasses import dataclass
from pathlib import Path
import json

from gtest_quiz.env import get_env, load_dotenv
from gtest_quiz.bank_epoch import DEFAULT_GEMINI_MODEL


# ------------------------------------------------------------
# 基本パス定義
# ------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent.parent
BANK_DIR = ROOT_DIR / "bank"
DATA_DIR = ROOT_DIR / "data"


# ------------------------------------------------------------
# AppConfig
# ------------------------------------------------------------

@dataclass
class AppConfig:
    """
    アプリ設定クラス。

    - APIキーの読み取り
    - QuestionBank / Meta のパス
    - 問題生成モデル
    """

    # ---------- API ----------
    gemini_api_key: str = ""
    gemini_model_list_url: str = (
        "https://generativelanguage.googleapis.com/v1beta/models"
    )

    # ---------- ファイルパス ----------
    question_bank_path: Path = BANK_DIR / "question_bank.jsonl"
    meta_json_path: Path = BANK_DIR / "meta.json"
    syllabus_pdf_path: Path = DATA_DIR / "JDLA_Gtest_Syllabus_2024_v1.3_JP.pdf"

    # ---------- 問題生成モデル設定 ----------
    model_failover_priority: list = None

    # ---------- 自動生成設定 ----------
    auto_refill_seed_prompt: str = (
        "シラバスに基づき、G検定の四択問題を1問生成してください。"
    )

    # ============================================================
    # 初期化処理
    # ============================================================

    def __post_init__(self):
        # APIキーのロード
        self.gemini_api_key = self._load_api_key()

        # 問題生成ではモデルを明示固定する。画像/動画系などの最新モデルを
        # 自動選択すると、品質とAPI消費の両方が不安定になる。
        self.model_failover_priority = [
            DEFAULT_GEMINI_MODEL,
        ]

    # ============================================================
    # 内部関数
    # ============================================================

    def _load_api_key(self) -> str:
        """
        Streamlit Cloud / GitHub Actions / ローカルすべてで
        GEMINI_API_KEY が使えるようにする。
        """

        load_dotenv(ROOT_DIR / ".env")
        key = get_env("GEMINI_API_KEY", "")
        return key  # キーなし → オフラインモードへ

    # ============================================================
    # JSON 読み取りユーティリティ
    # ============================================================

    @staticmethod
    def read_json(path: Path):
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, data: dict):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
