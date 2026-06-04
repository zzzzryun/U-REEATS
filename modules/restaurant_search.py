"""
modules/restaurant_search.py
==============================
음식점 검색, 거리 계산, 랭킹 산출 모듈

랭킹 알고리즘 설명:
  최종 점수 = (평점 × 0.35) + (리뷰 정규화 × 0.20) + (거리 역수 × 0.30) + (선호도 × 0.15)

  - 평점 점수: 5.0 만점 기준으로 정규화
  - 리뷰 정규화: 리뷰 수가 많을수록 높은 점수 (로그 스케일 적용)
  - 거리 역수: 가까울수록 높은 점수 (2km 기준)
  - 선호도 점수: 혼밥/단체 적합성, 선호 카테고리 일치 여부
"""

import os
import sys
import math
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    MAX_RECOMMENDED_STORES,
    RANKING_WEIGHT_RATING,
    RANKING_WEIGHT_REVIEW_COUNT,
    RANKING_WEIGHT_DISTANCE,
    RANKING_WEIGHT_PREFERENCE,
    DEFAULT_SEARCH_RADIUS
)
from utils.kakao_api import search_stores_by_keyword, build_kakao_map_url
from utils.helpers import calculate_distance_km, format_distance, parse_json_safe

logger = logging.getLogger(__name__)


def search_store_by_menu(
    menu_name: str,
    location: dict,
    cuisine_type: str = "전체"
) -> list[dict]:
    """
    추천된 메뉴를 기준으로 주변 음식점을 검색하는 함수

    카카오 로컬 API를 사용하여 메뉴 키워드와 위치 정보를 조합하여 검색

    Args:
        menu_name: 검색할 메뉴 이름
        location: {'latitude': float, 'longitude': float, 'address': str}
        cuisine_type: 음식 종류 (검색 키워드 보정에 사용)

    Returns:
        list[dict]: 검색된 음식점 목록
    """
    latitude = location.get("latitude", 37.4979)
    longitude = location.get("longitude", 127.0276)

    # 검색 키워드 구성 (메뉴명 + 카테고리)
    search_queries = []

    if cuisine_type and cuisine_type != "전체":
        search_queries.append(f"{menu_name} {cuisine_type}")
    search_queries.append(menu_name)
    search_queries.append(f"{menu_name} 맛집")

    # 각 키워드로 검색하여 결과 통합
    all_stores = []
    seen_place_ids = set()

    for query in search_queries:
        stores = search_stores_by_keyword(
            keyword=query,
            latitude=latitude,
            longitude=longitude,
            radius=DEFAULT_SEARCH_RADIUS
        )

        for store in stores:
            place_id = store.get("place_id")
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                all_stores.append(store)

        # 충분한 결과가 나오면 추가 검색 불필요
        if len(all_stores) >= 15:
            break

    logger.info(f"'{menu_name}' 음식점 검색 결과: {len(all_stores)}개")
    return all_stores


def calculate_distance(store: dict, user_location: dict) -> float:
    """
    음식점과 사용자 위치 간의 거리를 계산하는 함수

    Args:
        store: 음식점 정보 딕셔너리 (latitude, longitude 필드 필요)
        user_location: 사용자 위치 딕셔너리 (latitude, longitude 필드 필요)

    Returns:
        float: 직선 거리 (킬로미터)
    """
    try:
        user_lat = float(user_location.get("latitude", 0))
        user_lon = float(user_location.get("longitude", 0))
        store_lat = float(store.get("latitude", 0))
        store_lon = float(store.get("longitude", 0))

        if not all([user_lat, user_lon, store_lat, store_lon]):
            return 999.0  # 좌표 정보 없으면 매우 먼 거리로 처리

        distance = calculate_distance_km(user_lat, user_lon, store_lat, store_lon)

        # 카카오 API의 distance 필드도 참조 (더 정확한 경우)
        api_distance = store.get("distance")
        if api_distance:
            try:
                api_distance_km = float(api_distance) / 1000
                # 두 값의 평균 사용
                distance = (distance + api_distance_km) / 2
            except (ValueError, TypeError):
                pass

        return round(distance, 3)

    except Exception as e:
        logger.warning(f"거리 계산 오류: {e}")
        return 999.0


