"""
gui/frames/step7_location.py
================================
7단계: 위치 입력 화면

CLI 버전의 select_location()에 대응하지만, 가장 까다로운 화면임:
- '내 위치(자동 감지)'는 브라우저 위치 권한 → IP 추정 → 기본값 순으로
  최대 30초까지 걸릴 수 있는 3단계 폴백 작업
- 이 작업을 메인 스레드(화면을 그리는 스레드)에서 그대로 실행하면
  그 시간 동안 창 전체가 멈춘 것처럼 보임("응답 없음" 상태)
- 따라서 threading.Thread로 백그라운드에서 실행하고,
  완료되면 self.after(0, ...)를 통해 안전하게 메인 스레드로 결과를 전달함
  (Tkinter 위젯은 메인 스레드 밖에서 직접 건드리면 안 되는 제약이 있기 때문)
"""

import tkinter as tk
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui.widgets import (
    make_step_header, make_nav_buttons, make_card_frame,
    COLOR_BG, COLOR_TEXT, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_BORDER,
    COLOR_CARD_BG, COLOR_WARNING, COLOR_WARNING_BG,
    FONT_LABEL, FONT_SMALL, FONT_BUTTON
)

DEFAULT_LOCATION = {
    "address": "서울특별시 강남구 강남대로 396 (강남역)",
    "latitude": 37.4979,
    "longitude": 127.0276
}


