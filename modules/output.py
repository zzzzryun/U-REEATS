"""
modules/output.py
==================
추천 결과 출력 및 이력 관리 모듈

담당 기능:
1. 추천 메뉴 콘솔 출력 (포맷팅)
2. 추천 음식점 상세 출력
3. 카카오맵 링크 표시
4. 추천 이력 데이터베이스 저장
5. 재추천 / 새 검색 인터랙션
6. 세션 리셋
"""

import os
import sys
import json
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    APP_NAME, APP_VERSION, SEPARATOR_LINE, THIN_SEPARATOR,
    ALLERGY_DISPLAY_NAMES
)
from database.connection import execute_write
from utils.helpers import (
    print_header, print_subheader, print_info, print_warning,
    print_success, print_error, stars_rating, format_price_range,
    format_distance, generate_session_id, get_current_timestamp
)

logger = logging.getLogger(__name__)


def display_recommended_menu(
    recommended_menus: list[dict],
    allergy_warnings: list[str] = None
):
    """
    추천된 메뉴 목록을 출력하는 함수

    출력 형식:
    - 메뉴 이름 및 카테고리
    - 가격 범위
    - 추천 이유 (개인화된 설명)
    - 영양 정보 (있을 경우)
    - 알레르기 경고 (있을 경우)

    Args:
        recommended_menus: 추천 메뉴 딕셔너리 목록
        allergy_warnings: 알레르기 경고가 필요한 메뉴 목록
    """
    print_header("🍽️  추천 메뉴")

    if not recommended_menus:
        print_error("조건에 맞는 메뉴를 찾을 수 없습니다.")
        print_info("조건을 조금 완화하여 다시 검색해보세요.")
        return

    for i, menu in enumerate(recommended_menus, start=1):
        print(f"\n  {'━' * 50}")
        print(f"  {i}위 추천 메뉴")
        print(f"  {'━' * 50}")

        # 메뉴 기본 정보
        print(f"\n  🍴  {menu['menu_name']}")
        print(f"      카테고리: {menu.get('category', '-')}")
        print(f"      가격:     {format_price_range(menu.get('price_range_min', 0), menu.get('price_range_max', 0))}")

        # 메뉴 설명
        if menu.get("description"):
            print(f"\n      📝 {menu['description']}")

        # 영양 정보 (있을 경우)
        nutrition = menu.get("nutrition_info", {})
        if nutrition:
            print(f"\n      🥗 영양 정보 (1인분 기준)")
            if "calories" in nutrition:
                print(f"         칼로리: {nutrition['calories']}kcal", end="")
            if "protein" in nutrition:
                print(f"  |  단백질: {nutrition['protein']}g", end="")
            if "carbs" in nutrition:
                print(f"  |  탄수화물: {nutrition['carbs']}g", end="")
            print()

        # 특성 정보
        features = []
        if menu.get("is_solo_friendly"):
            features.append("혼밥 가능")
        if menu.get("is_group_friendly"):
            features.append("단체 가능")
        if menu.get("is_rice_based"):
            features.append("밥 종류")
        if menu.get("is_noodle_based"):
            features.append("면 종류")
        if features:
            print(f"\n      🏷️  특징: {' | '.join(features)}")

        # 추천 이유 (핵심 기능)
        reasons = menu.get("reasons", [])
        if reasons:
            print(f"\n      💡 추천 이유:")
            for reason in reasons:
                print(f"         {reason}")

    # 알레르기 경고 출력
    if allergy_warnings:
        print(f"\n  ⚠️  알레르기 정보 주의")
        print(f"      다음 메뉴는 알레르기 정보가 충분하지 않습니다:")
        for menu_name in allergy_warnings[:3]:  # 최대 3개만 표시
            print(f"      • {menu_name}")
        print(f"      → 주문 전 음식점에 알레르기 성분을 직접 문의하세요.")

    print()


def display_recommended_store(stores: list[dict], rank: int = 1):
    """
    추천 음식점 목록을 출력하는 함수

    Args:
        stores: 추천 음식점 딕셔너리 목록
        rank: 시작 순위 (기본값 1)
    """
    print_header("📍  추천 음식점 TOP 3")

    if not stores:
        print_error("주변에서 음식점을 찾을 수 없습니다.")
        print_info("검색 반경을 넓히거나 다른 메뉴로 다시 시도해보세요.")
        return

    for i, store in enumerate(stores, start=rank):
        print(f"\n  {'━' * 50}")
        print(f"  {i}위 추천 음식점")
        print(f"  {'━' * 50}")

        display_store_details(store, show_rank=False)


