"""
modules/user_input.py
=====================
사용자 입력을 수집하고 검증하는 모듈

설계 원칙:
- 각 입력 항목을 독립 함수로 분리 (단일 책임 원칙)
- 잘못된 입력에 대한 친절한 재입력 안내
- 입력값을 딕셔너리로 통합하여 반환
- 선택적 입력 항목은 건너뛰기(skip) 허용
"""

import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    CUISINE_TYPES, PRICE_RANGES, ALLERGY_LIST,
    ALLERGY_DISPLAY_NAMES, SEPARATOR_LINE
)
from utils.helpers import (
    print_header, print_subheader, print_warning,
    print_info, validate_number_input
)


def select_cuisine_type() -> str:
    """
    음식 종류를 선택받는 함수

    Returns:
        str: 선택된 음식 카테고리 이름 (e.g., '한식', '양식')
    """
    print_subheader("🍽️  음식 종류 선택")
    print("  어떤 종류의 음식이 드시고 싶으신가요?\n")

    for key, name in CUISINE_TYPES.items():
        print(f"  [{key}] {name}")

    print(f"  [0] 상관없음 (전체)\n")

    while True:
        choice = input("  선택 (숫자 입력): ").strip()

        if choice == "0":
            print_info("전체 음식 종류로 검색합니다.")
            return "전체"
        elif choice in CUISINE_TYPES:
            selected = CUISINE_TYPES[choice]
            print_info(f"선택됨: {selected}")
            return selected
        else:
            print_warning(f"0~{len(CUISINE_TYPES)} 사이의 숫자를 입력해주세요.")


def select_noodle_or_rice() -> Optional[str]:
    """
    밥 또는 면 선호도를 선택받는 함수

    Returns:
        Optional[str]: '밥', '면', 또는 None (상관없음)
    """
    print_subheader("🍚  밥/면 선호도")
    print("  밥과 면 중 어떤 것을 선호하시나요?\n")
    print("  [1] 밥 (볶음밥, 덮밥, 한정식 등)")
    print("  [2] 면 (파스타, 라멘, 국수 등)")
    print("  [0] 상관없음\n")

    while True:
        choice = input("  선택: ").strip()
        if choice == "1":
            print_info("밥 종류 메뉴를 우선적으로 추천합니다.")
            return "밥"
        elif choice == "2":
            print_info("면 종류 메뉴를 우선적으로 추천합니다.")
            return "면"
        elif choice == "0":
            print_info("밥/면 구분 없이 추천합니다.")
            return None
        else:
            print_warning("0, 1, 2 중 하나를 입력해주세요.")


def input_price_range() -> dict:
    """
    가격대를 입력받는 함수

    Returns:
        dict: {'label': str, 'min': int, 'max': int}
    """
    print_subheader("💰  가격대 선택")
    print("  예산은 어느 정도 생각하고 계신가요? (1인 기준)\n")

    for key, info in PRICE_RANGES.items():
        print(f"  [{key}] {info['label']}")

    print(f"  [0] 상관없음\n")

    while True:
        choice = input("  선택: ").strip()
        if choice == "0":
            print_info("가격대 제한 없이 추천합니다.")
            return {"label": "전체", "min": 0, "max": 999999}
        elif choice in PRICE_RANGES:
            selected = PRICE_RANGES[choice]
            print_info(f"선택됨: {selected['label']}")
            return selected
        else:
            print_warning(f"0~{len(PRICE_RANGES)} 사이의 숫자를 입력해주세요.")


def input_excluded_menu() -> list[str]:
    """
    제외할 메뉴를 입력받는 함수

    Returns:
        list[str]: 제외 메뉴 이름 목록
    """
    print_subheader("🚫  제외 메뉴 입력")
    print("  먹기 싫거나 못 먹는 메뉴를 입력해주세요.")
    print("  (여러 개일 경우 쉼표로 구분, 없으면 Enter)\n")
    print("  예시: 삼겹살, 초밥, 파스타\n")

    user_input = input("  제외 메뉴: ").strip()

    if not user_input:
        print_info("제외 메뉴 없음")
        return []

    # 쉼표로 분리 후 공백 제거
    excluded = [menu.strip() for menu in user_input.split(",") if menu.strip()]
    print_info(f"제외 메뉴 설정됨: {', '.join(excluded)}")
    return excluded


def input_preferred_menu() -> list[str]:
    """
    선호 메뉴를 입력받는 함수

    Returns:
        list[str]: 선호 메뉴 이름 목록
    """
    print_subheader("❤️  선호 메뉴 입력")
    print("  특별히 먹고 싶은 메뉴가 있으신가요?")
    print("  (여러 개일 경우 쉼표로 구분, 없으면 Enter)\n")
    print("  예시: 비빔밥, 라멘, 스테이크\n")

    user_input = input("  선호 메뉴: ").strip()

    if not user_input:
        print_info("선호 메뉴 없음")
        return []

    preferred = [menu.strip() for menu in user_input.split(",") if menu.strip()]
    print_info(f"선호 메뉴 설정됨: {', '.join(preferred)}")
    return preferred


