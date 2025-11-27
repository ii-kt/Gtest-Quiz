"""
app.py
======================

G検定対策クイズアプリ（Streamlit）エントリーポイント。

特徴:
- ホーム画面 + メニュー構成（C案）
- クイズ / 間違い復習 / 学習統計 / 設定 / 使い方
- オンライン( Gemini ) / オフライン問題の両対応
- 偏りを抑えた章選択（MetaManager）
- 推定クォータメーター表示（QuotaManager + ui.py）

前提:
- bank/question_bank.jsonl にサンプル問題が格納されている
- bank/meta.json が存在する（なければ自動で初期化される）
- 環境変数 GEMINI_API_KEY が設定されていればオンライン出題が有効
"""

from __future__ import annotations

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from gtest_quiz.meta import MetaManager
from gtest_quiz.models import SessionState, Question
from gtest_quiz.question_bank import (
    get_all_questions,
    pick_random_question,
    get_question_by_id,
)
from gtest_quiz.ui import render_quiz_page

# ----------------------------------------------------------------------
#  Streamlit の rerun 互換ラッパー
# ----------------------------------------------------------------------
def rerun() -> None:
    """
    Streamlit 1.x 以降では st.rerun、それ以前では st.experimental_rerun。
    両方に対応するための薄いラッパー。
    """
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # 古いバージョン向け
        st.experimental_rerun()  # type: ignore[attr-defined]


# google-generativeai は存在しない環境でも動くように、遅延インポート + フォールバック
try:
    import google.generativeai as genai  # type: ignore[import]
    HAS_GEMINI = True
except Exception:
    genai = None  # type: ignore[assignment]
    HAS_GEMINI = False


# ----------------------------------------------------------------------
#  アプリ共通設定読み込み
# ----------------------------------------------------------------------
def load_app_config() -> Dict[str, Any]:
    """
    config.toml があれば読み込み、アプリ設定を dict で返す。
    なければ空 dict。
    """
    if "app_config" in st.session_state:
        return st.session_state["app_config"]

    cfg: Dict[str, Any] = {}
    config_path = os.path.join(os.path.dirname(__file__), "config.toml")
    if os.path.exists(config_path):
        try:
            import tomllib  # Python 3.11+

            with open(config_path, "rb") as f:
                cfg = tomllib.load(f)
        except Exception:
            # tomllib がない環境 / 読み込み失敗時は設定なしで続行
            cfg = {}

    st.session_state["app_config"] = cfg
    return st.session_state["app_config"]


# ----------------------------------------------------------------------
#  MetaManager のシングルトン取得
# ----------------------------------------------------------------------
def get_meta_manager() -> MetaManager:
    """meta.json を管理する MetaManager のインスタンスを返す（シングルトン）。"""
    if "meta_manager" not in st.session_state:
        cfg = load_app_config()
        bank_dir = cfg.get("paths", {}).get("bank_dir", "bank")
        meta_path = os.path.join(bank_dir, "meta.json")
        st.session_state["meta_manager"] = MetaManager(meta_path)
    return st.session_state["meta_manager"]  # type: ignore[return-value]


# ----------------------------------------------------------------------
#  SessionState のシングルトン取得
# ----------------------------------------------------------------------
def get_session_state() -> SessionState:
    """Quiz用の SessionState をセッションに保持して返す。"""
    if "quiz_session" not in st.session_state:
        cfg = load_app_config()
        default_mode = (
            cfg.get("app", {}).get("default_mode", "auto")
            if isinstance(cfg.get("app"), dict)
            else "auto"
        )
        st.session_state["quiz_session"] = SessionState(mode=default_mode)
    return st.session_state["quiz_session"]  # type: ignore[return-value]


def set_page(page: str) -> None:
    """現在のページ種別を session_state に保持する。"""
    st.session_state["page"] = page


def get_page() -> str:
    """現在のページ種別を取得する。"""
    return st.session_state.get("page", "home")


# ----------------------------------------------------------------------
#  問題読み込み関連
# ----------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_all_questions_cached() -> List[Question]:
    """question_bank.jsonl を読み込んで Question のリストをキャッシュして返す。"""
    cfg = load_app_config()
    bank_dir = cfg.get("paths", {}).get("bank_dir", "bank")
    jsonl_path = os.path.join(bank_dir, "question_bank.jsonl")
    return get_all_questions(jsonl_path)


