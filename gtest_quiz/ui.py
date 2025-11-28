"""
ui.py
======================

Streamlit ベースの UI コンポーネントをまとめたモジュール。

責務:
- iPhone Safari を主ターゲットとしたレイアウトとスタイル
- 問題画面の描画（質問・選択肢・解説）
- ヘッダー（シラバス情報・クォータメーター・テーマ切替）
- ナビゲーションボタン（前へ / 次へ / 章変更）

ここでは「見た目」と「ユーザー操作の入力」を扱い、
問題選択ロジックやメタ情報更新などのビジネスロジックは app.py 側に任せる。

戻り値として「何が押されたか」「どの選択肢が新たに選ばれたか」を返す。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List

import streamlit as st

from .models import SessionState, Question

# ----------------------------------------------------------------------
#  テーマ定義（カラフルな 3 テーマ）
# ----------------------------------------------------------------------

THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#fdfbff",
        "text": "#0f172a",
        "surface": "#ffffff",
        "surface_alt": "#f5f3ff",
        "border": "#e5e7eb",
        "primary": "#6366f1",        # indigo
        "primary_soft": "#e0e7ff",
        "correct": "#16a34a",
        "incorrect": "#dc2626",
    },
    "dark": {
        "bg": "#020617",
        "text": "#e5e7eb",
        "surface": "#020617",
        "surface_alt": "#0f172a",
        "border": "#1f2937",
        "primary": "#8b5cf6",        # violet
        "primary_soft": "#4c1d95",
        "correct": "#22c55e",
        "incorrect": "#f97373",
    },
    "blue": {
        "bg": "#0f172a",
        "text": "#e5e7eb",
        "surface": "#020617",
        "surface_alt": "#0b1120",
        "border": "#1e293b",
        "primary": "#38bdf8",        # sky
        "primary_soft": "#0ea5e9",
        "correct": "#22c55e",
        "incorrect": "#f97373",
    },
}

# ----------------------------------------------------------------------
#  CSS 生成
# ----------------------------------------------------------------------
def _generate_css(theme: Dict[str, str]) -> str:
    """テーマに応じたグローバル CSS を生成する。"""

    return f"""
    <style>
    html, body {{
        margin: 0;
        padding: 0;
        background: radial-gradient(circle at top, {theme['primary_soft']}22 0, {theme['bg']} 60%);
        color: {theme['text']};
        -webkit-text-size-adjust: 100%;
        touch-action: manipulation;
        -webkit-tap-highlight-color: rgba(0,0,0,0);
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Helvetica Neue", Arial, sans-serif;
    }}

    .gq-container {{
        max-width: 720px;
        margin: 0 auto;
        padding: 0.75rem 0.9rem 3rem 0.9rem;
    }}

    .gq-header {{
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }}

    .gq-title-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.5rem;
    }}

    .gq-app-title {{
        font-weight: 650;
        letter-spacing: 0.02em;
        font-size: 1.15rem;
    }}

    .gq-mode-badge {{
        padding: 0.1rem 0.65rem;
        border-radius: 999px;
        border: 1px solid {theme['border']};
        font-size: 0.75rem;
        white-space: nowrap;
        background: {theme['surface_alt']};
    }}

    .gq-chapter-tags {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        font-size: 0.8rem;
    }}

    .gq-tag {{
        padding: 0.1rem 0.6rem;
        border-radius: 999px;
        background: {theme['surface']};
        border: 1px solid {theme['border']};
    }}

    /* クォータメーター */
    .gq-quota {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }}

    .gq-quota-label {{
        white-space: nowrap;
        color: {theme['text']}99;
    }}

    .gq-quota-bar {{
        position: relative;
        flex: 1;
        height: 6px;
        border-radius: 999px;
        overflow: hidden;
        background: {theme['surface_alt']};
    }}

    .gq-quota-fill {{
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        background: linear-gradient(90deg, {theme['primary']} 0%, {theme['primary_soft']} 100%);
        transition: width 0.2s ease-out;
    }}

    .gq-question-box {{
        margin-top: 1rem;
        padding: 1rem 1rem;
        border-radius: 18px;
        background: {theme['surface']};
        border: 1px solid {theme['border']};
        font-size: 1rem;
        line-height: 1.7;
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
    }}

    /* 選択肢（未回答時のボタン） */
    .gq-choice-row {{
        margin-top: 0.7rem;
    }}

    .gq-choice-row .stButton button {{
        width: 100%;
        padding: 0.85rem 1rem;
        border-radius: 14px;
        border: 1px solid {theme['border']};
        background: linear-gradient(135deg, {theme['primary_soft']} 0%, {theme['surface']} 60%);
        color: {theme['text']};
        font-size: 0.95rem;
        text-align: left;
        box-shadow: 0 8px 16px rgba(15, 23, 42, 0.08);
        transition: transform 0.08s ease-out, box-shadow 0.08s ease-out, border-color 0.08s ease-out;
    }}

    .gq-choice-row .stButton button:active {{
        transform: translateY(1px);
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
        border-color: {theme['primary']};
    }}

    /* 回答後のカード表示 */
    .gq-choice-card {{
        width: 100%;
        margin-top: 0.7rem;
        padding: 0.85rem 1rem;
        border-radius: 14px;
        border: 1px solid {theme['border']};
        background: {theme['surface']};
        font-size: 0.95rem;
        line-height: 1.6;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.06);
    }}

    .gq-choice-card-correct {{
        border-color: {theme['correct']};
        background: linear-gradient(135deg, {theme['correct']}22 0%, {theme['surface']} 60%);
    }}

    .gq-choice-card-incorrect {{
        border-color: {theme['incorrect']};
        background: linear-gradient(135deg, {theme['incorrect']}18 0%, {theme['surface']} 60%);
    }}

    .gq-explanation-box {{
        padding: 0.9rem 1rem;
        border-radius: 12px;
        background: {theme['surface_alt']};
        border: 1px solid {theme['border']};
        font-size: 0.95rem;
        line-height: 1.7;
    }}

    .gq-footer {{
        margin-top: 0.9rem;
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        font-size: 0.75rem;
        color: {theme['text']}99;
        text-align: center;
    }}

    .gq-safe-bottom {{
        height: 2.5rem;
    }}
    </style>
    """

# ----------------------------------------------------------------------
#  テーマ選択 / CSS 適用
# ----------------------------------------------------------------------
def _ensure_theme() -> str:
    """セッションに theme キーを用意し、現在のテーマキーを返す。"""
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"
    theme_key = st.session_state.get("theme", "light")
    if theme_key not in THEMES:
        theme_key = "light"
        st.session_state["theme"] = "light"
    return theme_key


def _render_theme_selector(theme_key: str) -> str:
    """ヘッダーの右上あたりにテーマ切替を表示し、選択されたテーマキーを返す。"""
    options = ["light", "dark", "blue"]
    labels = {"light": "Light", "dark": "Dark", "blue": "Blue"}

    idx = options.index(theme_key) if theme_key in options else 0
    selected = st.radio(
        "テーマ",
        options,
        index=idx,
        horizontal=True,
        label_visibility="collapsed",
        format_func=lambda k: labels.get(k, k),
    )
    st.session_state["theme"] = selected
    return selected


# ----------------------------------------------------------------------
#  公開 API: クイズページの描画
# ----------------------------------------------------------------------
def render_quiz_page(
    session: SessionState,
    *,
    progress_ratio: Optional[float] = None,
    quota_status: Optional[Dict[str, Any]] = None,
    mode_label: str = "AUTO",
) -> Dict[str, Any]:
    """
    クイズページ全体を描画し、ユーザー操作の結果を返す。

    戻り値:
        {
          "selected_choice": Optional[int],   # 新たに押された選択肢 index (なければ None)
          "clicked_next": bool,
          "clicked_prev": bool,
          "clicked_change_chapter": bool,
          "theme": str,                       # 現在のテーマキー
        }
    """
    if not isinstance(session.current_question, Question):
        st.error("問題がまだ選択されていません。")
        return {
            "selected_choice": None,
            "clicked_next": False,
            "clicked_prev": False,
            "clicked_change_chapter": False,
            "theme": _ensure_theme(),
        }

    # テーマ決定と CSS 注入
    theme_key = _ensure_theme()
    theme = THEMES[theme_key]
    st.markdown(_generate_css(theme), unsafe_allow_html=True)

    # 操作結果の初期値
    selected_choice: Optional[int] = None
    clicked_next = False
    clicked_prev = False
    clicked_change_chapter = False

    q = session.current_question

    # ----------------------------------------
    # コンテナ開始
    # ----------------------------------------
    st.markdown("<div class='gq-container'>", unsafe_allow_html=True)

    # ----------------------------------------
    # ヘッダー
    # ----------------------------------------
    with st.container():
        st.markdown("<div class='gq-header'>", unsafe_allow_html=True)

        col_left, col_right = st.columns([2.2, 1.8])

        with col_left:
            st.markdown(
                "<div class='gq-title-row'>"
                "<div class='gq-app-title'>G検定クイズ</div>"
                "</div>",
                unsafe_allow_html=True,
            )

            tags_html: List[str] = [
                f"<span class='gq-tag'>{q.chapter_group}</span>",
                f"<span class='gq-tag'>{q.chapter_id}</span>",
                f"<span class='gq-tag'>難易度: {q.difficulty}</span>",
            ]
            st.markdown(
                "<div class='gq-chapter-tags'>" + "".join(tags_html) + "</div>",
                unsafe_allow_html=True,
            )

        with col_right:
            mode_html = (
                f"<div style='text-align:right;'>"
                f"<span class='gq-mode-badge'>{mode_label}</span>"
                f"</div>"
            )
            st.markdown(mode_html, unsafe_allow_html=True)
            _render_theme_selector(theme_key)

        if quota_status is not None:
            _render_quota_meter(theme, quota_status)

        if progress_ratio is not None:
            pr = min(max(progress_ratio, 0.0), 1.0)
            percent = int(pr * 100)
            bar_html = (
                "<div class='gq-quota' style='margin-top:0.3rem;'>"
                "<div class='gq-quota-label'>章の進捗</div>"
                "<div class='gq-quota-bar'>"
                f"<div class='gq-quota-fill' style='width:{percent}%'></div>"
                "</div>"
                f"<div style='font-size:0.75rem; white-space:nowrap;'>{percent}%</div>"
                "</div>"
            )
            st.markdown(bar_html, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # ----------------------------------------
    # 問題文
    # ----------------------------------------
    st.markdown(
        f"<div class='gq-question-box'>{q.question}</div>",
        unsafe_allow_html=True,
    )

    # ----------------------------------------
    # 選択肢
    # ----------------------------------------
    answered_index = session.selected_index
    correct_index = q.correct_index if session.is_correct is not None else None

    for idx, choice_text in enumerate(q.choices):
        if answered_index is None:
            # 未回答: カラフルなボタンとして表示
            st.markdown("<div class='gq-choice-row'>", unsafe_allow_html=True)
            if st.button(
                choice_text,
                key=f"gq_choice_{idx}",
                use_container_width=True,
            ):
                selected_choice = idx
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # 回答済み: 正解/不正解を色分けしたカードとして表示
            classes = ["gq-choice-card"]
            if correct_index is not None:
                if idx == correct_index:
                    classes.append("gq-choice-card-correct")
                elif idx == answered_index and answered_index != correct_index:
                    classes.append("gq-choice-card-incorrect")
            class_attr = " ".join(classes)
            st.markdown(
                f"<div class='{class_attr}'>{choice_text}</div>",
                unsafe_allow_html=True,
            )

    # ----------------------------------------
    # 解説（回答済みの場合のみ）
    # ----------------------------------------
    if answered_index is not None:
        # 回答後はデフォルトで展開しておく
        with st.expander("解説", expanded=True):
            st.markdown(
                f"<div class='gq-explanation-box'>{q.explanation}</div>",
                unsafe_allow_html=True,
            )

    # ----------------------------------------
    # ナビゲーション
    # ----------------------------------------
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("◀ ひとつ前", key="gq_prev", use_container_width=True):
            clicked_prev = True
    with col_next:
        if st.button("次の問題 ▶", key="gq_next", use_container_width=True):
            clicked_next = True

    col_change, col_dummy = st.columns([1, 1])
    with col_change:
        if st.button("章を変える", key="gq_change_chapter", use_container_width=True):
            clicked_change_chapter = True

    # フッター
    st.markdown(
        "<div class='gq-footer'>"
        "<div>G検定対策用クイズアプリ</div>"
        "<div>© Gtest-Quiz</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    # 自動スクロールのターゲット
    st.markdown(
        "<div id='gq-answer-bottom' class='gq-safe-bottom'></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    return {
        "selected_choice": selected_choice,
        "clicked_next": clicked_next,
        "clicked_prev": clicked_prev,
        "clicked_change_chapter": clicked_change_chapter,
        "theme": st.session_state.get("theme", theme_key),
    }


# ----------------------------------------------------------------------
#  クォータメーター描画
# ----------------------------------------------------------------------
def _render_quota_meter(theme: Dict[str, str], quota_status: Dict[str, Any]) -> None:
    """推定クォータメーターを描画する。"""

    total = int(quota_status.get("total_used_tokens", 0))
    limit = quota_status.get("estimated_limit_tokens")
    last_429_at = quota_status.get("last_429_at")

    if isinstance(limit, (int, float)) and limit > 0:
        ratio = max(min(total / float(limit), 1.0), 0.0)
        percent = int(ratio * 100)
        label_text = f"推定クォータ {total}/{int(limit)} tokens"
    else:
        ratio = 0.0
        percent = 0
        label_text = "推定クォータ 学習中"

    extra = ""
    if last_429_at:
        extra = f"・最終 429: {last_429_at}"

    html = (
        "<div class='gq-quota'>"
        f"<div class='gq-quota-label'>{label_text}{extra}</div>"
        "<div class='gq-quota-bar'>"
        f"<div class='gq-quota-fill' style='width:{percent}%'></div>"
        "</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)