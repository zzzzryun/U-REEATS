"""
config/settings.py
==================
프로젝트 전역 설정 파일
- API 키, 데이터베이스 경로, 상수 등 모든 설정 값을 중앙 관리
- 실제 배포 시 환경변수(.env)로 민감한 정보를 분리하는 것을 권장
"""

import os

# ─────────────────────────────────────────────
# 프로젝트 기본 경로
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

# ─────────────────────────────────────────────
# 데이터베이스 설정
# ─────────────────────────────────────────────
DATABASE_PATH = os.path.join(DATABASE_DIR, "u_re_eats.db")

# ─────────────────────────────────────────────
# 카카오 API 설정
# 실제 사용 시: 카카오 개발자 콘솔(https://developers.kakao.com)에서 발급받은 키로 교체
# ─────────────────────────────────────────────
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY", "YOUR_KAKAO_REST_API_KEY_HERE")
KAKAO_LOCAL_API_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_GEOCODE_API_URL = "https://dapi.kakao.com/v2/local/search/address.json"
KAKAO_MAP_BASE_URL = "https://map.kakao.com/link/map"

# ─────────────────────────────────────────────
# 검색 및 추천 설정
# ─────────────────────────────────────────────
# 카카오 API 기본 검색 반경 (단위: 미터)
DEFAULT_SEARCH_RADIUS = 2000         # 2km
MAX_SEARCH_RADIUS = 5000             # 5km

# 추천 레스토랑 최대 개수
MAX_RECOMMENDED_STORES = 3

# 랭킹 알고리즘 가중치 (합계 = 1.0)
RANKING_WEIGHT_RATING = 0.35         # 평점 가중치
RANKING_WEIGHT_REVIEW_COUNT = 0.20   # 리뷰 수 가중치
RANKING_WEIGHT_DISTANCE = 0.30       # 거리 가중치
RANKING_WEIGHT_PREFERENCE = 0.15     # 사용자 선호도 가중치

# ─────────────────────────────────────────────
# 음식 카테고리 정의
# ─────────────────────────────────────────────
CUISINE_TYPES = {
    "1": "한식",
    "2": "양식",
    "3": "중식",
    "4": "일식",
    "5": "아시안",
    "6": "패스트푸드",
    "7": "분식",
    "8": "카페/디저트"
}

# ─────────────────────────────────────────────
# 가격대 정의
# ─────────────────────────────────────────────
PRICE_RANGES = {
    "1": {"label": "저렴 (1만원 미만)", "min": 0, "max": 10000},
    "2": {"label": "보통 (1만원 ~ 2만원)", "min": 10000, "max": 20000},
    "3": {"label": "비싼 (2만원 ~ 3만원)", "min": 20000, "max": 30000},
    "4": {"label": "고급 (3만원 이상)", "min": 30000, "max": 999999}
}

# ─────────────────────────────────────────────
# 알레르기 정보 목록
# ─────────────────────────────────────────────
ALLERGY_LIST = [
    "gluten",       # 글루텐 (밀가루)
    "dairy",        # 유제품
    "egg",          # 달걀
    "nuts",         # 견과류
    "shellfish",    # 갑각류
    "fish",         # 생선
    "soy",          # 대두(콩)
    "pork",         # 돼지고기
    "beef",         # 소고기
    "sesame"        # 참깨
]

ALLERGY_DISPLAY_NAMES = {
    "gluten": "글루텐(밀가루)",
    "dairy": "유제품(우유/치즈)",
    "egg": "달걀",
    "nuts": "견과류",
    "shellfish": "갑각류(새우/게)",
    "fish": "생선",
    "soy": "대두(콩)",
    "pork": "돼지고기",
    "beef": "소고기",
    "sesame": "참깨"
}

# ─────────────────────────────────────────────
# 로깅 설정
# ─────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"
LOG_FILE = os.path.join(BASE_DIR, "logs", "u_re_eats.log")

# ─────────────────────────────────────────────
# UI 설정
# ─────────────────────────────────────────────
APP_NAME = "U-RE EATS"
APP_VERSION = "1.0.0"
SEPARATOR_LINE = "=" * 60
THIN_SEPARATOR = "-" * 60
