"""
ui.py - モバイル優先で完全リニューアルした UI
-----------------------------------------------

特徴:
- 問題文は大きめカード
- 選択肢は A/B/C/D ラベル付きの flat-card ボタン
- 押し間違い防止のため、選択肢は明確に分離
- 正解/不正解は「上部の細い色バー」で可視化
- iPhone Safari でのレンダリング崩れを完全排除
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import streamlit as st
from .models import Question, SessionState

# -----------------------------------------------------------
# テーマカラー（Material You 風）
# -----------------------------------------------------------

THEMES = {
    "light": {
        "bg": "#F6F7FB",
        "text": "#1E293B",
        "surface": "#FFFFFF",
        "surface_alt": "#EEF2FF",
        "border": "#D4DAE7",
        "primary": "#6366F1",   # indigo
        "accent": "#A78BFA",    # purple
        "correct": "#16A34A",
        "incorrect": "#DC2626",
    },
    "dark": {
        "bg": "#0F172A",
        "text": "#E2E8F0",
        "surface": "#1E293B",
        "surface_alt": "#334155",
        "border": "#475569",
        "primary": "#818CF8",
        "accent": "#C084FC",
        "correct": "#22C55E",
        "incorrect": "#F87171",
    },
    "blue": {
        "bg": "#0A192F",
        "text": "#E2E8F0",
        "surface": "#102A43",
        "surface_alt": "#243B53",
        "border": "#334E68",
        "primary": "#38BDF8",
        "accent": "#7DD3FC",
        "correct": "#22C55E",
        "incorrect": "#F87171",
    },
}

# -----------------------------------------------------------
# CSS
# -----------------------------------------------------------

def _apply_css(theme: dict):
    st.markdown(
        f"""
        <style>
        body {{
            background: {theme["bg"]};
            color: {theme["text"]};
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", Helvetica, Arial;
        }}

        .gq-container {{
            max-width: 640px;
            margin: 0 auto;
            padding: 0.8rem 1rem 3rem 1rem;
        }}

        .gq-question-card {{
            background: {theme["surface"]};
            border: 1px solid {theme["border"]};
            border-radius: 18px;
            padding: 1.1rem 1.2rem;
            font-size: 1rem;
            line-height: 1.7;
            margin-bottom: 1.1rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        }}

        .gq-choice-btn button {{
            width: 100%;
            text-align: left;
            background: {theme["surface"]};
            color: {theme["text"]};
            border: 1px solid {theme["border"]};
            padding: 0.95rem 1rem;
            border-radius: 14px;
            font-size: 0.95rem;
            line-height: 1.5;
            box-shadow: 0 6px 14px rgba(0,0,0,0.05);
            margin-bottom: 0.75rem;
        }}

        .gq-choice-btn button:active {{
            background: {theme["surface_alt"]};
            border-color: {theme["primary"]};
        }}

        .gq-choice-card {{
            width: 100%;
            background: {theme["surface"]};
            border: 1px solid {theme["border"]};
            padding: 1rem 1rem;
            border-radius: 14px;
            margin-bottom: 0.75rem;
            line-height: 1.6;
            box-shadow: 0 6px 14px rgba(0,0,0,0.05);
            position: relative;
        }}

        .gq-correct-bar {{
            height: 4px;
            background: {theme["correct"]};
            width: 100%;
            border-radius: 4px 4px 0 0;
            position: absolute;
            left: 0; top: 0;
        }}

        .gq-incorrect-bar {{
            height: 4px;
            background: {theme["incorrect"]};
            width: 100%;
            border-radius: 4px 4px 0 0;
            position: absolute;
            left: 0; top: 0;
        }}

        .gq-label {{
            font-weight: 700;
            margin-right: 0.4rem;
            color: {theme["accent"]};
        }}

        .gq-explanation {{
            background: {theme["surface_alt"]};
            border: 1px solid {theme["border"]};
            border-radius: 14px;
            padding: 1rem;
            font-size: 0.95rem;
            margin-top: 1rem;
            line-height: 1.7;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------------------------------------
# メインUI
# -----------------------------------------------------------

def render_quiz_page(
    session: SessionState,
    *,
    progress_ratio: Optional[float] = None,
    quota_status: Optional[dict] = None,
    mode_label: str = "AUTO",
):
    if not isinstance(session.current_question, Question):
        st.error("問題が読み込めません。")
        return dict(selected_choice=None, clicked_next=False, clicked_prev=False, clicked_change_chapter=False)

    theme_key = st.session_state.get("theme", "light")
    theme = THEMES[theme_key]

    _apply_css(theme)

    q = session.current_question

    selected_choice = None
    clicked_next = False
    clicked_prev = False
    clicked_change_chapter = False

    st.markdown("<div class='gq-container'>", unsafe_allow_html=True)

    # -------------------
    # 問題文カード
    # -------------------
    st.markdown(f"<div class='gq-question-card'>{q.question}</div>", unsafe_allow_html=True)

    # -------------------
    # 選択肢
    # -------------------
    answered_index = session.selected_index
    correct_index = q.correct_index

    labels = ["A", "B", "C", "D"]

    for idx, choice in enumerate(q.choices):
        if answered_index is None:
            # 未回答：ボタンで表示
            with st.container():
                st.markdown("<div class='gq-choice-btn'>", unsafe_allow_html=True)
                if st.button(f"{labels[idx]}. {choice}", key=f"choice_{idx}", use_container_width=True):
                    selected_choice = idx
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            # 回答済み：カード表示
            bar = ""
            if idx == correct_index:
                bar = "<div class='gq-correct-bar'></div>"
            elif idx == answered_index and idx != correct_index:
                bar = "<div class='gq-incorrect-bar'></div>"

            st.markdown(
                f"""
                <div class='gq-choice-card'>
                    {bar}
                    <span class='gq-label'>{labels[idx]}</span>{choice}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # -------------------
    # 解説
    # -------------------
    if answered_index is not None:
        st.markdown(f"<div class='gq-explanation'>{q.explanation}</div>", unsafe_allow_html=True)

    # -------------------
    # 自動スクロールアンカー
    # -------------------
    st.markdown("<div id='gq-answer-bottom'></div>", unsafe_allow_html=True)

    # -------------------
    # ナビゲーション
    # -------------------
    cols = st.columns(3)
    if cols[0].button("◀ 前へ"):
        clicked_prev = True
    if cols[1].button("次へ ▶"):
        clicked_next = True
    if cols[2].button("章変更"):
        clicked_change_chapter = True

    st.markdown("</div>", unsafe_allow_html=True)

    return dict(
        selected_choice=selected_choice,
        clicked_next=clicked_next,
        clicked_prev=clicked_prev,
        clicked_change_chapter=clicked_change_chapter,
    )