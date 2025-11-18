"""
tools/auto_refill.py
======================

GitHub Actions から毎日実行され、問題バンク (bank/question_bank.jsonl)
に Gemini で生成した新しい問題を追加するスクリプト。

特徴:
- GEMINI_API_KEY がなければ何もせず正常終了（ワークフローを落とさない）
- MetaManager / meta.json を用いて、出題が少ない中項目から優先的に追加
- 1 行 1 問の JSONL 形式で追記
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

from gtest_quiz.meta import MetaManager
from gtest_quiz.question_bank import get_all_questions
from gtest_quiz.models import Question

# toml は config.toml が無い場合も考慮して optional
try:
    import toml  # type: ignore[import]
    HAS_TOML = True
except Exception:
    toml = None  # type: ignore[assignment]
    HAS_TOML = False

# Gemini SDK も optional
try:
    import google.generativeai as genai  # type: ignore[import]
    HAS_GEMINI = True
except Exception:
    genai = None  # type: ignore[assignment]
    HAS_GEMINI = False


# 1 回の実行で何問追加するか
N_NEW_QUESTIONS_PER_RUN = 3


# ----------------------------------------------------------------------
# 設定読み込み
# ----------------------------------------------------------------------
def load_app_config() -> Dict[str, Any]:
    path = "config.toml"
    if not HAS_TOML or not os.path.exists(path):
        return {}
    try:
        return toml.load(path)  # type: ignore[arg-type]
    except Exception:
        return {}


def get_paths(config: Dict[str, Any]) -> Tuple[str, str]:
    paths = config.get("paths", {}) if isinstance(config.get("paths"), dict) else {}
    meta_path = paths.get("meta", "bank/meta.json")
    bank_path = paths.get("question_bank", "bank/question_bank.jsonl")
    return meta_path, bank_path


# ----------------------------------------------------------------------
# Gemini 初期化 & モデル選択
# ----------------------------------------------------------------------
def init_gemini() -> bool:
    if not HAS_GEMINI:
        print("[auto_refill] google-generativeai がインストールされていないためスキップします。")
        return False

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[auto_refill] GEMINI_API_KEY が設定されていないためスキップします。")
        return False

    try:
        genai.configure(api_key=api_key)  # type: ignore[call-arg]
    except Exception as e:
        print(f"[auto_refill] Gemini の初期化に失敗しました: {e}")
        return False

    return True


def list_gemini_models() -> List[str]:
    if not HAS_GEMINI:
        return []
    try:
        models = genai.list_models()  # type: ignore[call-arg]
    except Exception as e:
        print(f"[auto_refill] モデル一覧の取得に失敗しました: {e}")
        return []

    names: List[str] = []
    for m in models:
        methods = getattr(m, "supported_generation_methods", [])
        if "generateContent" in methods:
            names.append(m.name)
    return sorted(names, reverse=True)


def choose_model(config: Dict[str, Any]) -> Optional[str]:
    if not HAS_GEMINI:
        return None

    available = list_gemini_models()
    if not available:
        return None

    gem_cfg = config.get("gemini")
    if isinstance(gem_cfg, dict):
        preferred = gem_cfg.get("preferred_model")
        if isinstance(preferred, str) and preferred and preferred in available:
            return preferred

    # fallback: 一番新しそうなもの
    return available[0]


# ----------------------------------------------------------------------
#  シラバス情報の取り扱い
# ----------------------------------------------------------------------
def collect_subchapters(meta: MetaManager) -> List[Tuple[str, str]]:
    """
    meta.json の chapters から (chapter_group_label, subchapter_label) のリストを作る。

    戻り値例:
        [("人工知能とは", "1. 人工知能の定義"),
         ("人工知能とは", "2. 人工知能分野で議論される問題"),
         ...]
    """
    result: List[Tuple[str, str]] = []
    chapters = meta.meta.get("chapters", {})
    if not isinstance(chapters, dict):
        return result

    for _group_key, group_val in chapters.items():
        if not isinstance(group_val, dict):
            continue
        group_label = group_val.get("label")
        sub = group_val.get("subchapters", {})
        if not isinstance(group_label, str) or not isinstance(sub, dict):
            continue
        for _sub_key, sub_val in sub.items():
            if not isinstance(sub_val, dict):
                continue
            sub_label = sub_val.get("label")
            if isinstance(sub_label, str):
                result.append((group_label, sub_label))
    return result


def score_subchapters_by_usage(meta: MetaManager) -> List[Tuple[str, str]]:
    """
    「これまでの出題回数が少ない中項目ほど優先される」ように
    (group_label, sub_label) をスコア付きで並べる。
    """
    pairs = collect_subchapters(meta)
    stats = meta.meta.get("chapter_stats", {})
    if not isinstance(stats, dict):
        stats = {}

    scored: List[Tuple[str, str, int]] = []
    for group_label, sub_label in pairs:
        stat = stats.get(sub_label, {})
        total = 0
        if isinstance(stat, dict):
            total = int(stat.get("total_questions", 0))
        scored.append((group_label, sub_label, total))

    # 出題回数が少ない順にソート
    scored.sort(key=lambda x: x[2])
    return [(g, s) for g, s, _ in scored]


# ----------------------------------------------------------------------
#  Gemini 用プロンプト
# ----------------------------------------------------------------------
def build_prompt(chapter_group: str, chapter_label: str) -> str:
    return f"""
