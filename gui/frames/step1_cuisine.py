"""
gui/frames/step1_cuisine.py
=============================
1단계: 음식 종류 선택 화면

CLI 버전의 select_cuisine_type()에 대응.
드롭다운(ttk.Combobox)으로 한식/양식/중식/일식/.../전체 중 하나를 선택받음.
"""

import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import CUISINE_TYPES
from gui.widgets import (
    make_step_header, make_nav_buttons, make_card_frame,
    COLOR_BG, COLOR_TEXT, FONT_LABEL
)


class CuisineFrame(tk.Frame):
    """
    1단계 화면: 음식 종류를 드롭다운으로 선택

    선택 가능한 값: config.settings.CUISINE_TYPES에 정의된 한식/양식/중식/일식/...
    "전체(상관없음)"도 옵션에 포함됨
    """

    def __init__(self, parent, app):
        """
        Args:
            parent: 이 프레임을 담을 부모 위젯 (보통 메인 윈도우의 컨테이너)
            app: 화면 전환을 담당하는 메인 App 객체 (gui/app.py의 App 클래스)
                 app.state로 공유 상태(AppState)에 접근하고,
                 app.go_to_next_step() / app.go_to_previous_step()으로 화면을 전환함
        """
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        make_step_header(
            self, step_number=1,
            title="어떤 종류의 음식이 드시고 싶으신가요?",
            subtitle="드롭다운에서 선택해주세요. 상관없으면 '전체'를 선택하세요."
        )

        card = make_card_frame(self)

        # 드롭다운에 표시할 선택지 목록 구성: ["전체", "한식", "양식", ...]
        self.display_options = ["전체"] + list(CUISINE_TYPES.values())

        tk.Label(
            card, text="음식 종류", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_TEXT,
            anchor="w"
        ).pack(anchor="w", pady=(20, 6))

        self.selected_value = tk.StringVar(value=self.app.state.cuisine_type)

        self.combobox = ttk.Combobox(
            card, textvariable=self.selected_value,
            values=self.display_options, state="readonly",
            font=FONT_LABEL, width=30
        )
        self.combobox.pack(anchor="w")

        # 첫 화면이므로 '이전' 버튼은 없음 (on_back=None)
        make_nav_buttons(self, on_next=self._handle_next, on_back=None)

    def _handle_next(self):
        """
        '다음' 버튼 클릭 시 실행됨.
        드롭다운에서 선택된 값을 공유 상태(AppState)에 저장하고 다음 단계로 이동.
        """
        self.app.state.cuisine_type = self.selected_value.get()
        self.app.go_to_next_step()
