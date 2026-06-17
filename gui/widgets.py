"""
gui/widgets.py
===============
모든 화면(Frame)에서 공통으로 사용하는 위젯 생성 헬퍼 함수 모음

목적:
- 9개 화면마다 똑같은 스타일의 제목/버튼/안내문구를 매번 새로 작성하지 않도록 함
- 색상, 폰트, 여백을 한 곳에서 관리해서 전체 화면의 통일성을 보장
- tkinter 기본 위젯에 일관된 디자인을 입혀서 보여주는 "껍데기" 함수들
"""

import tkinter as tk
from tkinter import ttk

# ─────────────────────────────────────────────
# 색상 테마 (한 곳에서 관리)
# ─────────────────────────────────────────────
COLOR_BG = "#FAFAF8"
COLOR_PRIMARY = "#0F6E56"        # 메인 강조색 (버튼, 진행 표시)
COLOR_PRIMARY_DARK = "#085041"
COLOR_TEXT = "#2C2C2A"
COLOR_TEXT_MUTED = "#5F5E5A"
COLOR_BORDER = "#D3D1C7"
COLOR_WARNING = "#854F0B"
COLOR_WARNING_BG = "#FAEEDA"
COLOR_DANGER = "#A32D2D"
COLOR_CARD_BG = "#FFFFFF"

FONT_TITLE = ("Malgun Gothic", 18, "bold")
FONT_SUBTITLE = ("Malgun Gothic", 11)
FONT_LABEL = ("Malgun Gothic", 12)
FONT_BUTTON = ("Malgun Gothic", 11, "bold")
FONT_SMALL = ("Malgun Gothic", 9)

TOTAL_STEPS = 8  # 결과 화면을 제외한 입력 단계 수


def make_step_header(parent, step_number: int, title: str, subtitle: str = "") -> tk.Frame:
    """
    각 화면 맨 위에 들어가는 "N/8단계 - 제목" 헤더와 진행률 바를 생성

    Args:
        parent: 헤더를 붙일 부모 위젯
        step_number: 현재 단계 번호 (1~8)
        title: 화면 제목 (예: "음식 종류를 선택해주세요")
        subtitle: 보조 설명 (선택)

    Returns:
        tk.Frame: 생성된 헤더 프레임 (parent에 이미 pack된 상태로 반환)
    """
    header = tk.Frame(parent, bg=COLOR_BG)
    header.pack(fill="x", padx=30, pady=(20, 10))

    step_label = tk.Label(
        header, text=f"{step_number} / {TOTAL_STEPS} 단계",
        font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_BG
    )
    step_label.pack(anchor="w")

    # 진행률 바 (ttk.Progressbar 사용)
    progress = ttk.Progressbar(
        header, orient="horizontal", length=300, mode="determinate",
        maximum=TOTAL_STEPS, value=step_number
    )
    progress.pack(anchor="w", pady=(4, 12), fill="x")

    title_label = tk.Label(
        header, text=title, font=FONT_TITLE, fg=COLOR_TEXT, bg=COLOR_BG,
        anchor="w", justify="left"
    )
    title_label.pack(anchor="w")

    if subtitle:
        subtitle_label = tk.Label(
            header, text=subtitle, font=FONT_SUBTITLE, fg=COLOR_TEXT_MUTED,
            bg=COLOR_BG, anchor="w", justify="left"
        )
        subtitle_label.pack(anchor="w", pady=(4, 0))

    return header