def display_store_details(store: dict, show_rank: bool = True):
    """
    음식점 상세 정보를 출력하는 함수

    Args:
        store: 음식점 정보 딕셔너리
        show_rank: 순위 표시 여부
    """
    print(f"\n  🏪  {store.get('place_name', '이름 없음')}")

    # 위치 정보
    address = store.get("road_address_name") or store.get("address_name") or store.get("full_address", "")
    if address:
        print(f"      📌 주소: {address}")

    # 전화번호
    if store.get("phone"):
        print(f"      📞 전화: {store['phone']}")

    # 거리
    if store.get("distance_display"):
        print(f"      🚶 거리: {store['distance_display']}")
    elif store.get("distance_km"):
        print(f"      🚶 거리: {format_distance(store['distance_km'])}")

    # 평점 및 리뷰
    rating = store.get("rating", 0)
    review_count = store.get("review_count", 0)
    if rating:
        print(f"      ⭐ 평점: {stars_rating(rating)}", end="")
        if review_count:
            print(f"  |  리뷰: {review_count:,}개")
        else:
            print()

    # 카테고리
    category = store.get("main_category") or store.get("category_name", "")
    if category:
        print(f"      🏷️  카테고리: {category}")

    # 랭킹 점수 (디버그 모드에서 유용)
    if os.environ.get("DEBUG"):
        score = store.get("ranking_score")
        if score:
            print(f"      📊 랭킹 점수: {score:.1f}/100")

    # 추천 이유
    reasons = store.get("recommendation_reasons", [])
    if reasons:
        print(f"\n      💡 추천 이유:")
        for reason in reasons:
            print(f"         {reason}")

    # 지도 링크
    display_map_location(store)


def display_map_location(store: dict):
    """
    카카오맵 링크를 출력하는 함수

    Args:
        store: 음식점 정보 딕셔너리 (map_url 또는 place_url 필드)
    """
    place_url = store.get("place_url") or store.get("kakao_map_url")
    direct_url = store.get("direct_map_url") or store.get("map_url")

    print(f"\n      🗺️  지도 보기:")
    if place_url and "mock" not in str(place_url):
        print(f"         카카오맵: {place_url}")
    elif direct_url and "mock" not in str(direct_url):
        print(f"         지도 링크: {direct_url}")
    else:
        # 좌표 기반 링크 생성
        lat = store.get("latitude")
        lon = store.get("longitude")
        name = store.get("place_name", "음식점")
        if lat and lon:
            kakao_link = f"https://map.kakao.com/link/map/{name},{lat},{lon}"
            print(f"         카카오맵: {kakao_link}")
        else:
            print(f"         지도 정보를 가져올 수 없습니다.")


