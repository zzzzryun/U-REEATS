"""
modules/menu_recommendation.py
================================
메뉴 분석 및 추천 엔진 모듈

추천 알고리즘 흐름:
1. 데이터베이스에서 전체 메뉴 로드
2. 사용자 조건으로 1차 필터링 (하드 필터: 알레르기, 제외 메뉴)
3. 소프트 스코어링으로 2차 정렬 (선호도, 카테고리, 가격 적합도)
4. 상위 N개 추천 메뉴 선정
5. 각 메뉴별 추천 이유 생성
"""

import os
import sys
import json
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.connection import execute_query
from utils.helpers import parse_json_safe, format_price_range

logger = logging.getLogger(__name__)


def load_menu_database(category: str = None) -> list[dict]:
    """
    메뉴 데이터베이스에서 메뉴 목록을 불러오는 함수

    Args:
        category: 특정 카테고리로 필터링 (None이면 전체 조회)

    Returns:
        list[dict]: 메뉴 정보 딕셔너리 목록
    """
    if category and category != "전체":
        query = """
            SELECT
                m.menu_id,
                m.menu_name,
                fc.category_name  AS category,
                m.price_range_min,
                m.price_range_max,
                m.is_rice_based,
                m.is_noodle_based,
                m.description,
                m.allergy_info,
                m.nutrition_info,
                m.is_solo_friendly,
                m.is_group_friendly
            FROM menu m
            JOIN food_category fc ON m.category_id = fc.category_id
            WHERE m.is_active = 1 AND fc.category_name = ?
            ORDER BY m.menu_name
        """
        menus = execute_query(query, (category,))
    else:
        query = """
            SELECT
                m.menu_id,
                m.menu_name,
                fc.category_name  AS category,
                m.price_range_min,
                m.price_range_max,
                m.is_rice_based,
                m.is_noodle_based,
                m.description,
                m.allergy_info,
                m.nutrition_info,
                m.is_solo_friendly,
                m.is_group_friendly
            FROM menu m
            JOIN food_category fc ON m.category_id = fc.category_id
            WHERE m.is_active = 1
            ORDER BY fc.category_name, m.menu_name
        """
        menus = execute_query(query)

    # allergy_info와 nutrition_info JSON 파싱
    for menu in menus:
        menu["allergy_info"] = parse_json_safe(menu.get("allergy_info"), default=[])
        menu["nutrition_info"] = parse_json_safe(menu.get("nutrition_info"), default={})

    logger.info(f"메뉴 DB 로드 완료: {len(menus)}개")
    return menus


def analyze_conditions(user_conditions: dict) -> dict:
    """
    사용자 입력 조건을 분석하여 추천 전략을 수립하는 함수

    Args:
        user_conditions: 사용자 입력 딕셔너리

    Returns:
        dict: 분석된 추천 전략
            - has_cuisine_preference: 음식 종류 선호 여부
            - has_food_base_preference: 밥/면 선호 여부
            - has_menu_preference: 특정 메뉴 선호 여부
            - has_allergies: 알레르기 정보 있음 여부
            - is_solo: 혼밥 여부
            - is_group: 단체 여부 (5명 이상)
            - price_flexible: 가격 제한 없음 여부
    """
    person_count = user_conditions.get("person_count", 1)
    cuisine_type = user_conditions.get("cuisine_type", "전체")
    price_range = user_conditions.get("price_range", {})

    analysis = {
        "has_cuisine_preference": cuisine_type not in ("전체", None, ""),
        "has_food_base_preference": user_conditions.get("food_base") is not None,
        "has_menu_preference": len(user_conditions.get("preferred_menus", [])) > 0,
        "has_exclusions": len(user_conditions.get("excluded_menus", [])) > 0,
        "has_allergies": len(user_conditions.get("allergies", [])) > 0,
        "is_solo": person_count == 1,
        "is_small_group": 2 <= person_count <= 4,
        "is_large_group": person_count >= 5,
        "price_flexible": price_range.get("max", 999999) >= 999999,
        "person_count": person_count,
        "cuisine_type": cuisine_type,
        "food_base": user_conditions.get("food_base"),
        "price_min": price_range.get("min", 0),
        "price_max": price_range.get("max", 999999),
        "excluded_menus": [m.lower() for m in user_conditions.get("excluded_menus", [])],
        "preferred_menus": [m.lower() for m in user_conditions.get("preferred_menus", [])],
        "allergies": user_conditions.get("allergies", [])
    }

    logger.debug(f"조건 분석 완료: {analysis}")
    return analysis