あなたは日本語で G検定(JDLA Deep Learning for GENERAL) の高品質な四択問題を作る専門家です。

以下の制約を厳密に守って、指定されたシラバス項目に対応する四択問題を 1 問だけ生成してください。

# シラバス情報
- 分野: {chapter_group}
- 中項目: {chapter_label}

# 出力条件
- G検定本試験レベルの知識を問う。
- 純粋な知識問題・概念理解問題・応用イメージ問題をバランス良く含める。
- 選択肢は必ず 4 つ。紛らわしいが、1つだけ明確に正しい選択肢を含める。
- 難易度は basic / standard / advanced のいずれか。

# 出力フォーマット (JSON 1オブジェクトのみ)
以下のキーを含む JSON オブジェクトとして出力してください:

{{
  "question": "問題文",
  "choices": ["選択肢1", "選択肢2", "選択肢3", "選択肢4"],
  "correct_index": 0,
  "explanation": "正解の理由と他の選択肢が誤りである理由を丁寧に解説する。",
  "difficulty": "basic|standard|advanced"
}}

絶対に JSON 以外の文字列は出力しないでください。
"""


def generate_one_question(
    model_name: str,
    meta: MetaManager,
    chapter_group: str,
    chapter_label: str,
) -> Optional[Question]:
    """指定された中項目について Gemini で 1 問生成し、Question として返す。"""

    if not HAS_GEMINI:
        return None

    prompt = build_prompt(chapter_group, chapter_label)
    quota = meta.get_quota_manager()

    approx_prompt_tokens = len(prompt) // 2

    try:
        model = genai.GenerativeModel(model_name)  # type: ignore[call-arg]
        response = model.generate_content(prompt)  # type: ignore[call-arg]
        text = response.text.strip() if hasattr(response, "text") else ""
        data = json.loads(text)
    except Exception as e:
        msg = str(e)
        print(f"[auto_refill] 問題生成に失敗しました: {msg}")
        if "429" in msg or "Resource exhausted" in msg:
            quota.register_429(message=msg)
        else:
            quota.register_error(message=msg)
        return None

    approx_output_tokens = len(text) // 2
    quota.add_usage(approx_prompt_tokens + approx_output_tokens)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    jq: Dict[str, Any] = {
        "id": f"Q_AUTO_{created_at}",
        "source": "auto_refill",
        "created_at": created_at,
        "domain": "技術分野",
        "chapter_group": chapter_group,
        "chapter_id": chapter_label,
        "difficulty": data.get("difficulty", "standard"),
        "question": data.get("question", "").strip(),
        "choices": data.get("choices", []),
        "correct_index": int(data.get("correct_index", 0)),
        "explanation": data.get("explanation", "").strip(),
        "syllabus": "G2024_v1.3",
    }

    # 最低限のバリデーション
    if (
        not jq["question"]
        or not isinstance(jq["choices"], list)
        or len(jq["choices"]) != 4
    ):
        print("[auto_refill] 生成結果が不正なため破棄しました。")
        return None

    return Question.from_dict(jq)


# ----------------------------------------------------------------------
#  JSONL 追記
# ----------------------------------------------------------------------
def append_questions_to_bank(bank_path: str, questions: List[Question]) -> None:
    if not questions:
        return
    os.makedirs(os.path.dirname(bank_path), exist_ok=True)
    with open(bank_path, "a", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q.to_dict(), ensure_ascii=False))
            f.write("\n")


# ----------------------------------------------------------------------
#  メイン処理
# ----------------------------------------------------------------------
def main() -> None:
    config = load_app_config()
    meta_path, bank_path = get_paths(config)

    meta = MetaManager(meta_path)
    meta.load()

    if not init_gemini():
        # オフライン・キー未設定などの場合、エラーにはせず静かに終了
        print("[auto_refill] Gemini が利用できないため、今回は問題追加を行いません。")
        return

    model_name = choose_model(config)
    if not model_name:
        print("[auto_refill] 利用可能な Gemini モデルが見つからないため終了します。")
        return

    # 出題が少ない順に中項目を並べる
    ranked_subchapters = score_subchapters_by_usage(meta)
    if not ranked_subchapters:
        print("[auto_refill] meta.json に章情報が無いため終了します。")
        return

    # すでにある問題を参照して、偏りをさらに軽減してもよいが、
    # ここでは simple に上位 N 件だけを対象とする。
    targets = ranked_subchapters[: N_NEW_QUESTIONS_PER_RUN * 2]

    generated: List[Question] = []

    for (group_label, sub_label) in targets:
        if len(generated) >= N_NEW_QUESTIONS_PER_RUN:
            break
        q = generate_one_question(model_name, meta, group_label, sub_label)
        if q is None:
            continue
        generated.append(q)
        # 利用統計に反映
        meta.record_usage(chapter_id=sub_label, source="online")

    if not generated:
        print("[auto_refill] 有効な問題を生成できませんでした。")
        meta.save()
        return

    append_questions_to_bank(bank_path, generated)
    meta.save()

    print(f"[auto_refill] 新規問題を {len(generated)} 問追加しました。")


if __name__ == "__main__":
    main()
