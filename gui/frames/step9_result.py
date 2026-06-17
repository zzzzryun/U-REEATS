"""
gui/frames/step9_result.py
==============================
9단계 (최종): 추천 결과 화면

CLI 버전의 display_recommended_menu(), display_recommended_store(),
display_recommendation_summary(), ask_retry_recommendation()을
하나의 화면으로 통합한 버전.

추천 계산(recommend_menu + get_restaurant_recommendation)은 카카오 API
호출을 포함해 시간이 걸릴 수 있으므로 7단계와 동일하게 백그라운드
스레드에서 실행하고, 결과는 self.after(0, ...)로 안전하게 반영함.

진행률 헤더(make_step_header)는 사용하지 않음 - 결과 화면은 "8단계 중 N번째"가
아니라 마법사의 끝이므로 별도의 헤더 스타일을 사용함.
"""

import tkinter as tk
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui.widgets import (
    COLOR_BG, COLOR_TEXT, COLOR_TEXT_MUTED, COLOR_PRIMARY, COLOR_PRIMARY_DARK,
    COLOR_BORDER, COLOR_CARD_BG, COLOR_WARNING, COLOR_WARNING_BG, COLOR_DANGER,
    FONT_TITLE, FONT_SUBTITLE, FONT_LABEL, FONT_BUTTON, FONT_SMALL,
    show_inline_warning, clear_frame
)


