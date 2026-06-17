"""
gui/frames/step4_excluded.py
===============================
4단계: 제외 메뉴 선택 화면

CLI 버전의 input_excluded_menu()에 대응.
CLI에서는 텍스트로 메뉴명을 직접 입력했지만(오타 위험, 철자 불일치 가능),
GUI에서는 DB에 실제로 존재하는 메뉴 목록을 체크박스로 보여줘서
오타 없이 정확하게 선택할 수 있도록 개선함.

스크롤 가능한 체크박스 목록을 위해 Canvas + Scrollbar 조합을 사용.
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


class ExcludedMenuFrame(tk.Frame):
    """4단계 화면: 제외하고 싶은 메뉴를 체크박스로 선택 (스크롤 가능)"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        make_step_header(
            self, step_number=4,
            title="먹기 싫거나 못 먹는 메뉴가 있나요?",
            subtitle="해당하는 메뉴를 모두 체크해주세요. 없으면 그냥 다음으로 넘어가세요."
        )

        card = make_card_frame(self)

        # ── 1단계에서 선택한 카테고리 기준으로 메뉴 목록 로드 ──
        # (예: '한식'을 선택했으면 한식 메뉴만 보여줘서 선택지를 줄임)
        all_menus = load_menu_database(self.app.state.cuisine_type)

        if not all_menus:
            tk.Label(
                card, text="표시할 메뉴가 없습니다. 다음으로 진행해주세요.",
                font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_BG
            ).pack(anchor="w", pady=20)
        else:
            scroll_area = self._make_scrollable_checklist(card)

            # 메뉴 이름 → BooleanVar 매핑 (이전에 선택했던 값 복원)
            self.checkbox_vars: dict[str, tk.BooleanVar] = {}
            previously_excluded = set(self.app.state.excluded_menus)

            for menu in all_menus:
                name = menu["menu_name"]
                var = tk.BooleanVar(value=(name in previously_excluded))
                self.checkbox_vars[name] = var
                make_checkbox_option(scroll_area, text=name, variable=var)

        make_nav_buttons(
            self, on_next=self._handle_next, on_back=self.app.go_to_previous_step
        )

    def _make_scrollable_checklist(self, parent) -> tk.Frame:
        """
        체크박스가 많을 때를 대비해 스크롤 가능한 영역을 생성

        tkinter에는 스크롤 가능한 Frame이 기본 제공되지 않으므로,
        Canvas 위에 Frame을 얹고 Scrollbar로 Canvas를 움직이는 표준적인 방식을 사용

        Returns:
            tk.Frame: 체크박스들을 추가해야 하는 실제 내부 프레임
        """
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

        # 마우스 휠 스크롤 지원 (Windows 기준 <MouseWheel> 이벤트)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return inner_frame

    def _handle_next(self):
        """체크된 메뉴 이름들을 모아서 excluded_menus 리스트로 저장"""
        if hasattr(self, "checkbox_vars"):
            self.app.state.excluded_menus = [
                name for name, var in self.checkbox_vars.items() if var.get()
            ]
        self.app.go_to_next_step()