def _estimate_store_rating(store: dict) -> float:
    """
    카카오 API 응답에 평점 정보가 없을 경우 카테고리와 리뷰 수로 추정

    실제 서비스에서는 외부 리뷰 API(네이버, 구글) 연동으로 대체 권장
    """
    # 목업 데이터의 경우 rating 필드가 직접 포함됨
    if "rating" in store and store["rating"]:
        return float(store["rating"])

    # 카테고리 기반 기본 평점 추정 (카카오 API는 기본 평점 미제공)
    category = store.get("category_name", "")
    if "한정식" in category:
        return 4.2
    elif "이자카야" in category or "오마카세" in category:
        return 4.5
    elif "패스트푸드" in category:
        return 3.8
    else:
        return 4.0


def _estimate_review_count(store: dict) -> int:
    """리뷰 수 추정 (API 미제공 시)"""
    if "review_count" in store and store["review_count"]:
        return int(store["review_count"])
    # 카테고리와 장소명으로 대략적 추정
    place_name = store.get("place_name", "")
    if "본점" in place_name or "원조" in place_name:
        return 350
    elif "유명" in place_name or "맛집" in place_name:
        return 200
    else:
        return 100


def _calculate_ranking_score(
    store: dict,
    distance_km: float,
    user_conditions: dict
) -> tuple[float, list[str]]:
    """
    음식점의 종합 랭킹 점수를 계산하고 추천 이유를 생성하는 함수

    점수 계산 공식:
    score = rating_score * W_rating
           + review_score * W_review
           + distance_score * W_distance
           + preference_score * W_preference

    Args:
        store: 음식점 정보 딕셔너리
        distance_km: 사용자와의 거리 (km)
        user_conditions: 사용자 조건 딕셔너리

    Returns:
        tuple[float, list[str]]:
            - 최종 점수 (0.0 ~ 100.0)
            - 추천 이유 목록
    """
    reasons = []
    rating = _estimate_store_rating(store)
    review_count = _estimate_review_count(store)
    person_count = user_conditions.get("person_count", 1)

    # ── 평점 점수 (0 ~ 100 정규화) ──────────────────
    rating_score = (rating / 5.0) * 100
    if rating >= 4.5:
        reasons.append(f"✓ 매우 높은 평점 ({rating:.1f}★)")
    elif rating >= 4.0:
        reasons.append(f"✓ 높은 평점 ({rating:.1f}★)")
    elif rating >= 3.5:
        reasons.append(f"✓ 평점: {rating:.1f}★")

    # ── 리뷰 수 점수 (로그 스케일, 0 ~ 100) ─────────
    # 로그 스케일: 100개=50점, 300개=70점, 1000개=90점
    review_score = min(100, math.log10(max(review_count, 1)) * 45)
    if review_count >= 300:
        reasons.append(f"✓ 리뷰 {review_count:,}개 이상의 인기 맛집")
    elif review_count >= 100:
        reasons.append(f"✓ 리뷰 수: {review_count:,}개")

    # ── 거리 점수 (가까울수록 높은 점수) ─────────────
    # 0km=100점, 1km=70점, 2km=50점, 5km=20점
    if distance_km <= 0.3:
        distance_score = 100.0
        reasons.append(f"✓ 매우 가까운 거리 ({format_distance(distance_km)})")
    elif distance_km <= 1.0:
        distance_score = 100 - (distance_km * 30)
        reasons.append(f"✓ 도보 가능 거리 ({format_distance(distance_km)})")
    elif distance_km <= 2.0:
        distance_score = max(0, 70 - (distance_km - 1.0) * 20)
        reasons.append(f"✓ 거리: {format_distance(distance_km)}")
    else:
        distance_score = max(0, 50 - (distance_km - 2.0) * 15)

    # ── 선호도 점수 (혼밥/단체 적합성) ──────────────
    preference_score = 50.0  # 기본값

    group_available = store.get("group_available", 1)
    solo_available = store.get("solo_available", 1)

    # 목업 데이터에서 category_name으로 추정
    category = store.get("category_name", "")

    if person_count == 1:
        # 혼밥 적합 음식점 우선 (분식, 라멘, 1인 한식 등)
        solo_friendly_keywords = ["라멘", "국밥", "설렁탕", "순댓국", "분식", "편의점"]
        if any(kw in store.get("place_name", "") + category for kw in solo_friendly_keywords):
            preference_score = 90.0
            reasons.append("✓ 혼밥하기 좋은 음식점입니다")
        elif solo_available:
            preference_score = 70.0
            reasons.append("✓ 1인 식사 가능한 음식점입니다")
        else:
            preference_score = 30.0

    elif person_count >= 5:
        # 단체 적합 음식점 우선 (고기구이, 회식 장소 등)
        group_friendly_keywords = ["삼겹살", "갈비", "고기", "회식", "단체", "룸"]
        if any(kw in store.get("place_name", "") + category for kw in group_friendly_keywords):
            preference_score = 90.0
            reasons.append(f"✓ {person_count}명 단체 식사에 적합합니다")
        elif group_available:
            preference_score = 70.0
            reasons.append("✓ 단체 좌석이 마련된 음식점입니다")
        else:
            preference_score = 30.0
    else:
        preference_score = 65.0  # 소규모는 대부분 무난

    # ── 최종 점수 계산 ────────────────────────────
    final_score = (
        rating_score    * RANKING_WEIGHT_RATING       +
        review_score    * RANKING_WEIGHT_REVIEW_COUNT  +
        distance_score  * RANKING_WEIGHT_DISTANCE      +
        preference_score * RANKING_WEIGHT_PREFERENCE
    )

    return round(final_score, 2), reasons