def input_person_count() -> int:
    """
    인원 수를 입력받는 함수

    Returns:
        int: 식사 인원 수 (1 이상)
    """
    print_subheader("👥  인원 수 입력")
    print("  몇 명이서 드실 예정인가요?\n")

    while True:
        user_input = input("  인원 수 (숫자): ").strip()
        count = validate_number_input(user_input, min_val=1, max_val=100)

        if count is not None:
            if count == 1:
                print_info("혼밥 모드! 혼자 먹기 좋은 음식점을 우선 추천합니다.")
            elif count <= 4:
                print_info(f"{count}명 소규모 식사")
            else:
                print_info(f"{count}명 단체 식사! 단체석 있는 음식점을 우선 추천합니다.")
            return count
        else:
            print_warning("1 이상의 숫자를 입력해주세요. (최대 100명)")


def select_location() -> dict:
    """
    현재 위치 또는 원하는 위치를 입력받는 함수

    Returns:
        dict: {'address': str, 'latitude': float, 'longitude': float}
    """
    print_subheader("📍  위치 입력")
    print("  어느 지역에서 식사하실 예정인가요?\n")
    print("  [1] 직접 주소/지역명 입력")
    print("  [2] 내 위치 (자동 감지 - 브라우저 권한 필요)\n")

    choice = input("  선택: ").strip()

    if choice == "1":
        print("\n  예시: 서울 강남구 역삼동, 홍대입구역, 신촌 연세대 앞")
        address = input("  주소 또는 지역명: ").strip()
        if not address:
            print_warning("주소를 입력하지 않아 기본 위치를 사용합니다.")
            return _get_default_location()

        # 카카오 API로 주소 → 좌표 변환
        from utils.kakao_api import geocode_address
        coords = geocode_address(address)
        if coords:
            print_info(f"위치 확인됨: {coords['address']}")
            return coords
        else:
            print_warning("주소를 찾을 수 없어 기본 위치를 사용합니다.")
            return _get_default_location()

    elif choice == "2":
        return _get_current_location_with_fallback()

    else:
        print_warning("올바른 선택이 아니어서 내 위치 자동 감지를 시도합니다.")
        return _get_current_location_with_fallback()


def _get_current_location_with_fallback() -> dict:
    """
    내 위치(자동 감지)를 시도하는 함수 - 3단계 폴백 구조

    감지 우선순위:
    1순위. 브라우저 위치 권한 (Wi-Fi 기반, 오차 10~50m) - 가장 정밀하지만 사용자 클릭 필요
    2순위. IP 기반 추정 (오차 수 km, 시/구 단위) - 자동이지만 부정확
    3순위. 기본 위치 (강남역) - 둘 다 실패했을 때 최후 수단

    각 단계가 실패해도 프로그램이 멈추지 않고 다음 단계로 안전하게 넘어감

    Returns:
        dict: {'address': str, 'latitude': float, 'longitude': float}
    """
    # ── 1순위: 브라우저 정밀 위치 감지 ──────────────
    print_info("브라우저를 통해 정밀 위치를 확인합니다. 잠시만 기다려주세요...")
    print_info("브라우저 창에서 위치 권한 팝업이 뜨면 '허용'을 눌러주세요.\n")

    from utils.browser_location import get_precise_location_via_browser
    precise_location = get_precise_location_via_browser(timeout_seconds=30)

    if precise_location:
        # 좌표만으로는 사람이 읽기 어려우니 주소로 변환 시도
        from utils.kakao_api import reverse_geocode
        address_info = reverse_geocode(
            precise_location["latitude"],
            precise_location["longitude"]
        )
        address = address_info["address"] if address_info else "현재 위치 (정밀 감지)"

        print_info(f"감지된 위치: {address}")
        return {
            "address": address,
            "latitude": precise_location["latitude"],
            "longitude": precise_location["longitude"]
        }

    # ── 2순위: IP 기반 추정으로 폴백 ─────────────────
    print_warning("정밀 위치 감지에 실패하여 IP 기반 추정으로 전환합니다.")

    from utils.kakao_api import get_current_location_by_ip
    ip_location = get_current_location_by_ip()

    if ip_location:
        print_info(f"감지된 위치: {ip_location['address']}")
        print_warning("IP 기반 위치는 시/구 단위로 추정되며 실제 위치와 차이가 있을 수 있습니다.")
        return ip_location

    # ── 3순위: 기본 위치로 최종 대체 ─────────────────
    print_warning("위치 자동 감지에 모두 실패하여 기본 위치를 사용합니다.")
    return _get_default_location()


def _get_default_location() -> dict:
    """기본 위치 (서울 강남역) 반환"""
    location = {
        "address": "서울특별시 강남구 강남대로 396 (강남역)",
        "latitude": 37.4979,
        "longitude": 127.0276
    }
    print_info(f"기본 위치 사용: {location['address']}")
    return location


