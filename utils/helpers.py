"""
utils/helpers.py
================
프로젝트 전반에서 사용되는 공통 유틸리티 함수 모음

포함 기능:
- 거리 계산 (하버사인 공식)
- 입력값 검증
- 텍스트 포맷팅
- UUID 생성
- 로깅 설정
"""

import math
import uuid
import re
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import LOG_LEVEL, LOG_FORMAT, SEPARATOR_LINE, THIN_SEPARATOR


# ─────────────────────────────────────────────
# 로깅 설정
# ─────────────────────────────────────────────

def setup_logging(name: str = "u_re_eats") -> logging.Logger:
    """
    일관된 로깅 설정을 적용한 Logger 인스턴스 반환

    Args:
        name: 로거 이름 (모듈별로 구분하여 사용)

    Returns:
        logging.Logger: 설정된 로거 객체
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # 중복 핸들러 방지
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    return logger


# ─────────────────────────────────────────────
# 거리 계산
# ─────────────────────────────────────────────

def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    두 좌표 사이의 직선 거리를 킬로미터 단위로 계산 (하버사인 공식)

    하버사인 공식: 지구 곡률을 고려한 정확한 거리 계산
    오차 범위: 0.5% 이내 (도시 내 거리 계산에 충분)

    Args:
        lat1, lon1: 출발지 위도/경도
        lat2, lon2: 목적지 위도/경도

    Returns:
        float: 두 지점 사이 거리 (킬로미터)
    """
    R = 6371.0  # 지구 반지름 (km)

    # 라디안 변환
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # 하버사인 계산
    a = (math.sin(delta_lat / 2) ** 2
         + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 3)


def format_distance(distance_km: float) -> str:
    """
    거리를 사람이 읽기 쉬운 형식으로 포맷팅

    Args:
        distance_km: 킬로미터 단위 거리

    Returns:
        str: '500m' 또는 '1.2km' 형식의 문자열
    """
    if distance_km < 1.0:
        return f"{int(distance_km * 1000)}m"
    else:
        return f"{distance_km:.1f}km"


# ─────────────────────────────────────────────
# 가격 포맷팅
# ─────────────────────────────────────────────

def format_price(price: int) -> str:
    """
    가격을 한국 원화 형식으로 포맷팅

    Args:
        price: 원화 금액 (정수)

    Returns:
        str: '12,000원' 형식의 문자열
    """
    return f"{price:,}원"


def format_price_range(price_min: int, price_max: int) -> str:
    """
    가격 범위를 포맷팅

    Args:
        price_min: 최소 가격
        price_max: 최대 가격

    Returns:
        str: '7,000원 ~ 12,000원' 형식의 문자열
    """
    return f"{format_price(price_min)} ~ {format_price(price_max)}"


# ─────────────────────────────────────────────
# 입력값 검증
# ─────────────────────────────────────────────

def validate_number_input(value: str, min_val: int, max_val: int) -> Optional[int]:
    """
    숫자 입력값의 유효성을 검사

    Args:
        value: 검사할 문자열 입력값
        min_val: 허용 최솟값
        max_val: 허용 최댓값

    Returns:
        Optional[int]: 유효한 경우 정수 반환, 그렇지 않으면 None
    """
    try:
        num = int(value.strip())
        if min_val <= num <= max_val:
            return num
        return None
    except (ValueError, AttributeError):
        return None


def parse_json_safe(json_str: str, default=None):
    """
    JSON 파싱을 안전하게 수행 (예외 처리 포함)

    Args:
        json_str: 파싱할 JSON 문자열
        default: 파싱 실패 시 반환할 기본값

    Returns:
        파싱된 Python 객체 또는 default 값
    """
    if not json_str:
        return default if default is not None else []
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


# ─────────────────────────────────────────────
# 세션 관리
# ─────────────────────────────────────────────

def generate_session_id() -> str:
    """
    고유한 세션 ID를 생성

    Returns:
        str: UUID4 기반의 세션 ID
    """
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    """현재 시각을 ISO 형식 문자열로 반환"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────
# UI 출력 헬퍼
# ─────────────────────────────────────────────

def print_header(title: str):
    """섹션 헤더를 출력"""
    print(f"\n{SEPARATOR_LINE}")
    print(f"  {title}")
    print(SEPARATOR_LINE)


def print_subheader(title: str):
    """서브섹션 헤더를 출력"""
    print(f"\n{THIN_SEPARATOR}")
    print(f"  {title}")
    print(THIN_SEPARATOR)


def print_info(message: str, indent: int = 0):
    """정보 메시지 출력"""
    prefix = "  " * indent
    print(f"{prefix}ℹ️  {message}")


def print_success(message: str):
    """성공 메시지 출력"""
    print(f"✅ {message}")


def print_warning(message: str):
    """경고 메시지 출력"""
    print(f"⚠️  {message}")


def print_error(message: str):
    """에러 메시지 출력"""
    print(f"❌ {message}")


def print_numbered_list(items: list, start: int = 1):
    """번호가 붙은 목록을 출력"""
    for i, item in enumerate(items, start=start):
        print(f"  {i}. {item}")


def truncate_text(text: str, max_length: int = 40) -> str:
    """텍스트를 최대 길이로 잘라서 반환"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def stars_rating(rating: float) -> str:
    """
    숫자 평점을 별 이모지로 시각화

    Args:
        rating: 0.0 ~ 5.0 범위의 평점

    Returns:
        str: '★★★★☆ (4.2)' 형식의 문자열
    """
    filled = int(rating)
    empty = 5 - filled
    return "★" * filled + "☆" * empty + f" ({rating:.1f})"