def filter_menus(menus: list[dict], analysis: dict) -> tuple[list[dict], list[dict]]:
    """
    분석된 조건을 바탕으로 메뉴를 필터링하는 함수

    필터링 단계:
    1. 알레르기 하드 필터 (알레르기 성분 포함 메뉴 완전 제외)
    2. 제외 메뉴 필터 (사용자가 명시적으로 제외한 메뉴)
    3. 가격대 필터 (범위를 벗어난 메뉴 제외)
    4. 음식 종류 필터 (선호 카테고리 외 메뉴 제외 - 전체 선택 시 생략)

    Args:
        menus: 전체 메뉴 목록
        analysis: analyze_conditions()의 반환값

    Returns:
        tuple[list[dict], list[dict]]:
            - 통과한 메뉴 목록
            - 알레르기 경고가 있는 메뉴 목록 (통과했지만 주의 필요)
    """
    passed_menus = []
    allergy_warning_menus = []

    user_allergies = set(analysis.get("allergies", []))
    excluded_menus_lower = analysis.get("excluded_menus", [])
    price_min = analysis.get("price_min", 0)
    price_max = analysis.get("price_max", 999999)
    cuisine_type = analysis.get("cuisine_type", "전체")
    food_base = analysis.get("food_base")

    for menu in menus:
        menu_name_lower = menu["menu_name"].lower()

        # ── 제외 메뉴 필터 ────────────────────────────
        is_excluded = any(
            excl in menu_name_lower or menu_name_lower in excl
            for excl in excluded_menus_lower
        )
        if is_excluded:
            continue

        # ── 알레르기 하드 필터 ────────────────────────
        menu_allergies = set(menu.get("allergy_info", []))
        allergy_conflict = user_allergies & menu_allergies
        if allergy_conflict:
            continue  # 알레르기 성분 포함 메뉴는 완전 제외

        # ── 가격대 필터 (중간 가격이 범위 내에 있는지 확인) ──
        menu_avg_price = (menu["price_range_min"] + menu["price_range_max"]) / 2
        if menu["price_range_min"] > price_max or menu["price_range_max"] < price_min:
            continue

        # ── 음식 종류 필터 ────────────────────────────
        if cuisine_type not in ("전체", None, ""):
            if menu["category"] != cuisine_type:
                continue

        # ── 밥/면 필터 ────────────────────────────────
        if food_base == "밥" and not menu.get("is_rice_based"):
            continue
        if food_base == "면" and not menu.get("is_noodle_based"):
            continue

        # ── 알레르기 정보 부재 경고 ────────────────────
        if not user_allergies and not menu_allergies:
            # 알레르기 정보 자체가 없는 메뉴 → 경고 추가하되 통과
            allergy_warning_menus.append(menu["menu_name"])

        passed_menus.append(menu)

    logger.info(f"필터링 결과: {len(menus)}개 → {len(passed_menus)}개")
    return passed_menus, allergy_warning_menus


def _calculate_menu_score(menu: dict, analysis: dict) -> float:
    """
    메뉴에 대한 추천 점수를 계산하는 내부 함수

    점수 구성:
    - 선호 메뉴 매칭: +30점
    - 가격 적합도 (범위 중앙 근접): +20점
    - 혼밥/단체 적합도: +15점
    - 설명 풍부도: +5점 (설명이 있으면 보너스)

    Args:
        menu: 메뉴 딕셔너리
        analysis: 분석된 조건 딕셔너리

    Returns:
        float: 0.0 ~ 100.0 범위의 추천 점수
    """
    score = 50.0  # 기본 점수

    menu_name_lower = menu["menu_name"].lower()
    preferred_menus = analysis.get("preferred_menus", [])

    # 선호 메뉴 매칭 점수
    for pref in preferred_menus:
        if pref in menu_name_lower or menu_name_lower in pref:
            score += 30.0
            break

    # 가격 적합도 점수 (사용자 예산 중앙값과 메뉴 중앙값 차이)
    if not analysis.get("price_flexible"):
        user_price_center = (analysis["price_min"] + analysis["price_max"]) / 2
        menu_price_center = (menu["price_range_min"] + menu["price_range_max"]) / 2
        price_diff_ratio = abs(user_price_center - menu_price_center) / max(user_price_center, 1)
        # 차이가 적을수록 높은 점수 (최대 +20점)
        price_score = max(0, 20 * (1 - price_diff_ratio))
        score += price_score

    # 인원 적합도 점수
    is_solo = analysis.get("is_solo", False)
    is_large_group = analysis.get("is_large_group", False)

    if is_solo and menu.get("is_solo_friendly"):
        score += 15.0
    elif is_large_group and menu.get("is_group_friendly"):
        score += 15.0
    elif not is_solo and not is_large_group:
        score += 8.0  # 소규모는 대부분 적합

    # 설명 풍부도 보너스
    if menu.get("description"):
        score += 5.0

    return min(score, 100.0)


