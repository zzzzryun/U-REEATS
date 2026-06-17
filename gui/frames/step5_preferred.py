"""
gui/frames/step5_preferred.py
================================
5단계: 선호 메뉴 선택 화면

CLI 버전의 input_preferred_menu()에 대응.
4단계(제외 메뉴)와 거의 동일한 구조이지만 의미가 반대임:
여기서 체크한 메뉴는 점수 가중치를 받아 추천 1순위로 올라갈 가능성이 높아짐
(menu_recommendation.py의 _calculate_menu_score 함수 참고).
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from modules.menu_recommendation import load_menu_database
from gui.widgets import (
    make_step_header, make_nav_buttons, make_card_frame, make_checkbox_option,
    COLOR_BG, COLOR_TEXT_MUTED, FONT_SMALL
)


class PreferredMenuFrame(tk.Frame):
    """5단계 화면: 특별히 먹고 싶은 메뉴를 체크박스로 선택 (스크롤 가능)"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        make_step_header(
            self, step_number=5,
            title="특별히 먹고 싶은 메뉴가 있나요?",
            subtitle="체크한 메뉴는 추천 시 우선적으로 고려됩니다. 없으면 다음으로 넘어가세요."
        )

        card = make_card_frame(self)

        all_menus = load_menu_database(self.app.state.cuisine_type)

        # 제외 메뉴로 이미 체크된 항목은 선호 메뉴 목록에서 제외
        # (같은 메뉴를 동시에 '제외'와 '선호'로 체크하는 모순을 방지)
        excluded_set = set(self.app.state.excluded_menus)
        available_menus = [m for m in all_menus if m["menu_name"] not in excluded_set]

        if not available_menus:
            tk.Label(
                card, text="표시할 메뉴가 없습니다. 다음으로 진행해주세요.",
                font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_BG
            ).pack(anchor="w", pady=20)
        else:
            scroll_area = self._make_scrollable_checklist(card)

            self.checkbox_vars: dict[str, tk.BooleanVar] = {}
            previously_preferred = set(self.app.state.preferred_menus)

            for menu in available_menus:
                name = menu["menu_name"]
                var = tk.BooleanVar(value=(name in previously_preferred))
                self.checkbox_vars[name] = var
                make_checkbox_option(scroll_area, text=name, variable=var)

        make_nav_buttons(
            self, on_next=self._handle_next, on_back=self.app.go_to_previous_step
        )

    def _make_scrollable_checklist(self, parent) -> tk.Frame:
        """스크롤 가능한 체크박스 영역 생성 (4단계와 동일한 구현)"""
        container = tk.Frame(parent, bg=COLOR_BG)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=COLOR_BG, highlightthickness=0, height=260)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        inner_frame = tk.Frame(canvas, bg=COLOR_BG)

        inner_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return inner_frame

    def _handle_next(self):
        """체크된 메뉴 이름들을 모아서 preferred_menus 리스트로 저장"""
        if hasattr(self, "checkbox_vars"):
            self.app.state.preferred_menus = [
                name for name, var in self.checkbox_vars.items() if var.get()
            ]
        self.app.go_to_next_step()