def input_additional_profile() -> dict:
    """
    추가 사용자 프로필 정보를 입력받는 함수
    (현재: 알레르기 정보, 향후: 식이 제한, 종교적 제약 등으로 확장 예정)

    Returns:
        dict: {'allergies': list[str]}
    """
    return {
        "allergies": input_allergy_info()
    }


def input_allergy_info() -> list[str]:
    """
    알레르기 정보를 입력받는 함수

    알레르기 정보 처리 원칙:
    - 정보가 없으면 경고 메시지 표시 (해당 음식점 추천 우선순위 하향)
    - 알레르기 성분 포함 메뉴는 추천에서 제외 또는 경고 표시

    Returns:
        list[str]: 알레르기 성분 코드 목록 (e.g., ['gluten', 'dairy'])
    """
    print_subheader("⚠️  알레르기 정보 입력")
    print("  알레르기가 있으신가요? 해당 성분이 포함된 메뉴는 제외됩니다.\n")

    for i, allergy_code in enumerate(ALLERGY_LIST, start=1):
        display_name = ALLERGY_DISPLAY_NAMES.get(allergy_code, allergy_code)
        print(f"  [{i:2d}] {display_name}")

    print("\n  [0] 알레르기 없음 / 건너뛰기")
    print("\n  선택 방법: 번호를 띄어쓰기로 구분 (예: 1 3 5)")
    print("             또는 '없음'을 입력하여 건너뛰기\n")

    user_input = input("  알레르기 번호: ").strip()

    if not user_input or user_input in ["0", "없음", "skip"]:
        print_warning("알레르기 정보를 입력하지 않았습니다.")
        print_warning("→ 알레르기 성분 확인이 불가능한 메뉴의 경우 경고가 표시됩니다.")
        return []

    # 번호를 알레르기 코드로 변환
    selected_allergies = []
    for num_str in user_input.split():
        num = validate_number_input(num_str, min_val=1, max_val=len(ALLERGY_LIST))
        if num is not None:
            allergy_code = ALLERGY_LIST[num - 1]
            if allergy_code not in selected_allergies:
                selected_allergies.append(allergy_code)

    if selected_allergies:
        display_names = [ALLERGY_DISPLAY_NAMES.get(a, a) for a in selected_allergies]
        print_info(f"알레르기 정보 설정됨: {', '.join(display_names)}")
        print_info("  → 해당 성분이 포함된 메뉴는 자동으로 제외됩니다.")
    else:
        print_warning("유효한 번호가 없어 알레르기 정보를 설정하지 않았습니다.")

    return selected_allergies


def validate_user_input(user_conditions: dict) -> tuple[bool, list[str]]:
    """
    수집된 사용자 입력값 전체를 검증하는 함수

    Args:
        user_conditions: 수집된 전체 사용자 조건 딕셔너리

    Returns:
        tuple[bool, list[str]]:
            - bool: 유효성 검사 통과 여부
            - list[str]: 오류 메시지 목록 (빈 리스트면 정상)
    """
    errors = []

    # 필수 항목 검증
    if not user_conditions.get("location"):
        errors.append("위치 정보가 없습니다.")

    person_count = user_conditions.get("person_count", 0)
    if not isinstance(person_count, int) or person_count < 1:
        errors.append("인원 수는 1명 이상이어야 합니다.")

    price_range = user_conditions.get("price_range", {})
    if price_range.get("min", -1) < 0 or price_range.get("max", -1) < 0:
        errors.append("가격 범위가 올바르지 않습니다.")

    if price_range.get("min", 0) > price_range.get("max", 0):
        errors.append("최소 가격이 최대 가격보다 클 수 없습니다.")

    # 알레르기 정보 부재 경고 (오류는 아님)
    if not user_conditions.get("allergies"):
        pass  # 경고는 input_allergy_info()에서 이미 출력

    is_valid = len(errors) == 0
    return is_valid, errors


def collect_all_user_input() -> dict:
    """
    모든 사용자 입력을 순서대로 수집하는 통합 함수

    Returns:
        dict: 수집된 전체 사용자 조건
            {
                'cuisine_type': str,
                'food_base': str or None,
                'price_range': dict,
                'excluded_menus': list,
                'preferred_menus': list,
                'person_count': int,
                'location': dict,
                'allergies': list
            }
    """
    print_header("🍴  U-RE EATS - 식사 조건 입력")
    print("  입력하신 조건을 바탕으로 최적의 메뉴와 음식점을 추천해드립니다.")
    print("  각 항목에서 [0] 또는 Enter를 누르면 건너뛸 수 있습니다.\n")

    user_conditions = {
        "cuisine_type":    select_cuisine_type(),
        "food_base":       select_noodle_or_rice(),
        "price_range":     input_price_range(),
        "excluded_menus":  input_excluded_menu(),
        "preferred_menus": input_preferred_menu(),
        "person_count":    input_person_count(),
        "location":        select_location(),
        **input_additional_profile()   # allergies 포함
    }

    # 최종 검증
    is_valid, errors = validate_user_input(user_conditions)
    if not is_valid:
        print("\n⚠️  입력 오류가 발견되었습니다:")
        for error in errors:
            print(f"   • {error}")
        print()

    return user_conditions
