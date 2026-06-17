"""
gui/frames/step3_price.py
============================
3단계: 가격대 선택 화면

CLI 버전의 input_price_range()에 대응.
config.settings.PRICE_RANGES에 정의된 가격대 목록을 라디오버튼으로 표시.
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.settings import PRICE_RANGES
from gui.widgets import (
    make_step_header, make_nav_buttons, make_card_frame, make_radio_option,
    COLOR_BG
)


class PriceFrame(tk.Frame):
    """3단계 화면: 1인 기준 예산 범위를 라디오버튼으로 선택"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        make_step_header(
            self, step_number=3,
            title="예산은 어느 정도 생각하고 계신가요?",
            subtitle="1인 기준 가격대를 선택해주세요."
        )

        card = make_card_frame(self)

        # 라디오버튼 값으로는 PRICE_RANGES의 key("1","2","3","4")를 그대로 사용하고,
        # "0"은 "상관없음"에 대응시킴
        current_label = self.app.state.price_range.get("label", "전체")
        current_key = self._find_key_by_label(current_label)
        self.selected_key = tk.StringVar(value=current_key)

        for key, info in PRICE_RANGES.items():
            make_radio_option(
                card, text=info["label"], variable=self.selected_key, value=key
            )

        make_radio_option(
            card, text="상관없음", variable=self.selected_key, value="0"
        )

        make_nav_buttons(
            self, on_next=self._handle_next, on_back=self.app.go_to_previous_step
        )

    def _find_key_by_label(self, label: str) -> str:
        """이전에 저장된 label 문자열로부터 PRICE_RANGES의 key를 역으로 찾음"""
        for key, info in PRICE_RANGES.items():
            if info["label"] == label:
                return key
        return "0"  # 못 찾으면 기본값: 상관없음

    def _handle_next(self):
        """선택된 가격대 정보를 {'label', 'min', 'max'} 딕셔너리로 변환해서 저장"""
        key = self.selected_key.get()
        if key == "0":
            self.app.state.price_range = {"label": "전체", "min": 0, "max": 999999}
        else:
            self.app.state.price_range = dict(PRICE_RANGES[key])
        self.app.go_to_next_step()
