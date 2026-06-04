"""
utils/kakao_api.py
==================
카카오 로컬 API 연동 모듈

제공 기능:
1. 키워드 기반 음식점 검색 (카카오 로컬 API)
2. 주소를 좌표로 변환 (지오코딩)
3. API 응답 정규화 및 오류 처리
4. API 사용 불가 시 폴백(Fallback) 데이터 제공

카카오 API 공식 문서: https://developers.kakao.com/docs/latest/ko/local/dev-guide
"""

import requests
import json
import os
import sys
import time
import logging
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import (
    KAKAO_REST_API_KEY,
    KAKAO_LOCAL_API_URL,
    KAKAO_GEOCODE_API_URL,
    KAKAO_MAP_BASE_URL,
    DEFAULT_SEARCH_RADIUS,
    MAX_SEARCH_RADIUS
)

logger = logging.getLogger(__name__)

# API 요청 헤더 (카카오 인증 방식)
KAKAO_HEADERS = {
    "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
    "Content-Type": "application/json"
}

# 모의(Mock) API 사용 여부 (API 키 미설정 시 자동 활성화)
USE_MOCK_API = (KAKAO_REST_API_KEY == "YOUR_KAKAO_REST_API_KEY_HERE")


def search_stores_by_keyword(
    keyword: str,
    latitude: float,
    longitude: float,
    radius: int = DEFAULT_SEARCH_RADIUS,
    page: int = 1,
    size: int = 15
) -> list[dict]:
    """
    카카오 로컬 API를 사용하여 키워드로 음식점을 검색

    Args:
        keyword: 검색 키워드 (e.g., '비빔밥 맛집', '삼겹살')
        latitude: 검색 중심 위도
        longitude: 검색 중심 경도
        radius: 검색 반경 (미터, 최대 20000)
        page: 페이지 번호 (1~45)
        size: 페이지당 결과 수 (1~15)

    Returns:
        list[dict]: 정규화된 음식점 정보 목록
        각 항목:
            - place_id: 카카오 장소 고유 ID
            - place_name: 음식점 이름
            - category_name: 카테고리 (e.g., '음식점 > 한식 > 해물,생선')
            - address_name: 지번 주소
            - road_address_name: 도로명 주소
            - phone: 전화번호
            - latitude: 위도 (float)
            - longitude: 경도 (float)
            - place_url: 카카오맵 상세 URL
            - distance: 검색 중심에서의 거리 (미터, 문자열)
    """
    if USE_MOCK_API:
        logger.warning("카카오 API 키가 설정되지 않아 목업 데이터를 사용합니다.")
        return _get_mock_store_data(keyword, latitude, longitude)

    try:
        params = {
            "query": keyword,
            "category_group_code": "FD6",  # FD6: 음식점 카테고리 코드
            "x": str(longitude),            # 경도가 x
            "y": str(latitude),             # 위도가 y
            "radius": min(radius, MAX_SEARCH_RADIUS),
            "page": page,
            "size": size,
            "sort": "distance"              # 거리순 정렬
        }

        response = requests.get(
            KAKAO_LOCAL_API_URL,
            headers=KAKAO_HEADERS,
            params=params,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        # API 응답 정규화
        stores = []
        for place in data.get("documents", []):
            stores.append(_normalize_kakao_place(place))

        logger.info(f"카카오 API 검색 결과: '{keyword}' → {len(stores)}개 음식점")
        return stores

    except requests.exceptions.ConnectionError:
        logger.error("카카오 API 연결 실패. 네트워크 연결을 확인하세요.")
        return _get_mock_store_data(keyword, latitude, longitude)

    except requests.exceptions.Timeout:
        logger.error("카카오 API 요청 시간 초과 (5초)")
        return _get_mock_store_data(keyword, latitude, longitude)

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        if status_code == 401:
            logger.error("카카오 API 인증 실패. API 키를 확인하세요.")
        elif status_code == 429:
            logger.warning("카카오 API 요청 한도 초과. 잠시 후 재시도합니다.")
            time.sleep(1)
        else:
            logger.error(f"카카오 API HTTP 오류: {status_code}")
        return _get_mock_store_data(keyword, latitude, longitude)

    except Exception as e:
        logger.error(f"카카오 API 예상치 못한 오류: {e}")
        return _get_mock_store_data(keyword, latitude, longitude)


def geocode_address(address: str) -> Optional[dict]:
    """
    주소 문자열을 위도/경도 좌표로 변환 (지오코딩)

    Args:
        address: 변환할 주소 문자열 (e.g., '서울특별시 강남구 테헤란로 152')

    Returns:
        Optional[dict]: 성공 시 {'latitude': float, 'longitude': float, 'address': str}
                        실패 시 None
    """
    if USE_MOCK_API:
        return _get_mock_coordinates(address)

    try:
        params = {"query": address, "size": 1}
        response = requests.get(
            KAKAO_GEOCODE_API_URL,
            headers=KAKAO_HEADERS,
            params=params,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        documents = data.get("documents", [])
        if not documents:
            logger.warning(f"주소 검색 결과 없음: '{address}'")
            return None

        doc = documents[0]
        return {
            "latitude": float(doc.get("y", 0)),
            "longitude": float(doc.get("x", 0)),
            "address": doc.get("address_name", address)
        }

    except Exception as e:
        logger.error(f"지오코딩 오류: {e}")
        return _get_mock_coordinates(address)


def build_kakao_map_url(store_name: str, latitude: float, longitude: float) -> str:
    """
    카카오맵 링크 URL을 생성

    Args:
        store_name: 음식점 이름
        latitude: 위도
        longitude: 경도

    Returns:
        str: 카카오맵 링크 URL
    """
    return f"{KAKAO_MAP_BASE_URL}/{store_name}/{longitude}/{latitude}"


# ─────────────────────────────────────────────
# 내부 헬퍼 함수
# ─────────────────────────────────────────────

def _normalize_kakao_place(place: dict) -> dict:
    """카카오 API 응답의 장소 정보를 내부 표준 형식으로 변환"""
    return {
        "place_id": place.get("id", ""),
        "place_name": place.get("place_name", ""),
        "category_name": place.get("category_name", ""),
        "address_name": place.get("address_name", ""),
        "road_address_name": place.get("road_address_name", ""),
        "phone": place.get("phone", ""),
        "latitude": float(place.get("y", 0)),
        "longitude": float(place.get("x", 0)),
        "place_url": place.get("place_url", ""),
        "distance": place.get("distance", "0"),  # 미터 단위 문자열
    }


def _get_mock_store_data(keyword: str, latitude: float, longitude: float) -> list[dict]:
    """
    API 키 미설정 또는 API 오류 시 사용하는 목업 데이터
    실제 서울 강남구 주변 좌표 기반으로 작성

    이 함수는 개발/테스트 환경에서만 사용하며,
    실제 배포 시에는 카카오 API 키를 반드시 설정해야 합니다.
    """
    # 메뉴 키워드에 맞는 목업 데이터 생성
    menu_keywords = {
        "비빔밥": [
            {
                "place_id": "mock_001",
                "place_name": "전주비빔밥 강남점",
                "category_name": "음식점 > 한식 > 한정식",
                "address_name": "서울 강남구 역삼동 823-5",
                "road_address_name": "서울 강남구 테헤란로 152",
                "phone": "02-555-1234",
                "latitude": latitude + 0.002,
                "longitude": longitude + 0.003,
                "place_url": "https://place.map.kakao.com/mock001",
                "distance": "350",
                "rating": 4.5,
                "review_count": 342
            },
            {
                "place_id": "mock_002",
                "place_name": "돌솥비빔밥 명인",
                "category_name": "음식점 > 한식",
                "address_name": "서울 강남구 역삼동 716-1",
                "road_address_name": "서울 강남구 강남대로 396",
                "phone": "02-555-5678",
                "latitude": latitude - 0.003,
                "longitude": longitude + 0.001,
                "place_url": "https://place.map.kakao.com/mock002",
                "distance": "520",
                "rating": 4.2,
                "review_count": 218
            },
            {
                "place_id": "mock_003",
                "place_name": "산채비빔밥 & 보리밥",
                "category_name": "음식점 > 한식 > 한정식",
                "address_name": "서울 강남구 논현동 113",
                "road_address_name": "서울 강남구 학동로 101",
                "phone": "02-555-9012",
                "latitude": latitude + 0.005,
                "longitude": longitude - 0.002,
                "place_url": "https://place.map.kakao.com/mock003",
                "distance": "780",
                "rating": 4.0,
                "review_count": 156
            }
        ],
        "삼겹살": [
            {
                "place_id": "mock_011",
                "place_name": "참숯 삼겹살 직화구이",
                "category_name": "음식점 > 한식 > 돼지고기구이",
                "address_name": "서울 강남구 역삼동 614-3",
                "road_address_name": "서울 강남구 역삼로 185",
                "phone": "02-556-2222",
                "latitude": latitude + 0.001,
                "longitude": longitude - 0.004,
                "place_url": "https://place.map.kakao.com/mock011",
                "distance": "420",
                "rating": 4.6,
                "review_count": 589
            },
            {
                "place_id": "mock_012",
                "place_name": "이층집 삼겹살",
                "category_name": "음식점 > 한식 > 돼지고기구이",
                "address_name": "서울 강남구 논현동 220",
                "road_address_name": "서울 강남구 논현로 428",
                "phone": "02-542-3333",
                "latitude": latitude - 0.002,
                "longitude": longitude + 0.005,
                "place_url": "https://place.map.kakao.com/mock012",
                "distance": "670",
                "rating": 4.3,
                "review_count": 421
            }
        ],
        "default": [
            {
                "place_id": f"mock_d{i:03d}",
                "place_name": f"{keyword} 맛집 {i}호점",
                "category_name": "음식점 > 한식",
                "address_name": f"서울 강남구 역삼동 {100+i*10}",
                "road_address_name": f"서울 강남구 테헤란로 {200+i*15}",
                "phone": f"02-555-{1000+i*111:04d}",
                "latitude": latitude + (i * 0.002),
                "longitude": longitude + (i * 0.001),
                "place_url": f"https://place.map.kakao.com/mock_d{i:03d}",
                "distance": str(300 + i * 150),
                "rating": round(3.5 + i * 0.3, 1),
                "review_count": 50 + i * 80
            }
            for i in range(1, 4)
        ]
    }

    # 키워드 매칭 시도 (부분 일치)
    for key, stores in menu_keywords.items():
        if key in keyword:
            return stores

    # 매칭 실패 시 기본 데이터 반환
    default = menu_keywords["default"]
    for store in default:
        store["place_name"] = f"{keyword} 전문점 {store['place_name'].split(' ')[-1]}"
    return default


def _get_mock_coordinates(address: str) -> dict:
    """
    주소에 대한 목업 좌표 반환 (서울 강남구 기준)

    지역명 키워드로 대략적인 좌표를 반환합니다.
    """
    # 주요 지역별 대략적 좌표 (서울 중심)
    location_coords = {
        "강남": {"latitude": 37.4979, "longitude": 127.0276},
        "홍대": {"latitude": 37.5563, "longitude": 126.9236},
        "신촌": {"latitude": 37.5594, "longitude": 126.9371},
        "건대": {"latitude": 37.5404, "longitude": 127.0693},
        "신림": {"latitude": 37.4847, "longitude": 126.9295},
        "이태원": {"latitude": 37.5342, "longitude": 126.9945},
        "종로": {"latitude": 37.5726, "longitude": 126.9807},
        "혜화": {"latitude": 37.5826, "longitude": 127.0017},
        "서울": {"latitude": 37.5665, "longitude": 126.9780},  # 서울 시청
    }

    for region, coords in location_coords.items():
        if region in address:
            return {**coords, "address": address}

    # 기본값: 서울 강남역 좌표
    return {
        "latitude": 37.4979,
        "longitude": 127.0276,
        "address": address or "서울특별시 강남구"
    }