def load_new_question(session: SessionState, meta: MetaManager) -> None:
    """
    新しい問題を選んで SessionState にセットする。
    章選択のロジックは MetaManager に委譲する。
    """
    questions = load_all_questions_cached()

    # MetaManager から「どの章から出すか」を決めてもらう（単純なラウンドロビンなど）
    # 現状はランダム出題だが、将来的に偏りを抑えたロジックに差し替え予定。
    chapter_id = meta.pick_next_chapter(questions)

    # その章から 1 問ランダムに選ぶ
    q = pick_random_question(questions, chapter_id=chapter_id)
    if q is None:
        # フォールバックとして、全体からランダムに 1 問選ぶ
        q = pick_random_question(questions)

    if q is None:
        # それでも見つからない場合は、アプリとしては致命的だがエラー表示で止める
        st.error("問題が見つかりませんでした。question_bank.jsonl を確認してください。")
        return

    # SessionState を更新
    session.start_new_question(question=q, source="offline", model_name=None)


# ----------------------------------------------------------------------
#  Gemini 関連（オンライン出題）
# ----------------------------------------------------------------------
def init_gemini_if_needed() -> None:
    """GEMINI_API_KEY があれば genai.configure を行う。"""
    if not HAS_GEMINI:
        return

    if "gemini_inited" in st.session_state:
        return

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return

    try:
        genai.configure(api_key=api_key)  # type: ignore[call-arg]
        st.session_state["gemini_inited"] = True
    except Exception as e:  # noqa: BLE001
        st.warning(f"Gemini の初期化に失敗しました: {e}")


def generate_question_online() -> Optional[Question]:
    """
    Gemini を使ってオンラインで問題文を生成するサンプル。
    現状は PoC 的な位置づけであり、本番用ではない。
    """
    if not HAS_GEMINI:
        st.error("オンライン出題は、この環境ではサポートされていません。")
        return None

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("環境変数 GEMINI_API_KEY が設定されていません。")
        return None

    init_gemini_if_needed()

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")  # type: ignore[attr-defined]
        prompt = (
            "あなたは JDLA G検定 の試験対策問題を作成する AI です。"
            "シラバス G2024_v1.3 に沿った単一選択式の問題を 1問 日本語で作成してください。"
            "返却形式は JSON で、キーは "
            '{"question", "choices", "correct_index", "chapter_group", "chapter_id", "difficulty"}'
            " としてください。"
        )
        resp = model.generate_content(prompt)  # type: ignore[attr-defined]
        text = resp.text  # type: ignore[assignment]

        data = json.loads(text)
        now = datetime.now(timezone.utc).isoformat()
        q = Question(
            id=f"online-{now}",
            source="online",
            created_at=now,
            domain="JDLA_GTEST",
            chapter_group=data.get("chapter_group", "オンライン出題"),
            chapter_id=data.get("chapter_id", "Online"),
            difficulty=data.get("difficulty", "N/A"),
            question=data["question"],
            choices=data["choices"],
            correct_index=int(data["correct_index"]),
            explanation=data.get("explanation", "オンライン生成問題です。"),
            meta={"syllabus": "G2024_v1.3"},
        )
        return q
    except Exception as e:  # noqa: BLE001
        st.error(f"オンライン問題生成に失敗しました: {e}")
        return None


def load_new_question_online(session: SessionState, meta: MetaManager) -> None:
    """
    オンライン（Gemini）で問題を生成して SessionState にセットする。
    """
    q = generate_question_online()
    if q is None:
        return

    session.start_new_question(question=q, source="online", model_name="gemini-1.5-flash")
    # オンライン出題も統計に含めたい場合はここで MetaManager へ記録する


# ----------------------------------------------------------------------
#  ページ描画: ホーム
# ----------------------------------------------------------------------
def render_home_page() -> None:
    st.title("G検定クイズ")

    st.markdown(
        """
        このアプリは、JDLA G検定 の試験対策用クイズアプリです。

        - 公式シラバス (G2024_v1.3) に対応したオフライン問題
        - オプションで Gemini を使ったオンライン出題
        - 間違えた問題だけを復習するモード
        - 章ごとの学習状況を可視化する統計ページ

        下のボタンから、学習を始めてください。
        """
    )

    st.write("")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 クイズを始める", use_container_width=True):
            set_page("quiz")
            rerun()
    with col2:
        if st.button("📝 間違えた問題を復習", use_container_width=True):
            set_page("review")
            rerun()

    st.write("")
    col3, col4 = st.columns(2)
    with col3:
        if st.button("📊 学習統計を見る", use_container_width=True):
            set_page("stats")
            rerun()
    with col4:
        if st.button("⚙️ 設定", use_container_width=True):
            set_page("settings")
            rerun()

    st.write("")
    if st.button("❓ 使い方を見る", use_container_width=True):
        set_page("help")
        rerun()


