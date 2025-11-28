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
- config.toml に一部設定を書ける（なくても動く）
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
    get_questions_by_chapter,
    pick_random_from_chapter,
    pick_random_question,
    get_question_by_id,
)
from gtest_quiz.ui import render_quiz_page

# toml (config 用)
try:
    import toml  # type: ignore[import]

    HAS_TOML = True
except Exception:  # noqa: BLE001
    toml = None  # type: ignore[assignment]
    HAS_TOML = False


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
except Exception:  # noqa: BLE001
    genai = None  # type: ignore[assignment]
    HAS_GEMINI = False


# ----------------------------------------------------------------------
#  アプリ設定読み込み
# ----------------------------------------------------------------------
def load_app_config() -> Dict[str, Any]:
    """
    ルート config.toml を読み込む。
    読み込みに失敗しても空 dict を返す。
    """
    if "app_config" in st.session_state:
        return st.session_state["app_config"]

    cfg: Dict[str, Any] = {}
    path = "config.toml"

    if HAS_TOML and os.path.exists(path):
        try:
            cfg = toml.load(path)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            cfg = {}

    st.session_state["app_config"] = cfg
    return cfg


# ----------------------------------------------------------------------
#  MetaManager / SessionState のラッパー
# ----------------------------------------------------------------------
def get_meta_manager() -> MetaManager:
    """
    MetaManager インスタンスを取得する。
    最初の呼び出し時に bank/meta.json を読み込み、以降はセッションで使い回す。
    """
    if "meta_manager" not in st.session_state:
        cfg = load_app_config()
        bank_dir = cfg.get("paths", {}).get("bank_dir", "bank") if isinstance(
            cfg.get("paths"), dict
        ) else "bank"
        meta_path = os.path.join(bank_dir, "meta.json")
        st.session_state["meta_manager"] = MetaManager(meta_path)
    return st.session_state["meta_manager"]  # type: ignore[return-value]


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
    st.session_state["page"] = page


def get_page() -> str:
    return st.session_state.get("page", "home")


# ----------------------------------------------------------------------
#  Gemini 関連
# ----------------------------------------------------------------------
def init_gemini_if_needed() -> None:
    """GEMINI_API_KEY があれば設定する（なければ何もしない）。"""
    if not HAS_GEMINI:
        return
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return
    try:
        genai.configure(api_key=api_key)  # type: ignore[call-arg]
    except Exception:  # noqa: BLE001
        # 失敗してもアプリ自体は動かす
        pass


def list_available_models() -> List[str]:
    """
    利用可能な Gemini モデル一覧を返す。
    generateContent に対応しているものだけを対象にし、名前逆ソート。
    """
    if not HAS_GEMINI:
        return []

    try:
        models = genai.list_models()  # type: ignore[call-arg]
    except Exception:  # noqa: BLE001
        return []

    names: List[str] = []
    for m in models:
        methods = getattr(m, "supported_generation_methods", [])
        if "generateContent" in methods:
            name = getattr(m, "name", "")
            if isinstance(name, str) and name:
                names.append(name)

    names = sorted(names, reverse=True)
    return names


def get_preferred_model_name() -> Optional[str]:
    """
    設定画面・config.toml を踏まえて「優先モデル名」を返す。
    実際に使えるかはオンライン出題時に再度確認する。
    """
    # 設定画面で指定されている場合を優先
    preferred = st.session_state.get("preferred_model")
    if isinstance(preferred, str) and preferred:
        return preferred

    # config.toml の [gemini].preferred_model
    cfg = load_app_config()
    gem_cfg = cfg.get("gemini")
    if isinstance(gem_cfg, dict):
        p = gem_cfg.get("preferred_model")
        if isinstance(p, str) and p:
            return p

    # 何も指定がなければ、利用可能モデル一覧の先頭
    candidates = list_available_models()
    return candidates[0] if candidates else None


def choose_model_with_fallback() -> Optional[str]:
    """
    優先モデル名を取得し、それが実際に利用可能かを簡易チェックする。
    ダメなら None を返す。
    """
    if not HAS_GEMINI:
        return None

    name = get_preferred_model_name()
    if not name:
        return None

    available = list_available_models()
    if name not in available:
        return None
    return name


def can_use_online(meta: MetaManager) -> bool:
    """
    オンライン出題を利用してよいかを、クォータ状況も踏まえて判定する。
    """
    if not HAS_GEMINI:
        return False
    if not os.getenv("GEMINI_API_KEY"):
        return False

    quota = meta.get_quota_manager()
    remaining = quota.get_remaining_ratio()
    # まだ上限未推定なら一旦 OK、とする
    if remaining is None:
        return True

    # config.toml の [quota].near_limit_ratio を参照
    cfg = load_app_config()
    near_ratio = 0.9
    qcfg = cfg.get("quota")
    if isinstance(qcfg, dict):
        r = qcfg.get("near_limit_ratio")
        try:
            near_ratio = float(r)
        except Exception:  # noqa: BLE001
            near_ratio = 0.9

    # 残りが 0 に近ければオンラインはやめておく
    return remaining > (1.0 - near_ratio)