def filter_by_constraints(stores: list[dict], user_conditions: dict) -> list[dict]:
    """
    음식점 목록에서 사용자 제약 조건에 맞지 않는 곳을 필터링

    Args:
        stores: 음식점 목록
        user_conditions: 사용자 조건 딕셔너리

    Returns:
        list[dict]: 필터링된 음식점 목록
    """
    person_count = user_conditions.get("person_count", 1)
    filtered = []

    for store in stores:
        # 좌표 정보가 없으면 제외
        if not store.get("latitude") or not store.get("longitude"):
            continue

        # 이름이 없으면 제외
        if not store.get("place_name"):
            continue

        filtered.append(store)

    return filtered


def rank_top_stores(
    stores: list[dict],
    user_location: dict,
    user_conditions: dict,
    top_n: int = MAX_RECOMMENDED_STORES
) -> list[dict]:
    """
    검색된 음식점을 랭킹 알고리즘으로 정렬하여 상위 N개를 반환

    Args:
        stores: 검색된 음식점 목록
        user_location: 사용자 위치 딕셔너리
        user_conditions: 사용자 조건 딕셔너리
        top_n: 반환할 최대 개수

    Returns:
        list[dict]: 랭킹 점수 및 추천 이유가 포함된 상위 음식점 목록
    """
    if not stores:
        return []

    # 필터링
    filtered = filter_by_constraints(stores, user_conditions)

    # 각 음식점에 거리와 점수 계산
    scored_stores = []
    for store in filtered:
        distance_km = calculate_distance(store, user_location)
        ranking_score, reasons = _calculate_ranking_score(store, distance_km, user_conditions)

        enriched_store = {
            **store,
            "distance_km": distance_km,
            "distance_display": format_distance(distance_km),
            "ranking_score": ranking_score,
            "recommendation_reasons": reasons,
            "rating": _estimate_store_rating(store),
            "review_count": _estimate_review_count(store),
            "map_url": build_kakao_map_url(
                store.get("place_name", ""),
                store.get("latitude", 0),
                store.get("longitude", 0)
            )
        }
        scored_stores.append(enriched_store)

    # 점수 내림차순 정렬
    scored_stores.sort(key=lambda s: s["ranking_score"], reverse=True)

    return scored_stores[:top_n]


