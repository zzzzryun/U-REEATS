"""
tests/test_modules.py
======================
각 모듈의 핵심 함수를 검증하는 단위 테스트

실행 방법:
    프로젝트 루트에서: python -m pytest tests/ -v
    또는 직접 실행:   python tests/test_modules.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import reset_database
from database.connection import check_database_exists, execute_query
from modules.menu_recommendation import (
    load_menu_database,
    analyze_conditions,
    filter_menus,
    recommend_menu,
    remove_duplicate_menus,
)
from modules.restaurant_search import calculate_distance, rank_top_stores
from utils.helpers import (
    calculate_distance_km,
    format_price,
    format_distance,
    validate_number_input,
    parse_json_safe,
    stars_rating,
)

# ── 테스트용 공통 데이터 ──────────────────────────────────────

SAMPLE_USER_CONDITIONS = {
    "cuisine_type": "한식",
    "food_base": "밥",
    "price_range": {"label": "보통", "min": 5000, "max": 15000},
    "excluded_menus": ["삼겹살"],
    "preferred_menus": ["비빔밥"],
    "person_count": 2,
    "location": {
        "address": "서울 강남구 역삼동",
        "latitude": 37.4979,
        "longitude": 127.0276
    },
    "allergies": []
}

SAMPLE_STORES = [
    {
        "place_id": "test_001",
        "place_name": "테스트 한식당",
        "address_name": "서울 강남구 역삼동 1",
        "road_address_name": "서울 강남구 테헤란로 1",
        "phone": "02-000-0001",
        "latitude": 37.5000,
        "longitude": 127.0300,
        "category_name": "음식점 > 한식",
        "distance": "300",
        "rating": 4.3,
        "review_count": 250
    },
    {
        "place_id": "test_002",
        "place_name": "테스트 분식집",
        "address_name": "서울 강남구 역삼동 2",
        "road_address_name": "서울 강남구 테헤란로 2",
        "phone": "02-000-0002",
        "latitude": 37.5050,
        "longitude": 127.0350,
        "category_name": "음식점 > 분식",
        "distance": "800",
        "rating": 3.8,
        "review_count": 120
    },
]

# ── 테스트 함수들 ─────────────────────────────────────────────

def test_database_initialization():
    """DB 초기화 및 데이터 삽입 테스트"""
    print("\n[테스트 1] 데이터베이스 초기화")
    reset_database()
    assert check_database_exists(), "DB 파일이 생성되지 않았습니다"

    menus = execute_query("SELECT COUNT(*) as cnt FROM menu")
    count = menus[0]["cnt"]
    assert count > 0, f"메뉴 데이터가 없습니다 (count={count})"
    print(f"  ✓ DB 생성 완료, 메뉴 {count}개 삽입됨")


def test_load_menu_database():
    """메뉴 DB 로드 테스트"""
    print("\n[테스트 2] 메뉴 DB 로드")
    menus = load_menu_database()
    assert len(menus) > 0, "메뉴가 로드되지 않았습니다"
    assert "menu_name" in menus[0], "menu_name 필드가 없습니다"
    assert "allergy_info" in menus[0], "allergy_info 필드가 없습니다"
    assert isinstance(menus[0]["allergy_info"], list), "allergy_info가 리스트가 아닙니다"
    print(f"  ✓ 전체 메뉴 {len(menus)}개 로드됨")

    korean_menus = load_menu_database("한식")
    assert all(m["category"] == "한식" for m in korean_menus), "한식 필터링 오류"
    print(f"  ✓ 한식 메뉴 {len(korean_menus)}개 필터링됨")


def test_analyze_conditions():
    """조건 분석 테스트"""
    print("\n[테스트 3] 조건 분석")
    analysis = analyze_conditions(SAMPLE_USER_CONDITIONS)

    assert analysis["has_cuisine_preference"] == True
    assert analysis["has_food_base_preference"] == True
    assert analysis["is_solo"] == False
    assert analysis["is_small_group"] == True
    assert analysis["price_min"] == 5000
    assert analysis["price_max"] == 15000
    print("  ✓ 조건 분석 정상 동작")

    solo_conditions = {**SAMPLE_USER_CONDITIONS, "person_count": 1}
    solo_analysis = analyze_conditions(solo_conditions)
    assert solo_analysis["is_solo"] == True
    print("  ✓ 혼밥 감지 정상 동작")

    group_conditions = {**SAMPLE_USER_CONDITIONS, "person_count": 6}
    group_analysis = analyze_conditions(group_conditions)
    assert group_analysis["is_large_group"] == True
    print("  ✓ 단체 감지 정상 동작")


def test_filter_menus():
    """메뉴 필터링 테스트"""
    print("\n[테스트 4] 메뉴 필터링")
    menus = load_menu_database()
    analysis = analyze_conditions(SAMPLE_USER_CONDITIONS)
    filtered, warnings = filter_menus(menus, analysis)

    # 삼겹살이 제외됐는지 확인
    names = [m["menu_name"] for m in filtered]
    assert "삼겹살" not in names, "제외 메뉴(삼겹살)가 필터링되지 않았습니다"
    print(f"  ✓ 제외 메뉴 필터링 정상: {len(menus)}개 → {len(filtered)}개")

    # 알레르기 필터링 테스트
    allergy_conditions = {**SAMPLE_USER_CONDITIONS, "allergies": ["pork"]}
    allergy_analysis = analyze_conditions(allergy_conditions)
    allergy_filtered, _ = filter_menus(menus, allergy_analysis)
    for menu in allergy_filtered:
        assert "pork" not in menu["allergy_info"], f"{menu['menu_name']}에 돼지고기 알레르기 포함"
    print(f"  ✓ 알레르기(돼지고기) 필터링 정상: {len(allergy_filtered)}개 남음")


def test_recommend_menu():
    """메뉴 추천 통합 테스트"""
    print("\n[테스트 5] 메뉴 추천")
    menus, warnings = recommend_menu(SAMPLE_USER_CONDITIONS, top_n=3)

    assert len(menus) > 0, "추천 메뉴가 없습니다"
    assert len(menus) <= 3, "추천 메뉴가 3개를 초과합니다"
    assert "reasons" in menus[0], "추천 이유가 없습니다"
    assert len(menus[0]["reasons"]) > 0, "추천 이유 목록이 비어있습니다"
    print(f"  ✓ {len(menus)}개 메뉴 추천됨")
    print(f"  ✓ 1순위: '{menus[0]['menu_name']}' (점수: {menus[0].get('score', 0):.1f})")
    print(f"  ✓ 추천 이유: {menus[0]['reasons'][0]}")


def test_remove_duplicate_menus():
    """중복 메뉴 제거 테스트"""
    print("\n[테스트 6] 중복 메뉴 제거")
    duplicates = [
        {"menu_id": 1, "menu_name": "비빔밥"},
        {"menu_id": 2, "menu_name": "냉면"},
        {"menu_id": 1, "menu_name": "비빔밥"},  # 중복
    ]
    result = remove_duplicate_menus(duplicates)
    assert len(result) == 2, f"중복 제거 실패: {len(result)}개 남음 (기대: 2개)"
    print("  ✓ 중복 메뉴 제거 정상 동작")


def test_calculate_distance():
    """거리 계산 테스트"""
    print("\n[테스트 7] 거리 계산")
    # 서울 강남역 ↔ 서울 시청 (약 8~10km)
    dist = calculate_distance_km(37.4979, 127.0276, 37.5665, 126.9780)
    assert 7.0 < dist < 11.0, f"거리 계산 오류: {dist}km (기대: 7~11km)"
    print(f"  ✓ 강남역↔시청: {dist:.2f}km (정상 범위)")

    # 같은 위치 → 0km
    zero_dist = calculate_distance_km(37.4979, 127.0276, 37.4979, 127.0276)
    assert zero_dist == 0.0, f"같은 위치 거리 오류: {zero_dist}"
    print(f"  ✓ 동일 위치 거리: {zero_dist}km")


def test_rank_stores():
    """음식점 랭킹 테스트"""
    print("\n[테스트 8] 음식점 랭킹")
    location = SAMPLE_USER_CONDITIONS["location"]
    ranked = rank_top_stores(SAMPLE_STORES, location, SAMPLE_USER_CONDITIONS, top_n=2)

    assert len(ranked) <= 2, "랭킹 결과가 top_n을 초과합니다"
    assert "ranking_score" in ranked[0], "ranking_score 필드가 없습니다"
    assert "distance_km" in ranked[0], "distance_km 필드가 없습니다"
    assert ranked[0]["ranking_score"] >= ranked[-1]["ranking_score"], "내림차순 정렬 오류"
    print(f"  ✓ 1위: '{ranked[0]['place_name']}' (점수: {ranked[0]['ranking_score']:.1f})")


def test_helpers():
    """유틸리티 함수 테스트"""
    print("\n[테스트 9] 유틸리티 함수")

    assert format_price(12000) == "12,000원"
    assert format_price(0) == "0원"
    print("  ✓ format_price 정상")

    assert format_distance(0.3) == "300m"
    assert format_distance(1.5) == "1.5km"
    print("  ✓ format_distance 정상")

    assert validate_number_input("3", 1, 10) == 3
    assert validate_number_input("0", 1, 10) is None
    assert validate_number_input("abc", 1, 10) is None
    print("  ✓ validate_number_input 정상")

    assert parse_json_safe('["gluten","dairy"]') == ["gluten", "dairy"]
    assert parse_json_safe("broken json", default=[]) == []
    assert parse_json_safe(None, default=[]) == []
    print("  ✓ parse_json_safe 정상")

    assert stars_rating(4.0).startswith("★★★★☆")
    assert stars_rating(5.0).startswith("★★★★★")
    print("  ✓ stars_rating 정상")


# ── 테스트 실행기 ─────────────────────────────────────────────

def run_all_tests():
    tests = [
        test_database_initialization,
        test_load_menu_database,
        test_analyze_conditions,
        test_filter_menus,
        test_recommend_menu,
        test_remove_duplicate_menus,
        test_calculate_distance,
        test_rank_stores,
        test_helpers,
    ]

    print("=" * 50)
    print("  U-RE EATS 단위 테스트 시작")
    print("=" * 50)

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ 실패: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ 오류: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"  결과: {passed}개 통과 / {failed}개 실패")
    print("=" * 50)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
