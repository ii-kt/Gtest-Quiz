"""
ui.py - モバイル優先のクイズ画面 UI
----------------------------------

・問題文は枠なしの大きめテキスト
・選択肢は A/B/C/D ラベル付きのカード風ボタン
・回答後は正解/誤答/その他を色分け
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List

import streamlit as st

from .models import Question, SessionState

# ----------------------------------------------------------------------
#  テーマ定義
# ----------------------------------------------------------------------
THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#f6f7fb",
        "text": "#0f172a",
        "surface": "#ffffff",
        "surface_alt": "#eef2ff",
        "border": "#e2e8f0",
        "primary": "#6366f1",
        "accent": "#a855f7",
        "correct": "#16a34a",
        "incorrect": "#dc2626",
        "muted": "#6b7280",
    },
    "dark": {
        "bg": "#020617",
        "text": "#e5e7eb",
        "surface": "#020617",
        "surface_alt": "#0b1120",
        "border": "#1f2937",
        "primary": "#818cf8",
        "accent": "#c084fc",
        "correct": "#22c55e",
        "incorrect": "#f97373",
        "muted": "#9ca3af",
    },
    "blue": {
        "bg": "#0b1120",
        "text": "#e5e7eb",
        "surface": "#020617",
        "surface_alt": "#0f172a",
        "border": "#1e293b",
        "primary": "#38bdf8",
        "accent": "#7dd3fc",
        "correct": "#22c55e",
        "incorrect": "#f97373",
        "muted": "#94a3b8",
    },
}


# ----------------------------------------------------------------------
#  CSS
# ----------------------------------------------------------------------
def _generate_css(theme: Dict[str, str]) -> str:
    return f"""
    <style>
    body {{
        background: {theme['bg']};
        color: {theme['text']};
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Helvetica Neue", Arial, sans-serif;
    }}

    .gq-container {{
        max-width: 720px;
        margin: 0 auto;
        padding: 0.9rem 1rem 3rem 1rem;
    }}

    .gq-header {{
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        margin-bottom: 0.4rem;
    }}

    .gq-title-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}

    .gq-app-title {{
        font-weight: 650;
        font-size: 1.15rem;
        letter-spacing: 0.02em;
    }}

    .gq-mode-badge {{
        padding: 0.1rem 0.6rem;
        border-radius: 999px;
        border: 1px solid {theme['border']};
        font-size: 0.75rem;
        background: {theme['surface_alt']};
        white-space: nowrap;
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

    .gq-question-text {{
        margin-top: 1.0rem;
        margin-bottom: 0.6rem;
        font-size: 1.02rem;
        line-height: 1.8;
        font-weight: 500;
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
        color: {theme['muted']};
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
        left: 0; top: 0; bottom: 0;
        background: linear-gradient(90deg, {theme['primary']} 0%, {theme['accent']} 100%);
        transition: width 0.2s ease-out;
    }}

    /* 選択肢（未回答時） */
    .gq-choice-row {{
        margin-top: 0.55rem;
        margin-bottom: 0.1rem;
    }}

    .gq-choice-row .stButton>button {{
        width: 100%;
        text-align: left;
        padding: 0.9rem 1rem;
        border-radius: 14px;
        border: 1px solid {theme['border']};
        background: {theme['surface']};
        color: {theme['text']};
        font-size: 0.95rem;
        line-height: 1.6;
        box-shadow: 0 8px 16px rgba(15, 23, 42, 0.18);
        transition: transform 0.06s ease-out,
                    box-shadow 0.06s ease-out,
                    border-color 0.06s ease-out,
                    background 0.06s ease-out;
    }}

    .gq-choice-row .stButton>button:active {{
        transform: translateY(1px);
        box-shadow: 0 4px 10px rgba(15, 23, 42, 0.2);
        border-color: {theme['primary']};
        background: {theme['surface_alt']};
    }}

    /* 回答済みカード */
    .gq-choice-card {{
        width: 100%;
        margin-top: 0.55rem;
        padding: 0.9rem 1rem;
        border-radius: 14px;
        border: 1px solid {theme['border']};
        background: {theme['surface']};
        font-size: 0.95rem;
        line-height: 1.6;
        box-shadow: 0 8px 16px rgba(15, 23, 42, 0.18);
    }}

    .gq-choice-card.correct {{
        border-color: {theme['correct']};
        background: linear-gradient(135deg, {theme['correct']}22, {theme['surface']});
    }}

    .gq-choice-card.wrong {{
        border-color: {theme['incorrect']};
        background: linear-gradient(135deg, {theme['incorrect']}22, {theme['surface']});
    }}

    .gq-choice-card.neutral {{
        opacity: 0.85;
    }}

    .gq-choice-label {{
        font-weight: 700;
        margin-right: 0.4rem;
        color: {theme['accent']};
    }}

    .gq-explanation-box {{
        margin-top: 0.9rem;
        padding: 0.95rem 1rem;
        border-radius: 14px;
        background: {theme['surface_alt']};
        border: 1px solid {theme['border']};
        font-size: 0.95rem;
        line-height: 1.7;
    }}

    .gq-footer {{
        margin-top: 1.0rem;
        text-align: center;
        font-size: 0.75rem;
        color: {theme['muted']};
    }}

    .gq-safe-bottom {{
        height: 2.4rem;
    }}
    </style>
    """


def _ensure_theme() -> str:
    if "theme" not in st.session_state:
        st.session_state["theme"] = "light"
    key = st.session_state.get("theme", "light")
    if key not in THEMES:
        key = "light"
        st.session_state["theme"] = "light"
    return key


def _render_theme_selector(theme_key: str) -> str:
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


def _render_quota_meter(theme: Dict[str, str], quota_status: Dict[str, Any]) -> None:
    total = int(quota_status.get("total_used_tokens", 0))
    limit = quota_status.get("estimated_limit_tokens")
    last_429_at = quota_status.get("last_429_at")

    if isinstance(limit, (int, float)) and limit > 0:
        ratio = max(min(total / float(limit), 1.0), 0.0)
        percent = int(ratio * 100)
        label_text = f"推定クォータ {total}/{int(limit)} tokens"
    else:
        percent = 0
        label_text = "推定クォータ 学習中"

    extra = f"・最終 429: {last_429_at}" if last_429_at else ""

    html = (
        "<div class='gq-quota'>"
        f"<div class='gq-quota-label'>{label_text}{extra}</div>"
        "<div class='gq-quota-bar'>"
        f"<div class='gq-quota-fill' style='width:{percent}%'></div>"
        "</div>"
        "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------------
#  メイン: クイズページ
# ----------------------------------------------------------------------
def render_quiz_page(
    session: SessionState,
    *,
    progress_ratio: Optional[float] = None,
    quota_status: Optional[Dict[str, Any]] = None,
    mode_label: str = "AUTO",
) -> Dict[str, Any]:
    if not isinstance(session.current_question, Question):
        st.error("問題がまだ選択されていません。")
        return {
            "selected_choice": None,
            "clicked_next": False,
            "clicked_prev": False,
            "clicked_change_chapter": False,
            "theme": _ensure_theme(),
        }

    theme_key = _ensure_theme()
    theme = THEMES[theme_key]
    st.markdown(_generate_css(theme), unsafe_allow_html=True)

    selected_choice: Optional[int] = None
    clicked_next = False
    clicked_prev = False
    clicked_change_chapter = False

    q = session.current_question
    answered_index = session.selected_index
    correct_index = q.correct_index
    labels = ["A", "B", "C", "D"]

    # コンテナ開始
    st.markdown("<div class='gq-container'>", unsafe_allow_html=True)

    # ヘッダー
    with st.container():
        st.markdown("<div class='gq-header'>", unsafe_allow_html=True)
        col_left, col_right = st.columns([2.2, 1.6])
        with col_left:
            st.markdown(
                "<div class='gq-title-row'>"
                "<div class='gq-app-title'>G検定クイズ</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            tags_html = [
                f"<span class='gq-tag'>{q.chapter_group}</span>",
                f"<span class='gq-tag'>{q.chapter_id}</span>",
                f"<span class='gq-tag'>難易度: {q.difficulty}</span>",
            ]
            st.markdown(
                "<div class='gq-chapter-tags'>" + "".join(tags_html) + "</div>",
                unsafe_allow_html=True,
            )
        with col_right:
            st.markdown(
                f"<div style='text-align:right;'><span class='gq-mode-badge'>{mode_label}</span></div>",
                unsafe_allow_html=True,
            )
            _render_theme_selector(theme_key)

        if quota_status is not None:
            _render_quota_meter(theme, quota_status)

        if progress_ratio is not None:
            pr = min(max(progress_ratio, 0.0), 1.0)
            percent = int(pr * 100)
            bar = (
                "<div class='gq-quota' style='margin-top:0.2rem;'>"
                "<div class='gq-quota-label'>章の進捗</div>"
                "<div class='gq-quota-bar'>"
                f"<div class='gq-quota-fill' style='width:{percent}%'></div>"
                "</div>"
                f"<div style='font-size:0.75rem; white-space:nowrap;'>{percent}%</div>"
                "</div>"
            )
            st.markdown(bar, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    # 問題文（枠なし）
    st.markdown(
        f"<div class='gq-question-text'>{q.question}</div>",
        unsafe_allow_html=True,
    )

    # 選択肢
    for idx, choice_text in enumerate(q.choices):
        label = labels[idx] if idx < len(labels) else f"{idx+1}"

        if answered_index is None:
            # 未回答: ボタン表示
            st.markdown("<div class='gq-choice-row'>", unsafe_allow_html=True)
            if st.button(f"{label}. {choice_text}", key=f"gq_choice_{idx}", use_container_width=True):
                selected_choice = idx
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            # 回答済み: 状態に応じたカード表示
            if idx == correct_index:
                state = "correct"
            elif idx == answered_index and answered_index != correct_index:
                state = "wrong"
            else:
                state = "neutral"

            st.markdown(
                f"<div class='gq-choice-card {state}'>"
                f"<span class='gq-choice-label'>{label}</span>{choice_text}"
                "</div>",
                unsafe_allow_html=True,
            )

    # 解説（回答済みのみ）
    if answered_index is not None:
        st.markdown(
            f"<div class='gq-explanation-box'>{q.explanation}</div>",
            unsafe_allow_html=True,
        )

    # 自動スクロールターゲット
    st.markdown("<div id='gq-answer-bottom' class='gq-safe-bottom'></div>", unsafe_allow_html=True)

    # ナビゲーション
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("◀ ひとつ前", key="gq_prev", use_container_width=True):
            clicked_prev = True
    with col_next:
        if st.button("次の問題 ▶", key="gq_next", use_container_width=True):
            clicked_next = True

    col_change, _ = st.columns([1, 1])
    with col_change:
        if st.button("章を変える", key="gq_change_chapter", use_container_width=True):
            clicked_change_chapter = True

    st.markdown(
        "<div class='gq-footer'>G検定対策用クイズアプリ / © Gtest-Quiz</div>",
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