def fetch_store_details(store: dict) -> dict:
    """
    음식점의 상세 정보를 가져오는 함수

    현재는 카카오 API 응답 데이터를 정제하는 역할
    향후 네이버 플레이스 API 연동으로 리뷰 본문, 사진 등 확장 가능

    Args:
        store: 기본 음식점 정보

    Returns:
        dict: 상세 정보가 보강된 음식점 딕셔너리
    """
    details = {
        **store,
        "full_address": store.get("road_address_name") or store.get("address_name", ""),
        "has_phone": bool(store.get("phone")),
        "kakao_map_url": store.get("place_url", ""),
        "direct_map_url": store.get("map_url", "")
    }

    # 카테고리에서 메인 카테고리 추출
    # 예: "음식점 > 한식 > 해물,생선" → "한식"
    category_raw = store.get("category_name", "")
    if " > " in category_raw:
        parts = category_raw.split(" > ")
        details["main_category"] = parts[1] if len(parts) > 1 else parts[0]
        details["sub_category"] = parts[2] if len(parts) > 2 else ""
    else:
        details["main_category"] = category_raw
        details["sub_category"] = ""

    return details


def handle_empty_search_result(
    menu_name: str,
    location: dict,
    user_conditions: dict
) -> list[dict]:
    """
    음식점 검색 결과가 없을 경우 처리하는 함수

    전략:
    1. 검색 반경 확대
    2. 키워드 단순화
    3. 대안 메뉴 제안

    Args:
        menu_name: 원래 검색 메뉴명
        location: 사용자 위치
        user_conditions: 사용자 조건

    Returns:
        list[dict]: 대안 음식점 목록 (비어있을 수 있음)
    """
    logger.warning(f"'{menu_name}' 검색 결과 없음. 반경 확대 재시도")

    # 반경 확대하여 재검색
    from utils.kakao_api import search_stores_by_keyword
    latitude = location.get("latitude", 37.4979)
    longitude = location.get("longitude", 127.0276)

    extended_stores = search_stores_by_keyword(
        keyword=menu_name,
        latitude=latitude,
        longitude=longitude,
        radius=5000  # 5km로 확대
    )

    if extended_stores:
        logger.info(f"반경 확대 검색으로 {len(extended_stores)}개 발견")
        return extended_stores

    # 그래도 없으면 카테고리 기반 검색
    cuisine_type = user_conditions.get("cuisine_type", "한식")
    if cuisine_type != "전체":
        logger.info(f"카테고리 '{cuisine_type}' 기반 대안 검색")
        fallback_stores = search_stores_by_keyword(
            keyword=cuisine_type,
            latitude=latitude,
            longitude=longitude,
            radius=3000
        )
        return fallback_stores

    return []


def get_restaurant_recommendation(
    recommended_menu: dict,
    user_conditions: dict
) -> list[dict]:
    """
    추천 메뉴에 맞는 레스토랑을 검색하고 랭킹화하여 반환하는 통합 함수

    Args:
        recommended_menu: 추천된 메뉴 정보 딕셔너리
        user_conditions: 사용자 조건

    Returns:
        list[dict]: 상위 3개 추천 음식점 목록
    """
    location = user_conditions.get("location", {})
    menu_name = recommended_menu.get("menu_name", "")
    cuisine_type = recommended_menu.get("category", "전체")

    # 음식점 검색
    stores = search_store_by_menu(menu_name, location, cuisine_type)

    # 검색 결과 없으면 빈 결과 처리
    if not stores:
        stores = handle_empty_search_result(menu_name, location, user_conditions)

    if not stores:
        return []

    # 랭킹 산출 및 상세 정보 보강
    top_stores = rank_top_stores(stores, location, user_conditions)

    # 상세 정보 추가
    detailed_stores = [fetch_store_details(store) for store in top_stores]

    return detailed_stores
