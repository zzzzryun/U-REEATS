"""
main.py
========
U-RE EATS 앱의 진입점(entry point)

실행 흐름:
1. DB 초기화 확인
2. 웰컴 배너 출력
3. 사용자 입력 수집
4. 메뉴 추천
5. 음식점 검색 및 랭킹
6. 결과 출력 및 이력 저장
7. 재추천 또는 종료
"""

import os
import sys
import logging

# 프로젝트 루트를 경로에 추가 (어느 위치에서 실행해도 동작하도록)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.schema import create_database, insert_initial_data
from database.connection import check_database_exists
from modules.user_input import collect_all_user_input
from modules.menu_recommendation import recommend_menu
from modules.restaurant_search import get_restaurant_recommendation
from modules.output import (
    display_welcome_banner,
    display_recommended_menu,
    display_recommended_store,
    display_recommendation_summary,
    display_no_result_message,
    save_recommendation_history,
    ask_retry_recommendation,
    reset_user_session,
)
from utils.helpers import setup_logging, print_header, print_warning, print_info

logger = setup_logging("main")


def initialize_app():
    """
    앱 시작 전 DB 존재 여부를 확인하고 없으면 자동 생성
    """
    if not check_database_exists():
        print_info("처음 실행을 감지했습니다. 데이터베이스를 초기화합니다...")
        create_database()
        insert_initial_data()
        print_info("초기화 완료!\n")


def run_recommendation_flow(
    session_id: str,
    user_conditions: dict = None,
    shown_menu_ids: set = None
) -> tuple[str, dict, set]:
    """
    추천 흐름을 한 사이클 실행하는 함수

    Args:
        session_id: 현재 세션 ID
        user_conditions: 이미 수집된 조건 (None이면 새로 수집)
        shown_menu_ids: 이번 세션에서 이미 1순위로 보여준 menu_id 집합
            ('다른 메뉴로 다시 추천받기'를 눌렀을 때 같은 메뉴가
             또 1순위로 나오지 않도록 점수 정렬에서 뒤로 미루는 데 사용)

    Returns:
        tuple[str, dict, set]:
            - 다음 행동 ('retry_same' / 'retry_new' / 'quit')
            - 이번 사이클에서 실제로 사용된 user_conditions
            - 누적된 shown_menu_ids (이번에 보여준 메뉴까지 포함)
    """
    shown_menu_ids = set(shown_menu_ids) if shown_menu_ids else set()

    # ── 1. 사용자 입력 수집 ───────────────────────
    if user_conditions is None:
        user_conditions = collect_all_user_input()
        shown_menu_ids = set()  # 조건이 새로 바뀌었으니 이전 기록은 초기화

    # ── 2. 메뉴 추천 ─────────────────────────────
    print_header("🔍  메뉴 분석 중...")
    recommended_menus, allergy_warnings = recommend_menu(
        user_conditions, top_n=3, exclude_menu_ids=shown_menu_ids
    )

    if not recommended_menus:
        display_no_result_message(user_conditions)
        return ask_retry_recommendation(), user_conditions, shown_menu_ids

    # ── 3. 메뉴 결과 출력 ─────────────────────────
    display_recommended_menu(recommended_menus, allergy_warnings)

    # ── 4. 1순위 메뉴 기준으로 음식점 검색 ──────────
    top_menu = recommended_menus[0]
    shown_menu_ids.add(top_menu["menu_id"])  # 이번에 보여준 1순위 메뉴를 기록

    print_header(f"📍  '{top_menu['menu_name']}' 주변 음식점 검색 중...")

    recommended_stores = get_restaurant_recommendation(top_menu, user_conditions)

    # ── 5. 음식점 결과 출력 ───────────────────────
    display_recommended_store(recommended_stores)

    # ── 6. 요약 출력 ─────────────────────────────
    display_recommendation_summary(top_menu, recommended_stores, session_id)

    # ── 7. 이력 저장 ─────────────────────────────
    history_id = save_recommendation_history(
        session_id=session_id,
        user_conditions=user_conditions,
        recommended_menu=top_menu,
        recommended_stores=recommended_stores
    )
    if history_id > 0:
        print_info(f"추천 이력이 저장되었습니다. (ID: {history_id})")

    # ── 8. 다음 행동 선택 ─────────────────────────
    return ask_retry_recommendation(), user_conditions, shown_menu_ids


def main():
    """
    앱 메인 루프
    사용자가 '종료'를 선택할 때까지 추천 사이클을 반복
    """
    # 앱 초기화
    initialize_app()

    # 웰컴 배너
    display_welcome_banner()

    session_id = reset_user_session()
    user_conditions = None
    shown_menu_ids = set()
    next_action = "start"

    while True:
        try:
            if next_action in ("start", "retry_new"):
                # 조건을 새로 입력받는 경우 → 이전에 보여준 메뉴 기록도 초기화
                session_id = reset_user_session()
                next_action, user_conditions, shown_menu_ids = run_recommendation_flow(
                    session_id, user_conditions=None, shown_menu_ids=None
                )

            elif next_action == "retry_same":
                # 같은 조건으로 다른 메뉴 추천
                # (이전에 저장된 user_conditions, shown_menu_ids 그대로 재사용)
                print_info("같은 조건으로 다른 메뉴를 추천합니다...\n")
                next_action, user_conditions, shown_menu_ids = run_recommendation_flow(
                    session_id, user_conditions=user_conditions, shown_menu_ids=shown_menu_ids
                )

            elif next_action == "quit":
                print_header("👋  U-RE EATS를 이용해 주셔서 감사합니다!")
                print("  맛있는 식사 되세요 😊\n")
                break

        except KeyboardInterrupt:
            print("\n\n  프로그램을 종료합니다.")
            break
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}", exc_info=True)
            print_warning(f"오류가 발생했습니다: {e}")
            print_warning("다시 시작합니다...\n")
            next_action = "retry_new"


if __name__ == "__main__":
    main()
