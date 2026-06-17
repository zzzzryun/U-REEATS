"""
gui/frames/step8_allergy.py
==============================
8단계: 알레르기 정보 선택 화면

CLI 버전의 input_allergy_info()에 대응.
4/5단계와 같은 체크박스 목록 패턴이지만, 데이터 소스가 DB가 아니라
config.settings.ALLERGY_LIST(고정된 10개 항목)라는 점이 다름.

알레르기 정보를 아예 체크하지 않고 넘어가는 경우(정보 없음)를 대비해
경고 문구를 화면에 항상 보이게 표시함 (요구사항: "missing allergy information을
safely handle하고 경고 메시지를 표시").
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import ALLERGY_LIST, ALLERGY_DISPLAY_NAMES
from gui.widgets import (
    make_step_header, make_nav_buttons, make_card_frame, make_checkbox_option,
    show_inline_warning, COLOR_BG
)


class AllergyFrame(tk.Frame):
    """8단계 화면: 알레르기 성분을 체크박스로 선택 (없으면 경고 표시 후 진행 가능)"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        make_step_header(
            self, step_number=8,
            title="알레르기가 있으신가요?",
            subtitle="해당 성분이 포함된 메뉴는 추천에서 자동으로 제외됩니다."
        )

        card = make_card_frame(self)

        self.checkbox_vars: dict[str, tk.BooleanVar] = {}
        previously_selected = set(self.app.state.allergies)

        grid_frame = tk.Frame(card, bg=COLOR_BG)
        grid_frame.pack(fill="x", pady=(10, 0))

        # 10개 항목을 2열로 배치해서 화면을 세로로 너무 길게 만들지 않음
        for index, code in enumerate(ALLERGY_LIST):
            display_name = ALLERGY_DISPLAY_NAMES.get(code, code)
            var = tk.BooleanVar(value=(code in previously_selected))
            self.checkbox_vars[code] = var

            row, col = divmod(index, 2)
            cell = tk.Frame(grid_frame, bg=COLOR_BG)
            cell.grid(row=row, column=col, sticky="w", padx=(0, 20))
            make_checkbox_option(cell, text=display_name, variable=var)

        # 알레르기 미입력 시 항상 보이는 안내 (체크박스를 하나라도 선택하면 숨김)
        self.warning_widget = None
        self._refresh_warning_visibility()

        # 체크박스 상태가 바뀔 때마다 경고 문구를 갱신
        for var in self.checkbox_vars.values():
            var.trace_add("write", lambda *args: self._refresh_warning_visibility())

        make_nav_buttons(
            self, on_next=self._handle_next, on_back=self.app.go_to_previous_step,
            next_text="추천받기"
        )

    def _refresh_warning_visibility(self):
        """체크된 항목이 하나도 없으면 경고를 보여주고, 하나라도 있으면 숨김"""
        any_checked = any(var.get() for var in self.checkbox_vars.values())

        if any_checked:
            if self.warning_widget is not None:
                self.warning_widget.pack_forget()
        else:
            if self.warning_widget is None:
                self.warning_widget = show_inline_warning(
                    self,
                    "알레르기 정보를 선택하지 않았습니다. 알레르기 성분 확인이 불가능한 "
                    "메뉴는 추천 시 우선순위가 낮아지고 별도로 표시됩니다."
                )
            else:
                self.warning_widget.pack(fill="x", pady=(8, 0))

    def _handle_next(self):
        """체크된 알레르기 코드들을 모아서 allergies 리스트로 저장"""
        self.app.state.allergies = [
            code for code, var in self.checkbox_vars.items() if var.get()
        ]
        self.app.go_to_next_step()
