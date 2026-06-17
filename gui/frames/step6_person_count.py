"""
gui/frames/step6_person_count.py
====================================
6단계: 인원 수 입력 화면

CLI 버전의 input_person_count()에 대응.
CLI에서는 1~100 사이의 숫자를 텍스트로 입력받고 validate_number_input()으로
유효성을 검사했지만, GUI에서는 Spinbox(증감 버튼이 달린 숫자 입력 위젯)를 사용해서
범위를 벗어난 값 자체를 입력할 수 없게 만듦 (잘못된 입력이 원천적으로 불가능).
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui.widgets import (
    make_step_header, make_nav_buttons, make_card_frame,
    COLOR_BG, COLOR_TEXT, COLOR_TEXT_MUTED, COLOR_PRIMARY,
    FONT_LABEL, FONT_SMALL
)

MIN_PERSON_COUNT = 1
MAX_PERSON_COUNT = 100


class PersonCountFrame(tk.Frame):
    """6단계 화면: 식사 인원 수를 Spinbox로 입력 (1~100명 범위로 제한)"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        make_step_header(
            self, step_number=6,
            title="몇 명이서 드실 예정인가요?",
            subtitle="혼밥이면 1명, 단체 식사면 인원 수를 늘려주세요."
        )

        card = make_card_frame(self)

        tk.Label(
            card, text="인원 수", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(anchor="w", pady=(20, 6))

        self.person_count_var = tk.IntVar(value=self.app.state.person_count)

        spin_row = tk.Frame(card, bg=COLOR_BG)
        spin_row.pack(anchor="w")

        self.spinbox = tk.Spinbox(
            spin_row, from_=MIN_PERSON_COUNT, to=MAX_PERSON_COUNT,
            textvariable=self.person_count_var, font=FONT_LABEL,
            width=8, justify="center",
            command=self._update_hint_text  # 화살표 클릭 시에도 안내 문구 갱신
        )
        self.spinbox.pack(side="left")

        tk.Label(
            spin_row, text="명", font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(side="left", padx=(8, 0))

        # 숫자를 직접 타이핑했을 때도 안내 문구가 갱신되도록 변화 감지
        self.person_count_var.trace_add("write", lambda *args: self._update_hint_text())

        self.hint_label = tk.Label(
            card, text="", font=FONT_SMALL, fg=COLOR_PRIMARY, bg=COLOR_BG,
            anchor="w"
        )
        self.hint_label.pack(anchor="w", pady=(12, 0))
        self._update_hint_text()

        make_nav_buttons(
            self, on_next=self._handle_next, on_back=self.app.go_to_previous_step
        )

    def _update_hint_text(self):
        """
        현재 선택된 인원 수에 맞춰 안내 문구를 갱신
        (CLI 버전의 print_info()에서 인원별로 다른 메시지를 보여주던 것과 동일한 로직)
        """
        try:
            count = self.person_count_var.get()
        except tk.TclError:
            # Spinbox에 빈 값이나 숫자가 아닌 값이 입력된 중간 상태일 수 있음
            return

        if count <= 0:
            text = ""
        elif count == 1:
            text = "혼밥 모드! 혼자 먹기 좋은 음식점을 우선 추천합니다."
        elif count <= 4:
            text = f"{count}명 소규모 식사로 추천합니다."
        else:
            text = f"{count}명 단체 식사! 단체석 있는 음식점을 우선 추천합니다."

        self.hint_label.config(text=text)

    def _handle_next(self):
        """
        Spinbox 값을 읽어서 person_count로 저장.
        Spinbox는 from_/to로 범위를 제한하지만, 직접 타이핑으로 범위 밖 값이나
        빈 값을 입력하는 극단적인 경우를 대비해 한 번 더 방어적으로 검증함.
        """
        try:
            count = self.person_count_var.get()
        except tk.TclError:
            count = MIN_PERSON_COUNT  # 잘못된 값이면 안전하게 최솟값으로 대체

        count = max(MIN_PERSON_COUNT, min(MAX_PERSON_COUNT, count))
        self.app.state.person_count = count
        self.app.go_to_next_step()