def save_recommendation_history(
    session_id: str,
    user_conditions: dict,
    recommended_menu: dict,
    recommended_stores: list[dict]
) -> int:
    """
    추천 이력을 데이터베이스에 저장하는 함수

    저장 데이터:
    - 세션 ID (사용자 세션 추적)
    - 사용자 입력 전체 (JSON)
    - 추천된 메뉴
    - 추천 이유
    - 추천된 음식점 목록 (스냅샷)
    - 검색 위치

    Args:
        session_id: 현재 세션 ID
        user_conditions: 사용자 입력 조건
        recommended_menu: 추천된 메뉴
        recommended_stores: 추천된 음식점 목록

    Returns:
        int: 저장된 이력의 ID (실패 시 -1)
    """
    try:
        # 저장용 데이터 준비 (민감 정보 제거)
        conditions_snapshot = {
            "cuisine_type":   user_conditions.get("cuisine_type"),
            "food_base":      user_conditions.get("food_base"),
            "price_range":    user_conditions.get("price_range", {}),
            "excluded_menus": user_conditions.get("excluded_menus", []),
            "person_count":   user_conditions.get("person_count"),
            "allergies":      user_conditions.get("allergies", []),
            "location_address": user_conditions.get("location", {}).get("address")
        }

        # 음식점 스냅샷 (핵심 정보만 저장)
        stores_snapshot = [
            {
                "place_id": s.get("place_id"),
                "place_name": s.get("place_name"),
                "address": s.get("address_name"),
                "distance_km": s.get("distance_km"),
                "rating": s.get("rating"),
                "ranking_score": s.get("ranking_score")
            }
            for s in recommended_stores[:3]
        ]

        history_id = execute_write("""
            INSERT INTO recommendation_history
            (session_id, user_conditions, recommended_menu_id,
             recommended_menu, recommendation_reasons,
             recommended_stores, search_location)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            json.dumps(conditions_snapshot, ensure_ascii=False),
            recommended_menu.get("menu_id"),
            recommended_menu.get("menu_name", ""),
            json.dumps(recommended_menu.get("reasons", []), ensure_ascii=False),
            json.dumps(stores_snapshot, ensure_ascii=False),
            user_conditions.get("location", {}).get("address", "")
        ))

        logger.info(f"추천 이력 저장 완료: history_id={history_id}")
        return history_id

    except Exception as e:
        logger.error(f"추천 이력 저장 실패: {e}")
        return -1


def ask_retry_recommendation() -> str:
    """
    추천 후 사용자에게 다음 행동을 묻는 함수

    Returns:
        str: 사용자 선택
            'retry_same'    - 같은 조건으로 다른 추천
            'retry_new'     - 조건을 바꿔서 재시작
            'quit'          - 종료
    """
    print_subheader("🔄  다음 행동 선택")
    print("  추천이 마음에 드셨나요?\n")
    print("  [1] 다른 메뉴로 다시 추천받기 (조건 유지)")
    print("  [2] 처음부터 다시 조건 입력하기")
    print("  [3] 종료\n")

    while True:
        choice = input("  선택: ").strip()
        if choice == "1":
            return "retry_same"
        elif choice == "2":
            return "retry_new"
        elif choice == "3":
            return "quit"
        else:
            print_warning("1, 2, 3 중 하나를 입력해주세요.")


def reset_user_session() -> str:
    """
    새 사용자 세션을 시작하는 함수

    Returns:
        str: 새로 생성된 세션 ID
    """
    new_session_id = generate_session_id()
    logger.info(f"새 세션 시작: {new_session_id}")
    return new_session_id


def display_welcome_banner():
    """앱 시작 시 웰컴 배너를 출력"""
    print("\n" + SEPARATOR_LINE)
    print(f"""
  ██╗   ██╗      ██████╗ ███████╗    ███████╗ █████╗ ████████╗███████╗
  ██║   ██║      ██╔══██╗██╔════╝    ██╔════╝██╔══██╗╚══██╔══╝██╔════╝
  ██║   ██║ ████╗██████╔╝█████╗      █████╗  ███████║   ██║   ███████╗
  ██║   ██║╚════╝██╔══██╗██╔══╝      ██╔══╝  ██╔══██║   ██║   ╚════██║
  ╚██████╔╝      ██║  ██║███████╗    ███████╗██║  ██║   ██║   ███████║
   ╚═════╝       ╚═╝  ╚═╝╚══════╝    ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
    """)
    print(f"  🍴  {APP_NAME} v{APP_VERSION}")
    print(f"  개인 맞춤형 메뉴 & 음식점 추천 시스템")
    print(f"  메뉴 고민은 그만! 지금 바로 추천받아보세요 ✨")
    print(SEPARATOR_LINE)


def display_recommendation_summary(
    menu: dict,
    stores: list[dict],
    session_id: str
):
    """
    최종 추천 결과를 요약하여 출력

    Args:
        menu: 추천된 메뉴
        stores: 추천된 음식점 목록
        session_id: 현재 세션 ID
    """
    print_header("✅  최종 추천 결과 요약")

    print(f"\n  📋 세션 ID: {session_id[:8]}...")
    print(f"  🕐 추천 시각: {get_current_timestamp()}")

    print(f"\n  🍴 추천 메뉴:  {menu.get('menu_name', '-')}")
    print(f"     카테고리:  {menu.get('category', '-')}")
    print(f"     예상 가격: {format_price_range(menu.get('price_range_min', 0), menu.get('price_range_max', 0))}")

    if stores:
        print(f"\n  🏪 추천 음식점 (거리 가중 랭킹 기준):")
        for i, store in enumerate(stores, 1):
            name = store.get("place_name", "이름 없음")
            dist = store.get("distance_display", "")
            rating = store.get("rating", 0)
            print(f"     {i}. {name} ({dist}) - 평점 {rating:.1f}★")
    else:
        print(f"\n  ⚠️  주변 음식점 정보를 가져오지 못했습니다.")
        print(f"      직접 '{menu.get('menu_name')}' 키워드로 카카오맵에서 검색해보세요!")

    print()


def display_no_result_message(user_conditions: dict):
    """
    추천 결과가 없을 때 출력하는 함수

    Args:
        user_conditions: 사용자 입력 조건 (힌트 제공용)
    """
    print_header("😅  추천 결과 없음")
    print_error("입력하신 조건에 맞는 메뉴를 찾지 못했습니다.")
    print()
    print("  💡 다음 방법을 시도해보세요:")
    print("     1. 가격대 범위를 넓혀보세요")
    print("     2. 음식 종류를 '전체'로 변경해보세요")
    print("     3. 제외 메뉴 수를 줄여보세요")
    print("     4. 밥/면 선호도를 '상관없음'으로 변경해보세요")

    excluded = user_conditions.get("excluded_menus", [])
    if len(excluded) > 3:
        print(f"\n  ⚠️  제외 메뉴가 {len(excluded)}개로 많습니다. 일부를 해제해보세요.")

    allergies = user_conditions.get("allergies", [])
    if allergies:
        allergy_names = [ALLERGY_DISPLAY_NAMES.get(a, a) for a in allergies]
        print(f"\n  ⚠️  알레르기 제한: {', '.join(allergy_names)}")
        print(f"      이로 인해 일부 메뉴가 제외되었습니다.")
    print()
