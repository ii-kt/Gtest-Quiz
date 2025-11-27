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

from dataclasses import dataclass
from typing import Any, Dict, Optional

import streamlit as st

from .models import Question, SessionState


# ----------------------------------------------------------------------
#  テーマ定義
# ----------------------------------------------------------------------
THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#f5f5f7",
        "surface": "#ffffff",
        "surface_alt": "#f0f0f4",
        "primary": "#2563eb",
        "primary_soft": "#dbeafe",
        "border": "#d0d0dd",
        "text": "#111827",
        "muted": "#6b7280",
        "correct": "#16a34a",
        "incorrect": "#dc2626",
    },
    "dark": {
        "bg": "#0b1120",
        "surface": "#020617",
        "surface_alt": "#111827",
        "primary": "#3b82f6",
        "primary_soft": "#1d4ed8",
        "border": "#1f2937",
        "text": "#e5e7eb",
        "muted": "#9ca3af",
        "correct": "#22c55e",
        "incorrect": "#d64545",
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
        background: {theme['bg']};
        color: {theme['text']};
        -webkit-text-size-adjust: 100%;
        touch-action: manipulation;
        -webkit-tap-highlight-color: rgba(0,0,0,0);
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Helvetica Neue", Arial, sans-serif;
    }}

    .gq-container {{
        max-width: 700px;
        margin: 0 auto;
        padding: 0.5rem 0.75rem 2.5rem 0.75rem;
    }}

    .gq-header {{
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }}

    .gq-title-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    .gq-app-title {{
        font-weight: 600;
        font-size: 1.15rem;
    }}

    .gq-mode-badge {{
        padding: 0.1rem 0.5rem;
        border-radius: 999px;
        border: 1px solid {theme['border']};
        font-size: 0.75rem;
        white-space: nowrap;
    }}

    .gq-chapter-tags {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        font-size: 0.8rem;
    }}

    .gq-tag {{
        padding: 0.1rem 0.5rem;
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
        left: 0;
        top: 0;
        bottom: 0;
        background: {theme['primary']};
        transition: width 0.2s ease-out;
    }}

    .gq-question-box {{
        margin-top: 0.8rem;
        padding: 0.9rem;
        border-radius: 12px;
        background: {theme['surface']};
        border: 1px solid {theme['border']};
        font-size: 1rem;
        line-height: 1.6;
    }}

    .gq-choice-btn {{
        width: 100%;
        margin-top: 0.6rem;
        padding: 0.75rem 0.85rem;
        border-radius: 12px;
        border: 1px solid {theme['border']};
        background: {theme['surface']};
        color: {theme['text']};
        font-size: 0.95rem;
        text-align: left;
        transition: background 0.15s ease-out, border-color 0.15s ease-out;
    }}

    .gq-choice-btn:active {{
        background: {theme['surface']};
    }}

    .gq-choice-correct {{
        background: {theme['correct']}22 !important;
        border-color: {theme['correct']} !important;
    }}

    .gq-choice-incorrect {{
        background: {theme['incorrect']}22 !important;
        border-color: {theme['incorrect']} !important;
    }}

    .gq-explanation-box {{
        padding: 0.9rem;
        border-radius: 10px;
        background: {theme['surface_alt']};
        border: 1px solid {theme['border']};
        font-size: 0.95rem;
        line-height: 1.6;
    }}

    .gq-footer {{
        margin-top: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
        font-size: 0.75rem;
        color: {theme['muted']};
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
    # Streamlit の radio を横並びで使用
    labels = {"light": "ライト", "dark": "ダーク"}

    selected = st.radio(
        "テーマ",
        options=list(labels.keys()),
        index=list(labels.keys()).index(theme_key),
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

    引数:
        session:
            models.SessionState のインスタンス。
            - current_question に Question が入っている前提。
        progress_ratio:
            章内の進捗 (0.0〜1.0)。None の場合は表示しない。
        quota_status:
            MetaManager.get_quota_status() の戻り値を想定。
            total_used_tokens / estimated_limit_tokens / last_429_at / last_error
        mode_label:
            画面上に表示するモード表記 (例: "ONLINE", "OFFLINE", "AUTO")。

    戻り値:
        {
          "selected_choice": Optional[int],   # 新たに押された選択肢 index (なければ None)
          "clicked_next": bool,
          "clicked_prev": bool,
          "clicked_change_chapter": bool,
          "theme": str,                       # 現在のテーマキー
        }
    """
    # セーフティ: 問題がない場合
    if not isinstance(session.current_question, Question):
        st.error("問題がまだ選択されていません。")
        return {
            "selected_choice": None,
            "clicked_next": False,
            "clicked_prev": False,
            "clicked_change_chapter": False,
            "theme": _ensure_theme(),
        }

    # テーマを決定し、CSS を適用
    theme_key = _ensure_theme()
    theme = THEMES[theme_key]
    css = _generate_css(theme)
    st.markdown(css, unsafe_allow_html=True)

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

            # 章ラベルタグ
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
            # モードバッジ
            mode_html = (
                f"<div style='text-align:right;'>"
                f"<span class='gq-mode-badge'>{mode_label}</span>"
                f"</div>"
            )
            st.markdown(mode_html, unsafe_allow_html=True)
            _render_theme_selector(theme_key)

        # クォータメーター
        if quota_status is not None:
            _render_quota_meter(theme, quota_status)

        # 進捗バー（章内）
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
    # すでに回答済みかどうか
    answered_index = session.selected_index
    correct_index = q.correct_index if session.is_correct is not None else None

    for idx, choice_text in enumerate(q.choices):
        classes = ["gq-choice-btn"]

        if answered_index is not None and correct_index is not None:
            if idx == correct_index:
                classes.append("gq-choice-correct")
            elif idx == answered_index and answered_index != correct_index:
                classes.append("gq-choice-incorrect")

        class_attr = " ".join(classes)
        button_html = f"<button class='{class_attr}'>{choice_text}</button>"

        # Streamlit のボタンはクリック検知専用にして、見た目はカスタム HTML ボタンで表示する。
        # ラベルを空文字にしておくことで、選択肢が二重に表示される問題を避ける。
        if st.button(
            " ",
            key=f"gq_choice_{idx}",
            use_container_width=True,
        ):
            # 未回答時のみ「新たな選択」として扱う
            if answered_index is None:
                selected_choice = idx

        # 上記 st.button 用に class を当てるための HTML を後追いで描画（視覚のみ）
        st.markdown(
            f"<div style='margin-top:-3.1rem; pointer-events:none;'>{button_html}</div>",
            unsafe_allow_html=True,
        )

    # ----------------------------------------
    # 解説（回答済みの場合のみ）
    # ----------------------------------------
    if answered_index is not None:
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

    # 自動スクロールのターゲットとなるアンカー
    st.markdown("<div id='gq-answer-bottom' class='gq-safe-bottom'></div>", unsafe_allow_html=True)
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
    """
    quota_status を元にクォータメーターを描画する。
    quota_status は MetaManager.get_quota_status() の戻り値想定。
    """
    total = quota_status.get("total_used_tokens")
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