def recommend_menu(
    user_conditions: dict,
    top_n: int = 3
) -> tuple[list[dict], list[str]]:
    """
    사용자 조건에 맞는 메뉴를 추천하는 메인 함수

    Args:
        user_conditions: 사용자 입력 조건 딕셔너리
        top_n: 반환할 추천 메뉴 수

    Returns:
        tuple[list[dict], list[str]]:
            - 추천 메뉴 목록 (각 항목에 'reasons' 필드 포함)
            - 알레르기 경고 메뉴 목록
    """
    # 1단계: 조건 분석
    analysis = analyze_conditions(user_conditions)

    # 2단계: 데이터베이스에서 메뉴 로드
    menus = load_menu_database(analysis.get("cuisine_type"))

    if not menus:
        logger.warning("데이터베이스에서 메뉴를 찾을 수 없습니다.")
        return [], []

    # 3단계: 필터링
    filtered_menus, allergy_warnings = filter_menus(menus, analysis)

    if not filtered_menus:
        # 필터링 결과가 없으면 조건 완화 후 재시도
        logger.warning("필터링 결과 없음. 조건을 완화하여 재시도합니다.")
        relaxed_analysis = {**analysis, "cuisine_type": "전체", "food_base": None}
        filtered_menus, allergy_warnings = filter_menus(menus, relaxed_analysis)

    # 4단계: 중복 제거
    filtered_menus = remove_duplicate_menus(filtered_menus)

    # 5단계: 점수 계산 및 정렬
    scored_menus = []
    for menu in filtered_menus:
        menu["score"] = _calculate_menu_score(menu, analysis)
        menu["reasons"] = generate_menu_recommendation_reasons(menu, analysis)
        scored_menus.append(menu)

    scored_menus.sort(key=lambda m: m["score"], reverse=True)

    # 6단계: 상위 N개 반환
    top_menus = scored_menus[:top_n]
    logger.info(f"최종 추천 메뉴: {[m['menu_name'] for m in top_menus]}")

    return top_menus, allergy_warnings


def remove_duplicate_menus(menus: list[dict]) -> list[dict]:
    """
    중복 메뉴를 제거하는 함수 (menu_id 기준)

    Args:
        menus: 메뉴 목록

    Returns:
        list[dict]: 중복이 제거된 메뉴 목록
    """
    seen_ids = set()
    unique_menus = []
    for menu in menus:
        menu_id = menu.get("menu_id")
        if menu_id not in seen_ids:
            seen_ids.add(menu_id)
            unique_menus.append(menu)
    return unique_menus


def generate_menu_recommendation_reasons(menu: dict, analysis: dict) -> list[str]:
    """
    메뉴 추천 이유를 생성하는 함수

    추천 이유는 사용자가 "왜 이 메뉴가 추천됐는지" 이해할 수 있도록
    구체적이고 개인화된 문장으로 작성합니다.

    Args:
        menu: 추천된 메뉴 딕셔너리
        analysis: 분석된 조건 딕셔너리

    Returns:
        list[str]: 추천 이유 문자열 목록 (최소 1개, 최대 5개)
    """
    reasons = []

    # ── 음식 종류 일치 ──────────────────────────────
    if analysis.get("has_cuisine_preference"):
        cuisine = analysis.get("cuisine_type", "")
        if menu.get("category") == cuisine:
            reasons.append(f"✓ 선호하신 {cuisine} 카테고리의 메뉴입니다")

    # ── 선호 메뉴 매칭 ─────────────────────────────
    menu_name_lower = menu["menu_name"].lower()
    for pref in analysis.get("preferred_menus", []):
        if pref in menu_name_lower or menu_name_lower in pref:
            reasons.append(f"✓ 선호 메뉴 '{pref}'와(과) 일치합니다")
            break

    # ── 가격대 적합성 ──────────────────────────────
    price_min_u = analysis.get("price_min", 0)
    price_max_u = analysis.get("price_max", 999999)
    price_mid_m = (menu["price_range_min"] + menu["price_range_max"]) / 2

    if not analysis.get("price_flexible"):
        if price_min_u <= price_mid_m <= price_max_u:
            reasons.append(
                f"✓ 선택하신 가격대 내의 메뉴입니다 "
                f"({format_price_range(menu['price_range_min'], menu['price_range_max'])})"
            )
    else:
        reasons.append(
            f"✓ 가격: {format_price_range(menu['price_range_min'], menu['price_range_max'])}"
        )

    # ── 인원 적합성 ────────────────────────────────
    if analysis.get("is_solo") and menu.get("is_solo_friendly"):
        reasons.append("✓ 혼밥하기 좋은 메뉴입니다")
    elif analysis.get("is_large_group") and menu.get("is_group_friendly"):
        reasons.append(f"✓ {analysis.get('person_count')}명 단체 식사에 적합합니다")

    # ── 밥/면 선호 일치 ────────────────────────────
    food_base = analysis.get("food_base")
    if food_base == "밥" and menu.get("is_rice_based"):
        reasons.append("✓ 선호하신 '밥' 종류의 메뉴입니다")
    elif food_base == "면" and menu.get("is_noodle_based"):
        reasons.append("✓ 선호하신 '면' 종류의 메뉴입니다")

    # ── 알레르기 안전 확인 ──────────────────────────
    if analysis.get("has_allergies"):
        reasons.append("✓ 알레르기 성분이 포함되지 않은 안전한 메뉴입니다")

    # 이유가 없으면 기본 이유 추가
    if not reasons:
        reasons.append(f"✓ {menu.get('category', '')} 카테고리의 인기 메뉴입니다")

    return reasons
