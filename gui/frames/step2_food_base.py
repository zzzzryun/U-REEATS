"""
gui/frames/step2_food_base.py
================================
2단계: 밥/면 선호도 선택 화면

CLI 버전의 select_noodle_or_rice()에 대응.
선택지가 3개뿐이므로(밥/면/상관없음) 드롭다운보다 라디오버튼이 한눈에 보기 좋음.
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui.widgets import (
    make_step_header, make_nav_buttons, make_card_frame, make_radio_option,
    COLOR_BG
)


class FoodBaseFrame(tk.Frame):
    """2단계 화면: 밥/면 중 선호하는 것을 라디오버튼으로 선택"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        make_step_header(
            self, step_number=2,
            title="밥과 면 중 어떤 것을 선호하시나요?",
            subtitle="하나를 선택해주세요."
        )

        card = make_card_frame(self)

        # 기존 상태값 복원: None은 "상관없음", "밥"/"면"은 그대로 사용
        current = self.app.state.food_base or "상관없음"
        self.selected_value = tk.StringVar(value=current)

        make_radio_option(
            card, text="밥", variable=self.selected_value, value="밥",
            description="볶음밥, 덮밥, 한정식 등 밥 종류 메뉴를 우선 추천합니다."
        )
        make_radio_option(
            card, text="면", variable=self.selected_value, value="면",
            description="파스타, 라멘, 국수 등 면 종류 메뉴를 우선 추천합니다."
        )
        make_radio_option(
            card, text="상관없음", variable=self.selected_value, value="상관없음",
            description="밥/면 구분 없이 추천합니다."
        )

        make_nav_buttons(
            self, on_next=self._handle_next, on_back=self.app.go_to_previous_step
        )

    def _handle_next(self):
        """
        선택된 값을 공유 상태에 저장.
        "상관없음"을 선택하면 None으로 저장해서 menu_recommendation.py의
        filter_menus()가 기대하는 형식(None = 필터링 안 함)에 맞춤.
        """
        value = self.selected_value.get()
        self.app.state.food_base = None if value == "상관없음" else value
        self.app.go_to_next_step()