def make_nav_buttons(
    parent,
    on_next,
    on_back=None,
    next_text: str = "다음",
    back_text: str = "이전",
    next_enabled: bool = True
) -> tk.Frame:
    """
    화면 하단에 들어가는 "이전 / 다음" 네비게이션 버튼 영역을 생성

    Args:
        parent: 버튼 영역을 붙일 부모 위젯
        on_next: '다음' 버튼 클릭 시 실행할 콜백 함수
        on_back: '이전' 버튼 클릭 시 실행할 콜백 함수 (None이면 이전 버튼 숨김 - 첫 화면용)
        next_text: 다음 버튼에 표시할 문구 (마지막 단계는 "추천받기"로 바꿀 수 있음)
        back_text: 이전 버튼 문구
        next_enabled: 다음 버튼 활성화 여부 (필수 입력이 안 됐으면 False로)

    Returns:
        tk.Frame: 생성된 버튼 프레임
    """
    nav = tk.Frame(parent, bg=COLOR_BG)
    nav.pack(fill="x", padx=30, pady=(20, 24), side="bottom")

    next_btn = tk.Button(
        nav, text=next_text, font=FONT_BUTTON, command=on_next,
        bg=COLOR_PRIMARY, fg="white", activebackground=COLOR_PRIMARY_DARK,
        activeforeground="white", relief="flat", padx=24, pady=10,
        cursor="hand2", state="normal" if next_enabled else "disabled"
    )
    next_btn.pack(side="right")

    if on_back is not None:
        back_btn = tk.Button(
            nav, text=back_text, font=FONT_LABEL, command=on_back,
            bg=COLOR_BG, fg=COLOR_TEXT_MUTED, activebackground=COLOR_BORDER,
            relief="flat", padx=20, pady=10, cursor="hand2",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        back_btn.pack(side="right", padx=(0, 12))

    return nav


def make_card_frame(parent) -> tk.Frame:
    """
    화면 본문(선택지, 체크박스 등)을 담는 카드 형태의 컨테이너 생성

    Args:
        parent: 카드를 붙일 부모 위젯

    Returns:
        tk.Frame: 생성된 카드 프레임 (이 안에 자식 위젯을 추가하면 됨)
    """
    card = tk.Frame(parent, bg=COLOR_BG)
    card.pack(fill="both", expand=True, padx=30, pady=10)
    return card


def make_radio_option(
    parent,
    text: str,
    variable: tk.StringVar,
    value: str,
    description: str = ""
) -> tk.Frame:
    """
    카드 스타일의 라디오 버튼 한 개를 생성 (선택지가 적을 때 사용)

    Args:
        parent: 부모 위젯
        text: 라디오 버튼 옆에 표시할 메인 텍스트
        variable: 선택 상태를 저장할 tk.StringVar
        value: 이 라디오 버튼이 선택됐을 때 variable에 들어갈 값
        description: 보조 설명 (선택)

    Returns:
        tk.Frame: 생성된 라디오 옵션 프레임
    """
    option = tk.Frame(parent, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER,
                       highlightthickness=1, cursor="hand2")
    option.pack(fill="x", pady=4)

    radio = tk.Radiobutton(
        option, text=text, variable=variable, value=value,
        font=FONT_LABEL, bg=COLOR_CARD_BG, fg=COLOR_TEXT,
        activebackground=COLOR_CARD_BG, selectcolor=COLOR_CARD_BG,
        anchor="w", padx=12, pady=10, cursor="hand2"
    )
    radio.pack(fill="x")

    if description:
        desc_label = tk.Label(
            option, text=description, font=FONT_SMALL, fg=COLOR_TEXT_MUTED,
            bg=COLOR_CARD_BG, anchor="w", padx=36
        )
        desc_label.pack(fill="x", pady=(0, 8))

    return option


def make_checkbox_option(parent, text: str, variable: tk.BooleanVar) -> tk.Checkbutton:
    """
    체크박스 한 개를 생성 (제외 메뉴, 선호 메뉴, 알레르기 목록에서 사용)

    Args:
        parent: 부모 위젯
        text: 체크박스 옆에 표시할 텍스트
        variable: 체크 상태를 저장할 tk.BooleanVar

    Returns:
        tk.Checkbutton: 생성된 체크박스 위젯
    """
    checkbox = tk.Checkbutton(
        parent, text=text, variable=variable,
        font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_TEXT,
        activebackground=COLOR_BG, selectcolor=COLOR_CARD_BG,
        anchor="w", padx=4, pady=6, cursor="hand2"
    )
    checkbox.pack(fill="x", anchor="w")
    return checkbox


def show_inline_warning(parent, message: str) -> tk.Label:
    """
    화면 안에 경고/안내 메시지를 노란색 배경 박스로 표시
    (CLI의 print_warning()에 대응하는 GUI 버전)

    Args:
        parent: 부모 위젯
        message: 표시할 경고 문구

    Returns:
        tk.Label: 생성된 경고 라벨
    """
    warning = tk.Label(
        parent, text=f"  ⚠  {message}", font=FONT_SMALL,
        fg=COLOR_WARNING, bg=COLOR_WARNING_BG, anchor="w",
        padx=12, pady=8, wraplength=560, justify="left"
    )
    warning.pack(fill="x", pady=(8, 0))
    return warning


def clear_frame(frame: tk.Frame):
    """
    프레임 안의 모든 자식 위젯을 제거 (화면을 다시 그리기 전에 호출)

    Args:
        frame: 비울 프레임
    """
    for widget in frame.winfo_children():
        widget.destroy()