def build_online_prompt(chapter_label: str, chapter_group: str) -> str:
    """オンライン出題用プロンプト（auto_refill.py と同系統）。"""
    return f"""
あなたは日本語で G検定(JDLA Deep Learning for GENERAL) の高品質な四択問題を作る専門家です。

以下の制約を厳密に守って、指定されたシラバス項目に対応する四択問題を 1 問だけ生成してください。

# シラバス情報
- 分野: {chapter_group}
- 中項目: {chapter_label}

# 出力条件
- G検定本試験レベルの知識を問う。
- 四択問題 (選択肢は A/B/C/D の 4 つ) とする。
- 問題文は 1～3 行程度に収める。
- 選択肢は紛らわしさのあるものを含め、受験者をある程度迷わせるようにする。
- 正解は必ず 1 つだけにする。
- 解説では、なぜその選択肢が正しいのか、他の選択肢がなぜ誤りなのかを簡潔に説明する。

# 出力フォーマット（JSON）
次の JSON 形式のみを出力してください。日本語テキスト中に余計な説明は書かないでください。

{{
  "question": "問題文（日本語）",
  "choices": ["Aの選択肢", "Bの選択肢", "Cの選択肢", "Dの選択肢"],
  "correct_index": 0,
  "explanation": "なぜその選択肢が正しいのか、他が誤りなのかの解説（日本語）"
}}
"""  # noqa: E501


def generate_online_question(
    meta: MetaManager,
    chapter_label: str,
) -> Optional[Question]:
    """
    指定された章ラベルからオンライン問題を 1問生成する。
    失敗した場合は None を返し、呼び出し側でオフラインへフォールバックする。
    """
    if not can_use_online(meta):
        return None

    model_name = choose_model_with_fallback()
    if not model_name:
        return None

    chapters = meta.meta.get("chapters", {})
    chapter_group = "ディープラーニング"
    for _group_key, group_val in chapters.items():
        subchapters = group_val.get("subchapters", {})
        for _sub_key, sub_val in subchapters.items():
            if sub_val.get("label") == chapter_label:
                chapter_group = group_val.get("label", chapter_group)
                break

    prompt = build_online_prompt(chapter_label=chapter_label, chapter_group=chapter_group)

    try:
        model = genai.GenerativeModel(model_name)  # type: ignore[attr-defined]
        resp = model.generate_content(prompt)  # type: ignore[attr-defined]
        text = resp.text
    except Exception as e:  # noqa: BLE001
        meta.get_quota_manager().record_error(str(e))
        return None

    try:
        data = json.loads(text)
    except Exception:  # noqa: BLE001
        meta.get_quota_manager().record_error("invalid_json")
        return None

    try:
        q = Question(
            id=f"online-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            source="online",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            domain="JDLA_GTEST",
            chapter_group=chapter_group,
            chapter_id=chapter_label,
            difficulty="online",
            question=data["question"],
            choices=list(data["choices"]),
            correct_index=int(data["correct_index"]),
            explanation=data.get("explanation", ""),
            meta={"model": model_name},
        )
    except Exception as e:  # noqa: BLE001
        meta.get_quota_manager().record_error(f"invalid_struct: {e}")
        return None

    # トークン使用量を（概算で）記録
    quota = meta.get_quota_manager()
    quota.add_usage(
        prompt_tokens=len(prompt),
        completion_tokens=len(text),
    )

    return q


# ----------------------------------------------------------------------
#  新しい問題のロード
# ----------------------------------------------------------------------
def load_new_question(session: SessionState, meta: MetaManager) -> None:
    """
    SessionState に新しい問題をセットする。
    - mode = "online" の場合はオンライン優先（失敗したらオフライン）
    - mode = "offline" の場合はオフラインのみ
    - mode = "auto" の場合はオンライン試行→失敗時オフライン
    いずれの場合も、MetaManager の choose_next_chapter により
    偏りを抑えた章選択を行う。
    """
    all_questions = get_all_questions()
    available_chapters = sorted({q.chapter_id for q in all_questions})
    if not available_chapters:
        st.error("問題バンクが空です。bank/question_bank.jsonl を確認してください。")
        return

    chapter_id = meta.choose_next_chapter(available_chapter_ids=available_chapters)
    if chapter_id is None:
        # フォールバックとして先頭の章を使用
        chapter_id = list(available_chapters)[0]

    mode = session.mode

    def try_online() -> Optional[Question]:
        return generate_online_question(meta, chapter_label=chapter_id)

    def try_offline() -> Optional[Question]:
        q = pick_random_from_chapter(chapter_id)
        if q is None:
            q = pick_random_question()
        return q

    question: Optional[Question] = None
    source = "offline"

    if mode == "online":
        question = try_online()
        source = "online" if question is not None else "offline"
        if question is None:
            question = try_offline()
    elif mode == "offline":
        question = try_offline()
        source = "offline"
    else:  # auto
        question = try_online()
        source = "online" if question is not None else "offline"
        if question is None:
            question = try_offline()

    if question is None:
        st.error("新しい問題を取得できませんでした。")
        return

    session.start_new_question(
        question=question,
        source="online" if source == "online" else "offline",
        model_name=get_preferred_model_name() if source == "online" else None,
    )