# ----------------------------------------------------------------------
#  ページ描画: クイズ本編
# ----------------------------------------------------------------------
def render_quiz_page_main() -> None:
    session = get_session_state()
    meta = get_meta_manager()

    st.caption("クイズモード: オフライン問題 (sample)")

    # モード切替（将来的な拡張用。現状はオフライン固定）
    mode = st.radio(
        "出題モード",
        options=["auto", "offline", "online"],
        format_func=lambda m: {
            "auto": "AUTO（状況に応じて自動）",
            "offline": "オフライン問題のみ",
            "online": "Gemini オンライン出題",
        }.get(m, m),
        horizontal=True,
        index=["auto", "offline", "online"].index(session.mode)
        if session.mode in ["auto", "offline", "online"]
        else 0,
    )
    session.mode = mode

    st.write("")

    # まだ問題がなければ 1 問ロード
    if not isinstance(session.current_question, Question):
        load_new_question(session, meta)

    quota_status = meta.get_quota_status()
    progress_ratio = None  # 現状は未実装

    mode_label = session.mode.upper()

    ui_result = render_quiz_page(
        session=session,
        progress_ratio=progress_ratio,
        quota_status=quota_status,
        mode_label=mode_label,
    )

    if ui_result["selected_choice"] is not None:
        idx = ui_result["selected_choice"]
        correct = session.answer(idx)
        if session.current_question is not None:
            meta.record_usage(
                chapter_id=session.current_question.chapter_id,
                source=session.source,
            )
            meta.save()
        if correct:
            st.success("正解です！")
        else:
            st.warning("不正解です。解説を確認しましょう。")

        # 回答直後に、解説と結果が見える位置まで自動スクロールする
        st.markdown(
            """
            <script>
            const target = document.getElementById('gq-answer-bottom');
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
            }
            </script>
            """,
            unsafe_allow_html=True,
        )

    if ui_result["clicked_next"]:
        load_new_question(session, meta)
        rerun()
    elif ui_result["clicked_prev"]:
        if session.history:
            last = session.history[-1]
            prev_q = get_question_by_id(last.question_id)
            if prev_q is not None:
                session.start_new_question(
                    question=prev_q,
                    source=last.source,
                    model_name=session.model_name,
                )
                rerun()
    elif ui_result["clicked_change_chapter"]:
        load_new_question(session, meta)
        rerun()

    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  ページ: 間違えた問題だけで復習
# ----------------------------------------------------------------------
def render_review_page() -> None:
    session = get_session_state()
    meta = get_meta_manager()  # noqa: F841 （今後拡張用に保持）

    st.title("間違えた問題を復習")

    if not session.history:
        st.info("まだ解答履歴がありません。まずはクイズを解いてみましょう。")
        if st.button("🎯 クイズを始める", use_container_width=True):
            set_page("quiz")
            rerun()
        return

    wrong_history = [h for h in session.history if not h.correct]

    if not wrong_history:
        st.success("間違えた問題はありません。素晴らしいです！")
        if st.button("🏠 ホームに戻る", use_container_width=True):
            set_page("home")
            rerun()
        return

    st.write(f"これまでに間違えた問題: {len(wrong_history)} 問")

    selected_idx = st.number_input(
        "復習する履歴のインデックス（0 が最初）",
        min_value=0,
        max_value=len(wrong_history) - 1,
        value=0,
        step=1,
    )

    record = wrong_history[selected_idx]
    q = get_question_by_id(record.question_id)

    if q is None:
        st.error("該当する問題データが見つかりませんでした。")
    else:
        st.subheader("復習問題")
        st.markdown(f"**問題 ID:** {q.id}")
        st.markdown(f"**章:** {q.chapter_group} / {q.chapter_id}")
        st.markdown(f"**難易度:** {q.difficulty}")
        st.write("")
        st.markdown(q.question)
        st.write("")
        for i, choice in enumerate(q.choices):
            prefix = "✅" if i == q.correct_index else "❌"
            st.markdown(f"- {prefix} {choice}")
        st.write("")
        st.markdown("**解説:**")
        st.info(q.explanation)

    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  ページ: 学習統計