class ResultFrame(tk.Frame):
    """9단계 화면: 추천 메뉴와 음식점을 보여주고, 재추천/재시작 옵션을 제공"""

    def __init__(self, parent, app):
        super().__init__(parent, bg=COLOR_BG)
        self.app = app

        # 스크롤 가능한 전체 컨테이너 (메뉴+음식점 3개를 다 보여주면 길어지므로)
        self.canvas = tk.Canvas(self, bg=COLOR_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=COLOR_BG)

        self.content.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.content, anchor="nw", width=640)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._show_loading_state()

        # 화면이 생성되자마자 추천 계산을 백그라운드에서 시작
        thread = threading.Thread(target=self._run_recommendation_in_background, daemon=True)
        thread.start()

    # ───────────────────────────────────────────
    # 로딩 / 추천 계산
    # ───────────────────────────────────────────

    def _show_loading_state(self):
        """추천 계산이 진행되는 동안 보여줄 로딩 화면"""
        clear_frame(self.content)
        loading = tk.Frame(self.content, bg=COLOR_BG)
        loading.pack(fill="both", expand=True, pady=120)

        tk.Label(
            loading, text="🔍  메뉴를 분석하고 음식점을 검색하는 중입니다...",
            font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_TEXT
        ).pack()
        tk.Label(
            loading, text="잠시만 기다려주세요.", font=FONT_SUBTITLE,
            bg=COLOR_BG, fg=COLOR_TEXT_MUTED
        ).pack(pady=(8, 0))

    def _run_recommendation_in_background(self):
        """
        백그라운드 스레드에서 실행: 메뉴 추천 + 음식점 검색.
        이 함수 안에서는 Tkinter 위젯을 직접 건드리지 않고,
        결과를 self.after(0, ...)를 통해서만 화면에 반영함.
        """
        from modules.menu_recommendation import recommend_menu
        from modules.restaurant_search import get_restaurant_recommendation

        user_conditions = self.app.state.to_user_conditions()

        recommended_menus, allergy_warnings = recommend_menu(
            user_conditions, top_n=3, exclude_menu_ids=self.app.state.shown_menu_ids
        )

        if not recommended_menus:
            self._safe_after(lambda: self._render_no_result(user_conditions))
            return

        top_menu = recommended_menus[0]
        self.app.state.shown_menu_ids.add(top_menu["menu_id"])

        recommended_stores = get_restaurant_recommendation(top_menu, user_conditions)

        self.app.state.last_top_menu = top_menu
        self.app.state.last_stores = recommended_stores

        self._safe_after(lambda: self._render_result(top_menu, recommended_stores, allergy_warnings))

    def _safe_after(self, callback):
        """
        백그라운드 스레드에서 메인 스레드로 안전하게 결과를 전달하는 헬퍼.

        중요한 설계 원칙 (이전 버전의 버그를 고친 부분):
        - winfo_exists()를 포함한 거의 모든 Tkinter 메서드는 메인 스레드에서만
          호출이 보장됨. 백그라운드 스레드에서 self.winfo_exists()를 직접 호출하면
          내부적으로 1초 가까이 블로킹되다가 RuntimeError가 발생하는 것이 확인됨
          (Tkinter/Tcl이 스레드 간 호출을 검증하는 과정에서 발생하는 현상).
        - 따라서 "위젯이 아직 살아있는가?"라는 확인은 반드시 메인 스레드,
          즉 after() 콜백이 실제로 실행되는 그 시점에 해야 함.
        - self.after() 자체는 스레드에서 호출해도 안전하다고 알려진 Tkinter API이므로,
          여기서는 무조건 after()를 등록하고, 실제 존재 여부 검사는
          콜백 내부(_run_callback_if_alive)로 미룸.
        """
        def _run_callback_if_alive():
            # 이 함수는 메인 스레드(Tkinter 이벤트 루프)에서 실행되므로
            # winfo_exists()를 안전하게 호출할 수 있음
            try:
                if self.winfo_exists():
                    callback()
            except tk.TclError:
                pass  # 위젯이 이미 파괴된 경우 - 조용히 무시

        try:
            self.after(0, _run_callback_if_alive)
        except RuntimeError:
            # 메인 루프 자체가 이미 종료된 경우 (예: 프로그램이 완전히 닫힌 뒤)
            pass

    # ───────────────────────────────────────────
    # 결과 없음 처리
    # ───────────────────────────────────────────

    def _render_no_result(self, user_conditions: dict):
        """조건에 맞는 메뉴가 없을 때 (CLI의 display_no_result_message에 대응)"""
        clear_frame(self.content)

        tk.Label(
            self.content, text="😅  조건에 맞는 메뉴를 찾지 못했습니다",
            font=FONT_TITLE, bg=COLOR_BG, fg=COLOR_DANGER
        ).pack(anchor="w", padx=30, pady=(24, 8))

        tips = tk.Label(
            self.content,
            text="다음을 시도해보세요:\n"
                 "  • 가격대 범위를 넓혀보세요\n"
                 "  • 음식 종류를 '전체'로 변경해보세요\n"
                 "  • 제외 메뉴 수를 줄여보세요",
            font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_TEXT_MUTED, justify="left", anchor="w"
        )
        tips.pack(anchor="w", padx=30, pady=(0, 20))

        self._render_action_buttons(found_result=False)

    # ───────────────────────────────────────────
    # 결과 렌더링
    # ───────────────────────────────────────────

    def _render_result(self, menu: dict, stores: list, allergy_warnings: list):
        """추천 메뉴 + 음식점 목록을 화면에 그림"""
        clear_frame(self.content)

        tk.Label(
            self.content, text="✅  추천 결과", font=FONT_TITLE,
            bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(anchor="w", padx=30, pady=(20, 12))

        self._render_menu_card(menu)

        if allergy_warnings:
            warning_text = (
                "다음 메뉴는 알레르기 정보가 충분하지 않습니다: "
                + ", ".join(allergy_warnings[:3])
                + " → 주문 전 음식점에 알레르기 성분을 직접 문의하세요."
            )
            show_inline_warning(self.content, warning_text)

        tk.Frame(self.content, bg=COLOR_BORDER, height=1).pack(fill="x", padx=30, pady=20)

        tk.Label(
            self.content, text="📍  추천 음식점", font=FONT_TITLE,
            bg=COLOR_BG, fg=COLOR_TEXT
        ).pack(anchor="w", padx=30, pady=(0, 12))

        if not stores:
            tk.Label(
                self.content,
                text="주변에서 음식점을 찾을 수 없습니다. 직접 카카오맵에서 검색해보세요!",
                font=FONT_LABEL, bg=COLOR_BG, fg=COLOR_TEXT_MUTED
            ).pack(anchor="w", padx=30, pady=(0, 20))
        else:
            for rank, store in enumerate(stores, start=1):
                self._render_store_card(rank, store)

        self._render_action_buttons(found_result=True)

    def _render_menu_card(self, menu: dict):
        """추천 메뉴 1개를 카드 형태로 표시"""
        card = tk.Frame(self.content, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=30, pady=(0, 8))

        inner = tk.Frame(card, bg=COLOR_CARD_BG)
        inner.pack(fill="x", padx=20, pady=16)

        tk.Label(
            inner, text=f"🍴 {menu.get('menu_name', '-')}", font=FONT_TITLE,
            bg=COLOR_CARD_BG, fg=COLOR_TEXT
        ).pack(anchor="w")

        price_text = f"{menu.get('price_range_min', 0):,}원 ~ {menu.get('price_range_max', 0):,}원"
        tk.Label(
            inner, text=f"{menu.get('category', '-')}  |  {price_text}",
            font=FONT_SUBTITLE, bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED
        ).pack(anchor="w", pady=(4, 0))

        if menu.get("description"):
            tk.Label(
                inner, text=menu["description"], font=FONT_LABEL,
                bg=COLOR_CARD_BG, fg=COLOR_TEXT, wraplength=560, justify="left", anchor="w"
            ).pack(anchor="w", pady=(10, 0))

        reasons = menu.get("reasons", [])
        if reasons:
            tk.Label(
                inner, text="💡 추천 이유", font=FONT_LABEL,
                bg=COLOR_CARD_BG, fg=COLOR_TEXT
            ).pack(anchor="w", pady=(12, 4))
            for reason in reasons:
                tk.Label(
                    inner, text=f"   {reason}", font=FONT_SMALL,
                    bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, anchor="w"
                ).pack(anchor="w")

    def _render_store_card(self, rank: int, store: dict):
        """추천 음식점 1개를 카드 형태로 표시"""
        card = tk.Frame(self.content, bg=COLOR_CARD_BG, highlightbackground=COLOR_BORDER, highlightthickness=1)
        card.pack(fill="x", padx=30, pady=(0, 10))

        inner = tk.Frame(card, bg=COLOR_CARD_BG)
        inner.pack(fill="x", padx=20, pady=14)

        tk.Label(
            inner, text=f"{rank}위  🏪 {store.get('place_name', '이름 없음')}",
            font=FONT_LABEL, bg=COLOR_CARD_BG, fg=COLOR_TEXT
        ).pack(anchor="w")

        address = store.get("road_address_name") or store.get("address_name", "")
        if address:
            tk.Label(
                inner, text=f"📌 {address}", font=FONT_SMALL,
                bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, anchor="w"
            ).pack(anchor="w", pady=(6, 0))

        info_parts = []
        if store.get("distance_display"):
            info_parts.append(f"🚶 {store['distance_display']}")
        if store.get("rating"):
            info_parts.append(f"⭐ {store['rating']:.1f}")
        if store.get("review_count"):
            info_parts.append(f"리뷰 {store['review_count']:,}개")
        if info_parts:
            tk.Label(
                inner, text="   |   ".join(info_parts), font=FONT_SMALL,
                bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, anchor="w"
            ).pack(anchor="w", pady=(4, 0))

        reasons = store.get("recommendation_reasons", [])
        if reasons:
            for reason in reasons:
                tk.Label(
                    inner, text=f"   {reason}", font=FONT_SMALL,
                    bg=COLOR_CARD_BG, fg=COLOR_TEXT_MUTED, anchor="w"
                ).pack(anchor="w", pady=(6 if reason == reasons[0] else 0, 0))

        map_url = store.get("place_url") or store.get("map_url")
        if map_url:
            link = tk.Label(
                inner, text="🗺  카카오맵에서 보기", font=FONT_SMALL,
                bg=COLOR_CARD_BG, fg=COLOR_PRIMARY, cursor="hand2", anchor="w"
            )
            link.pack(anchor="w", pady=(8, 0))
            link.bind("<Button-1>", lambda e, url=map_url: self._open_url(url))

    def _open_url(self, url: str):
        """음식점 카드의 지도 링크 클릭 시 기본 브라우저로 열기"""
        import webbrowser
        webbrowser.open(url)

    # ───────────────────────────────────────────
    # 하단 액션 버튼 (다른 메뉴 / 처음부터 / 종료)
    # ───────────────────────────────────────────

    def _render_action_buttons(self, found_result: bool):
        """
        CLI의 ask_retry_recommendation()에 대응.
        세 가지 행동을 버튼으로 제공: 다른 메뉴 추천, 처음부터 다시, 종료
        """
        action_row = tk.Frame(self.content, bg=COLOR_BG)
        action_row.pack(fill="x", padx=30, pady=(10, 30))

        if found_result:
            retry_same_btn = tk.Button(
                action_row, text="🔄 다른 메뉴로 다시 추천받기", font=FONT_BUTTON,
                command=self._handle_retry_same, bg=COLOR_PRIMARY, fg="white",
                activebackground=COLOR_PRIMARY_DARK, relief="flat", padx=16, pady=10, cursor="hand2"
            )
            retry_same_btn.pack(side="left", padx=(0, 10))

        retry_new_btn = tk.Button(
            action_row, text="↩ 처음부터 다시 입력하기", font=FONT_BUTTON,
            command=self._handle_retry_new, bg=COLOR_CARD_BG, fg=COLOR_TEXT,
            relief="flat", padx=16, pady=10, cursor="hand2",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        retry_new_btn.pack(side="left", padx=(0, 10))

        quit_btn = tk.Button(
            action_row, text="종료", font=FONT_BUTTON,
            command=self.app.quit_app, bg=COLOR_BG, fg=COLOR_TEXT_MUTED,
            relief="flat", padx=16, pady=10, cursor="hand2",
            highlightbackground=COLOR_BORDER, highlightthickness=1
        )
        quit_btn.pack(side="left")

    def _handle_retry_same(self):
        """'다른 메뉴로 다시 추천받기': 조건은 유지, shown_menu_ids로 중복만 회피"""
        self._show_loading_state()
        thread = threading.Thread(target=self._run_recommendation_in_background, daemon=True)
        thread.start()

    def _handle_retry_new(self):
        """'처음부터 다시 입력하기': 모든 상태를 초기화하고 1단계로 이동"""
        self.app.state.reset()
        self.app.go_to_step(0)