# ----------------------------------------------------------------------
#  ページ: ホーム
# ----------------------------------------------------------------------
def render_home_page() -> None:
    st.markdown("## 🧠 G検定クイズへようこそ")

    meta = get_meta_manager()
    usage = meta.meta.get("usage", {})
    total = usage.get("total_questions", 0)
    online = usage.get("online_questions", 0)
    offline = usage.get("offline_questions", 0)

    st.write(f"- 累計解答数: **{total} 問**")
    st.write(f"- オンライン出題: **{online} 問**")
    st.write(f"- オフライン出題: **{offline} 問**")

    st.write("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 クイズを始める", use_container_width=True):
            set_page("quiz")
            rerun()
    with col2:
        if st.button("🔁 間違えた問題だけで復習", use_container_width=True):
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
    if st.button("❓ 使い方", use_container_width=True):
        set_page("help")
        rerun()


# ----------------------------------------------------------------------
#  ページ: クイズ
# ----------------------------------------------------------------------
def render_quiz_main_page() -> None:
    session = get_session_state()
    meta = get_meta_manager()

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

        # 回答結果が表示されたら、自動的に画面下部（解説付近）までスクロールする
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

    st.markdown("## 🔁 間違えた問題だけで復習")

    wrongs = [r for r in session.history if not r.correct]
    if not wrongs:
        st.info("まだ間違えた問題の記録がありません。クイズを解いてから利用してください。")
    else:
        st.write(f"これまでに **{len(wrongs)} 問** 間違えています。")
        rows = []
        for r in reversed(wrongs[-10:]):
            q = get_question_by_id(r.question_id)
            if q is None:
                continue
            rows.append(f"- [{q.chapter_id}] {q.question[:40]}...")
        if rows:
            st.markdown("\n".join(rows))

    st.write("")
    if st.button("🎯 クイズ画面へ戻る", use_container_width=True):
        set_page("quiz")
        rerun()
    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  ページ: 学習統計
# ----------------------------------------------------------------------
def render_stats_page() -> None:
    session = get_session_state()
    meta = get_meta_manager()

    st.markdown("## 📊 学習統計")

    st.write("### セッション内の解答履歴")
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
    st.markdown("### Meta 情報 (クォータ状況)")

    quota = meta.get_quota_status()
    st.json(quota)

    st.write("")
    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  ページ: 設定
# ----------------------------------------------------------------------
def render_settings_page() -> None:
    st.markdown("## ⚙️ 設定")

    session = get_session_state()
    cfg = load_app_config()

    st.markdown("### 出題モード")

    mode_map = {
        "auto": "自動 (オンライン優先+フォールバック)",
        "online": "オンライン優先",
        "offline": "オフラインのみ",
    }
    modes = list(mode_map.keys())
    labels = [mode_map[m] for m in modes]

    try:
        index = modes.index(session.mode)
    except ValueError:
        index = 0

    selected_label = st.radio(
        "出題モード",
        labels,
        index=index,
    )
    selected_mode = modes[labels.index(selected_label)]
    session.mode = selected_mode

    st.write("---")
    st.markdown("### オンラインモデル")

    models = list_available_models()
    if not models:
        st.info("利用可能な Gemini モデルが見つかりませんでした。")
    else:
        preferred = get_preferred_model_name()
        try:
            idx = models.index(preferred) if preferred else 0
        except ValueError:
            idx = 0

        selected_model = st.selectbox(
            "使用するモデル",
            models,
            index=idx,
        )
        st.session_state["preferred_model"] = selected_model
        st.write(f"現在の優先モデル: `{selected_model}`")

    st.write("---")
    st.markdown("### config.toml (参考)")

    st.json(cfg)

    if st.button("🏠 ホームに戻る", use_container_width=True):
        set_page("home")
        rerun()


# ----------------------------------------------------------------------
#  ページ: 使い方
# ----------------------------------------------------------------------
def render_help_page() -> None:
    st.markdown("## ❓ 使い方")

    st.markdown(
        """
1. ホーム画面の「🚀 クイズを始める」からクイズを開始します。
2. 各問題の選択肢のいずれかをタップすると、その場で正解／不正解が判定されます。
3. 判定後は自動的に画面下部（メッセージと解説付近）までスクロールします。
4. 「次の問題 ▶」ボタンで別の問題に進みます。
5. 「🔁 間違えた問題だけで復習」で、不正解だった問題だけを復習できます。
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

    load_app_config()
    init_gemini_if_needed()

    page = get_page()

    if page == "quiz":
        render_quiz_main_page()
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