# ----------------------------------------------------------------------
def render_stats_page() -> None:
    session = get_session_state()
    meta = get_meta_manager()

    st.title("学習統計")

    st.write("※現状は簡易的な統計のみを表示しています。")

    st.subheader("セッション内の解答履歴")
    if not session.history:
        st.info("まだ解答履歴がありません。")
    else:
        total = len(session.history)
        correct = sum(1 for h in session.history if h.correct)
        st.metric("解いた問題数", total)
        st.metric("正解数", correct)
        st.metric("正答率", f"{(correct / total) * 100:.1f} %")
        st.write("")

        st.write("直近の解答履歴:")
        for i, h in enumerate(reversed(session.history[-20:]), 1):
            mark = "⭕" if h.correct else "❌"
            dt = datetime.fromisoformat(h.answered_at)
            st.write(
                f"{i:02d}. {mark} {h.question.chapter_group} / {h.question.chapter_id} "
                f"({dt.strftime('%Y-%m-%d %H:%M:%S')})"
            )

    st.write("")
    st.subheader("Meta 情報 (token 使用量など)")

    quota = meta.get_quota_status()
    st.write(quota)

    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  ページ: 設定
# ----------------------------------------------------------------------
def render_settings_page() -> None:
    session = get_session_state()
    cfg = load_app_config()

    st.title("設定")

    st.subheader("出題モードの初期値")
    default_mode = st.selectbox(
        "アプリ起動時のモード",
        options=["auto", "offline", "online"],
        format_func=lambda m: {
            "auto": "AUTO（状況に応じて自動）",
            "offline": "オフライン問題のみ",
            "online": "オンライン出題（Gemini）",
        }.get(m, m),
        index=["auto", "offline", "online"].index(
            cfg.get("app", {}).get("default_mode", "auto")
            if isinstance(cfg.get("app"), dict)
            else "auto"
        ),
    )

    if st.button("設定を保存", use_container_width=True):
        cfg.setdefault("app", {})["default_mode"] = default_mode
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        try:
            import tomli_w  # type: ignore[import]
        except Exception:
            st.error("tomli_w がインストールされていないため、設定を保存できません。")
        else:
            with open(config_path, "wb") as f:
                tomli_w.dump(cfg, f)  # type: ignore[arg-type]
            st.success("設定を保存しました。")

    st.write("")
    st.subheader("現在のセッション状態（デバッグ用）")
    st.json(session.to_dict())

    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  ページ: 使い方
# ----------------------------------------------------------------------
def render_help_page() -> None:
    st.title("使い方")

    st.markdown(
        """
        ### 基本的な使い方

        1. ホーム画面の「🎯 クイズを始める」を押すと、ランダムに 1 問出題されます。
        2. 選択肢のいずれかを押すと、その場で正解／不正解が判定されます。
        3. 「解説」セクションで、なぜその選択肢が正解なのかを確認できます。
        4. 「次の問題 ▶」ボタンで別の問題に進みます。
        5. 「間違えた問題を復習」では、過去に不正解だった問題だけを復習できます。
        """
    )

    st.markdown(
        """
        ### オンライン出題について

        - オンライン出題を有効にするには、環境変数 `GEMINI_API_KEY` を設定してください。
        - オンライン出題は PoC 段階であり、問題品質は保証されません。
        """
    )

    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  メイン
# ----------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="G検定クイズ",
        page_icon="🤖",
        layout="centered",
    )

    cfg = load_app_config()
    if cfg.get("ui", {}).get("hide_streamlit_style", True):
        hide_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
        """
        st.markdown(hide_style, unsafe_allow_html=True)

    page = get_page()

    if page == "home":
        render_home_page()
    elif page == "quiz":
        render_quiz_page_main()
    elif page == "review":
        render_review_page()
    elif page == "stats":
        render_stats_page()
    elif page == "settings":
        render_settings_page()
    elif page == "help":
        render_help_page()
    else:
        set_page("home")
        render_home_page()


if __name__ == "__main__":
    main()