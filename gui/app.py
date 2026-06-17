"""
gui/app.py
===========
9개 화면(Frame)을 묶어서 전환을 관리하는 메인 애플리케이션 클래스

CLI 버전의 main.py에 있던 메인 루프(while True: ... next_action = ...)를
이벤트 기반 구조로 재구성한 것. CLI는 코드가 순서대로 진행되며 input()에서
멈춰 기다리지만, GUI는 각 화면이 '다음'/'이전' 버튼을 누를 때마다
go_to_next_step() / go_to_previous_step()이 호출되어 화면이 바뀌는 방식.

화면 전환 원리:
- 모든 Frame을 같은 위치(container)에 겹쳐서 만들어두고, 필요한 것만 보여주는
  대신, 메모리 효율을 위해 "현재 화면만 생성하고 이전 화면은 제거"하는 방식을 사용.
  (9단계 결과 화면은 추천 계산 등 무거운 작업을 포함하므로, 안 보는 화면을
   계속 살려두면 불필요하게 자원을 소모함)
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gui.state import AppState
from gui.widgets import COLOR_BG

from gui.frames.step1_cuisine import CuisineFrame
from gui.frames.step2_food_base import FoodBaseFrame
from gui.frames.step3_price import PriceFrame
from gui.frames.step4_excluded import ExcludedMenuFrame
from gui.frames.step5_preferred import PreferredMenuFrame
from gui.frames.step6_person_count import PersonCountFrame
from gui.frames.step7_location import LocationFrame
from gui.frames.step8_allergy import AllergyFrame
from gui.frames.step9_result import ResultFrame


class App:
    """
    U-RE EATS GUI의 메인 컨트롤러.

    역할:
    - tk.Tk() 메인 윈도우를 생성하고 관리
    - AppState 인스턴스 하나를 만들어서 모든 화면이 공유하도록 함
    - 화면 순서(STEP_CLASSES)를 정의하고, 현재 화면 인덱스를 추적
    - go_to_next_step() / go_to_previous_step() / go_to_step(index)로 화면을 교체
    """

    # 화면 순서: 인덱스 0~8이 1~9단계에 대응
    STEP_CLASSES = [
        CuisineFrame,        # 0: 1단계 - 음식 종류
        FoodBaseFrame,       # 1: 2단계 - 밥/면
        PriceFrame,          # 2: 3단계 - 가격대
        ExcludedMenuFrame,   # 3: 4단계 - 제외 메뉴
        PreferredMenuFrame,  # 4: 5단계 - 선호 메뉴
        PersonCountFrame,    # 5: 6단계 - 인원 수
        LocationFrame,       # 6: 7단계 - 위치
        AllergyFrame,        # 7: 8단계 - 알레르기
        ResultFrame,         # 8: 9단계 - 결과 (최종)
    ]

    def __init__(self, root: tk.Tk):
        """
        Args:
            root: main.py에서 생성한 tk.Tk() 인스턴스
        """
        self.root = root
        self.state = AppState()
        self.current_step_index = 0
        self.current_frame: tk.Frame | None = None

        self._setup_window()

        # 화면을 담을 컨테이너 (이 안에서 Frame들이 교체됨)
        self.container = tk.Frame(self.root, bg=COLOR_BG)
        self.container.pack(fill="both", expand=True)

        self._render_current_step()

    def _setup_window(self):
        """메인 윈도우의 제목, 크기, 최소 크기를 설정"""
        self.root.title("U-RE EATS - 개인 맞춤형 메뉴 & 음식점 추천")
        self.root.geometry("700x720")
        self.root.minsize(640, 600)
        self.root.configure(bg=COLOR_BG)

        # 창을 닫을 때 확인 없이 바로 종료 (필요 시 messagebox로 확인창 추가 가능)
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

    def _render_current_step(self):
        """
        현재 current_step_index에 해당하는 화면(Frame)을 생성해서 보여줌.
        이전 화면이 있으면 먼저 제거(destroy)해서 메모리를 정리함.
        """
        if self.current_frame is not None:
            self.current_frame.destroy()

        step_class = self.STEP_CLASSES[self.current_step_index]
        self.current_frame = step_class(self.container, app=self)
        self.current_frame.pack(fill="both", expand=True)

    # ───────────────────────────────────────────
    # 화면 전환 메서드 (각 Frame에서 호출됨)
    # ───────────────────────────────────────────

    def go_to_next_step(self):
        """
        다음 단계로 이동.
        각 Frame의 '다음' 버튼 콜백(_handle_next)이 자신의 입력값을
        self.state에 저장한 뒤 이 메서드를 호출하는 구조.
        """
        if self.current_step_index < len(self.STEP_CLASSES) - 1:
            self.current_step_index += 1
            self._render_current_step()

    def go_to_previous_step(self):
        """이전 단계로 이동. 이미 입력했던 값은 각 Frame의 __init__에서 복원됨."""
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self._render_current_step()

    def go_to_step(self, index: int):
        """
        특정 단계로 직접 이동.
        주로 9단계(결과 화면)에서 '처음부터 다시 입력하기'를 눌렀을 때
        go_to_step(0)으로 1단계로 돌아가는 용도로 사용.
        """
        if 0 <= index < len(self.STEP_CLASSES):
            self.current_step_index = index
            self._render_current_step()

    def quit_app(self):
        """애플리케이션을 안전하게 종료"""
        self.root.quit()
        self.root.destroy()