class LocationFrame(tk.Frame):
    """7단계 화면: 주소 직접 입력 또는 내 위치 자동 감지 중 선택"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app
        self._detection_in_progress = False  # 중복 클릭 방지 플래그

        make_step_header(
            self, step_number=7,
            title="어느 지역에서 식사하실 예정인가요?",
            subtitle="직접 입력하거나, 내 위치를 자동으로 감지할 수 있습니다."
        )

        card = make_card_frame(self)

        # ── 선택 버튼 2개 (직접입력 / 내위치자동) ──────────
        button_row = tk.Frame(card, bg=COLOR_BG)
        button_row.pack(fill="x", pady=(10, 16))

        self.manual_btn = tk.Button(
            button_row, text="📝 직접 입력", font=FONT_BUTTON,
            command=self._show_manual_input, bg=COLOR_CARD_BG, fg=COLOR_TEXT,
            relief="flat", padx=20, pady=12, cursor="hand2",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        self.manual_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.auto_btn = tk.Button(
            button_row, text="📍 내 위치 (자동 감지)", font=FONT_BUTTON,
            command=self._start_auto_detection, bg=COLOR_CARD_BG, fg=COLOR_TEXT,
            relief="flat", padx=20, pady=12, cursor="hand2",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        self.auto_btn.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # ── 직접 입력용 영역 (처음엔 숨김) ──────────────
        self.manual_frame = tk.Frame(card, bg=COLOR_BG)
        tk.Label(
            self.manual_frame, text="주소 또는 지역명", font=FONT_LABEL,
            bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(anchor="w", pady=(8, 4))

        self.address_entry = tk.Entry(self.manual_frame, font=FONT_LABEL, width=40)
        self.address_entry.pack(anchor="w", fill="x")

        tk.Label(
            self.manual_frame, text="예시: 서울 강남구 역삼동, 홍대입구역",
            font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_BG
        ).pack(anchor="w", pady=(4, 0))

        # ── 상태 표시 영역 (감지 진행 상황, 결과, 경고) ────
        self.status_frame = tk.Frame(card, bg=COLOR_BG)
        self.status_frame.pack(fill="x", pady=(16, 0))

        self.status_label = tk.Label(
            self.status_frame, text="", font=FONT_SMALL, fg=COLOR_PRIMARY,
            bg=COLOR_BG, anchor="w", wraplength=560, justify="left"
        )
        self.status_label.pack(anchor="w")

        # ── 기존에 저장된 위치가 있으면 미리 보여줌 ────────
        if self.app.state.location:
            self._display_confirmed_location(self.app.state.location, warn=False)

        self.nav = make_nav_buttons(
            self, on_next=self._handle_next, on_back=self.app.go_to_previous_step,
            next_enabled=bool(self.app.state.location)
        )

    # ───────────────────────────────────────────
    # 직접 입력 흐름
    # ───────────────────────────────────────────

    def _show_manual_input(self):
        """'직접 입력' 버튼 클릭 시 입력칸을 화면에 표시"""
        self.manual_frame.pack(fill="x", pady=(0, 8))
        self.address_entry.delete(0, tk.END)
        self.address_entry.focus_set()
        self.address_entry.bind("<Return>", lambda e: self._submit_manual_address())

        # 입력칸 아래에 확인 버튼을 동적으로 추가
        if not hasattr(self, "confirm_btn"):
            self.confirm_btn = tk.Button(
                self.manual_frame, text="이 주소로 확인", font=FONT_SMALL,
                command=self._submit_manual_address, bg=COLOR_PRIMARY, fg="white",
                relief="flat", padx=12, pady=6, cursor="hand2"
            )
            self.confirm_btn.pack(anchor="w", pady=(8, 0))

    def _submit_manual_address(self):
        """입력한 주소를 카카오 지오코딩 API로 좌표 변환 (이건 보통 빠르므로 동기 처리)"""
        address = self.address_entry.get().strip()
        if not address:
            self._show_status("주소를 입력해주세요.", is_warning=True)
            return

        from utils.kakao_api import geocode_address
        self._show_status("주소를 확인하는 중입니다...", is_warning=False)
        self.update_idletasks()  # 상태 메시지를 즉시 화면에 반영

        coords = geocode_address(address)
        if coords:
            self._display_confirmed_location(coords, warn=False)
        else:
            self._show_status(
                "주소를 찾을 수 없습니다. 다시 입력하거나 기본 위치를 사용해주세요.",
                is_warning=True
            )
            self.app.state.location = dict(DEFAULT_LOCATION)
            self._set_next_enabled(True)

    # ───────────────────────────────────────────
    # 내 위치 자동 감지 흐름 (백그라운드 스레드)
    # ───────────────────────────────────────────

    def _start_auto_detection(self):
        """
        '내 위치(자동 감지)' 버튼 클릭 시 실행.
        브라우저 위치 권한 요청은 최대 30초까지 걸릴 수 있으므로,
        반드시 별도 스레드에서 실행해서 화면이 멈추지 않도록 함.
        """
        if self._detection_in_progress:
            return  # 이미 감지 중이면 중복 실행 방지

        self._detection_in_progress = True
        self.auto_btn.config(state="disabled", text="감지 중...")
        self.manual_btn.config(state="disabled")
        self._set_next_enabled(False)
        self._show_status(
            "브라우저를 열어 위치 권한을 요청합니다. 팝업에서 '허용'을 눌러주세요...",
            is_warning=False
        )

        # 백그라운드 스레드에서 실제 위치 감지 로직을 실행
        thread = threading.Thread(target=self._run_detection_in_background, daemon=True)
        thread.start()

    def _run_detection_in_background(self):
        """
        백그라운드 스레드에서 실행되는 함수.
        주의: 이 함수 안에서는 Tkinter 위젯을 직접 건드리면 안 됨!
              (Tkinter는 스레드 안전하지 않으므로, 결과는 self.after(0, ...)로
               메인 스레드에 안전하게 넘겨서 처리해야 함)
        """
        from utils.browser_location import get_precise_location_via_browser
        from utils.kakao_api import reverse_geocode, get_current_location_by_ip

        # 1순위: 브라우저 정밀 위치
        precise = get_precise_location_via_browser(timeout_seconds=30)
        if precise:
            address_info = reverse_geocode(precise["latitude"], precise["longitude"])
            address = address_info["address"] if address_info else "현재 위치 (정밀 감지)"
            result = {"address": address, "latitude": precise["latitude"], "longitude": precise["longitude"]}
            self._safe_after(lambda: self._on_detection_success(result, precise=True))
            return

        # 2순위: IP 기반 추정
        self._safe_after(lambda: self._show_status("정밀 위치 감지에 실패하여 IP 기반 추정으로 전환합니다...", is_warning=True))
        ip_location = get_current_location_by_ip()
        if ip_location:
            self._safe_after(lambda: self._on_detection_success(ip_location, precise=False))
            return

        # 3순위: 기본 위치
        self._safe_after(lambda: self._on_detection_failed())

    def _safe_after(self, callback):
        """
        백그라운드 스레드에서 메인 스레드로 안전하게 결과를 전달하는 헬퍼.

        winfo_exists()를 백그라운드 스레드에서 직접 호출하면 Tkinter 내부의
        스레드 검증 과정에서 약 1초간 블로킹되다 RuntimeError가 발생하는 것이
        확인되었음. 따라서 존재 여부 확인은 after() 콜백이 실제로 실행되는
        메인 스레드 시점으로 미루고, 여기서는 무조건 after()만 등록함.
        """
        def _run_callback_if_alive():
            try:
                if self.winfo_exists():
                    callback()
            except tk.TclError:
                pass

        try:
            self.after(0, _run_callback_if_alive)
        except RuntimeError:
            pass

    def _on_detection_success(self, location: dict, precise: bool):
        """
        백그라운드 스레드 작업이 끝난 뒤, 메인 스레드에서 안전하게 호출되는 콜백.
        self.after(0, ...)를 통해서만 호출되므로 여기서는 위젯을 자유롭게 건드려도 됨.
        """
        self._detection_in_progress = False
        self.auto_btn.config(state="normal", text="📍 내 위치 (자동 감지)")
        self.manual_btn.config(state="normal")

        if not precise:
            self._show_status(
                "⚠ IP 기반 위치는 시/구 단위로 추정되며 실제 위치와 차이가 있을 수 있습니다.",
                is_warning=True
            )
        self._display_confirmed_location(location, warn=False, append_status=not precise)

    def _on_detection_failed(self):
        """위치 자동 감지가 완전히 실패했을 때 (메인 스레드에서 호출됨)"""
        self._detection_in_progress = False
        self.auto_btn.config(state="normal", text="📍 내 위치 (자동 감지)")
        self.manual_btn.config(state="normal")

        self._show_status(
            "위치 자동 감지에 모두 실패하여 기본 위치(강남역)를 사용합니다.",
            is_warning=True
        )
        self.app.state.location = dict(DEFAULT_LOCATION)
        self._set_next_enabled(True)

    # ───────────────────────────────────────────
    # 공통 헬퍼
    # ───────────────────────────────────────────

    def _display_confirmed_location(self, location: dict, warn: bool, append_status: bool = False):
        """확정된 위치 정보를 화면에 표시하고 상태에 저장, 다음 버튼 활성화"""
        self.app.state.location = location

        message = f"✅ 위치 확인됨: {location.get('address', '알 수 없음')}"
        if not append_status:
            self._show_status(message, is_warning=warn)
        else:
            # IP 기반 경고 문구 뒤에 위치 확인 메시지를 덧붙여서 두 줄로 보여줌
            current = self.status_label.cget("text")
            self.status_label.config(text=f"{current}\n{message}")

        self._set_next_enabled(True)

    def _show_status(self, message: str, is_warning: bool):
        """상태 메시지를 화면에 표시 (경고면 색을 바꿔서 강조)"""
        color = COLOR_WARNING if is_warning else COLOR_PRIMARY
        self.status_label.config(text=message, fg=color)

    def _set_next_enabled(self, enabled: bool):
        """다음 버튼 활성화/비활성화 (nav 프레임 안의 버튼을 찾아서 조작)"""
        for widget in self.nav.winfo_children():
            if isinstance(widget, tk.Button) and widget.cget("text") in ("다음", "추천받기"):
                widget.config(state="normal" if enabled else "disabled")

    def _handle_next(self):
        """
        '다음' 버튼 클릭 시 실행.
        위치가 아직 확정되지 않았으면(이론상 버튼이 비활성화되어 있어야 하므로
        거의 발생하지 않지만) 안전하게 기본 위치로 대체.
        """
        if not self.app.state.location:
            self.app.state.location = dict(DEFAULT_LOCATION)
        self.app.go_to_next_step()
