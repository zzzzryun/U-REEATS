"""
database/schema.py
==================
데이터베이스 스키마 생성 및 초기 데이터 삽입 모듈

설계 원칙:
- 미래 확장성을 고려한 정규화된 스키마
- 영양 정보, 주문 이력, AI 학습 데이터를 위한 테이블 사전 설계
- SQLite의 JSON 타입을 활용한 유연한 데이터 저장
"""

import sqlite3
import json
import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DATABASE_PATH, DATABASE_DIR


def create_database():
    """
    전체 데이터베이스 스키마를 생성하는 메인 함수
    기존 데이터베이스가 있으면 재생성하지 않음 (데이터 보호)
    """
    # database 디렉토리가 없으면 생성
    os.makedirs(DATABASE_DIR, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # 외래키 제약 활성화
    conn.execute("PRAGMA journal_mode = WAL")  # 동시성 향상
    cursor = conn.cursor()

    print("[DB] 데이터베이스 스키마 생성 중...")
    _create_tables(cursor)
    conn.commit()
    print("[DB] 스키마 생성 완료!")
    conn.close()


def _create_tables(cursor):
    """모든 테이블을 순서대로 생성 (외래키 순서 준수)"""

    # ─────────────────────────────────────────────
    # 1. 음식 카테고리 테이블 (정규화)
    # ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_category (
            category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT    NOT NULL UNIQUE,  -- '한식', '양식' 등
            description   TEXT,                      -- 카테고리 설명
            created_at    TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ─────────────────────────────────────────────
    # 2. 메뉴 테이블 (핵심 테이블)
    # ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            menu_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_name        TEXT    NOT NULL,           -- 메뉴 이름 (e.g., '비빔밥')
            category_id      INTEGER NOT NULL,            -- food_category 외래키
            price_range_min  INTEGER NOT NULL DEFAULT 0, -- 최소 가격 (원)
            price_range_max  INTEGER NOT NULL DEFAULT 0, -- 최대 가격 (원)
            is_rice_based    INTEGER NOT NULL DEFAULT 0, -- 밥 기반 여부 (0/1)
            is_noodle_based  INTEGER NOT NULL DEFAULT 0, -- 면 기반 여부 (0/1)
            description      TEXT,                       -- 메뉴 설명
            allergy_info     TEXT    DEFAULT '[]',       -- JSON 배열: ['gluten', 'dairy']
            nutrition_info   TEXT    DEFAULT '{}',       -- JSON: {'calories':500, 'protein':30}
            is_solo_friendly INTEGER NOT NULL DEFAULT 1, -- 혼밥 적합 여부
            is_group_friendly INTEGER NOT NULL DEFAULT 1,-- 단체 적합 여부
            is_active        INTEGER NOT NULL DEFAULT 1, -- 활성화 여부 (소프트 삭제)
            created_at       TEXT    DEFAULT (datetime('now', 'localtime')),
            updated_at       TEXT    DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (category_id) REFERENCES food_category(category_id)
        )
    """)

    # ─────────────────────────────────────────────
    # 3. 음식점 테이블
    # ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS store (
            store_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            kakao_place_id    TEXT    UNIQUE,            -- 카카오 API place_id (중복 방지)
            store_name        TEXT    NOT NULL,           -- 음식점 이름
            address           TEXT    NOT NULL,           -- 지번 주소
            road_address      TEXT,                       -- 도로명 주소
            phone             TEXT,                       -- 전화번호
            category_name     TEXT,                       -- 카카오 카테고리 (e.g., '음식점 > 한식')
            latitude          REAL,                       -- 위도
            longitude         REAL,                       -- 경도
            rating            REAL    DEFAULT 0.0,        -- 평점 (0.0 ~ 5.0)
            review_count      INTEGER DEFAULT 0,          -- 리뷰 수
            group_available   INTEGER DEFAULT 1,          -- 단체석 가능 여부
            solo_available    INTEGER DEFAULT 1,          -- 혼밥 가능 여부
            price_level       INTEGER DEFAULT 2,          -- 가격대 (1:저, 2:중, 3:고)
            menu_keywords     TEXT    DEFAULT '[]',       -- JSON: 대표 메뉴 키워드 목록
            open_hours        TEXT,                       -- 영업시간 정보
            is_active         INTEGER DEFAULT 1,          -- 활성화 여부
            last_fetched_at   TEXT,                       -- 마지막 API 조회 시각
            created_at        TEXT    DEFAULT (datetime('now', 'localtime')),
            updated_at        TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ─────────────────────────────────────────────
    # 4. 추천 이력 테이블 (핵심 비즈니스 데이터)
    # ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendation_history (
            history_id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          TEXT    NOT NULL,         -- 세션 식별자 (UUID)
            user_conditions     TEXT    NOT NULL,         -- JSON: 사용자 입력 전체
            recommended_menu_id INTEGER,                  -- 추천된 메뉴 ID
            recommended_menu    TEXT    NOT NULL,         -- 추천 메뉴 이름 (스냅샷)
            recommendation_reasons TEXT DEFAULT '[]',     -- JSON: 추천 이유 목록
            recommended_stores  TEXT    DEFAULT '[]',     -- JSON: 추천 음식점 목록 스냅샷
            user_feedback       TEXT,                     -- 사용자 피드백 (선택)
            was_accepted        INTEGER DEFAULT 0,        -- 추천 수락 여부 (AI 학습용)
            search_location     TEXT,                     -- 검색 위치
            recommendation_date TEXT    DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (recommended_menu_id) REFERENCES menu(menu_id)
        )
    """)

    # ─────────────────────────────────────────────
    # 5. 사용자 선호도 학습 테이블 (AI 확장 대비)
    # ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_preference (
            preference_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id       TEXT    NOT NULL,            -- 세션 기반 식별
            preferred_cuisine TEXT,                       -- 선호 음식 종류
            preferred_menus  TEXT    DEFAULT '[]',        -- JSON: 선호 메뉴 목록
            excluded_menus   TEXT    DEFAULT '[]',        -- JSON: 제외 메뉴 목록
            allergy_info     TEXT    DEFAULT '[]',        -- JSON: 알레르기 정보
            price_min        INTEGER DEFAULT 0,
            price_max        INTEGER DEFAULT 99999,
            person_count     INTEGER DEFAULT 1,
            location_address TEXT,
            latitude         REAL,
            longitude        REAL,
            created_at       TEXT    DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ─────────────────────────────────────────────
    # 6. 주문 이력 테이블 (미래 기능: 실제 주문 연동)
    # ─────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_history (
            order_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id       TEXT    NOT NULL,
            history_id       INTEGER,                     -- 추천 이력 참조
            store_id         INTEGER,                     -- 주문 음식점
            menu_id          INTEGER,                     -- 주문 메뉴
            order_amount     INTEGER DEFAULT 0,           -- 주문 금액
            person_count     INTEGER DEFAULT 1,
            order_status     TEXT    DEFAULT 'pending',   -- pending/completed/cancelled
            ordered_at       TEXT    DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (history_id) REFERENCES recommendation_history(history_id),
            FOREIGN KEY (store_id)   REFERENCES store(store_id),
            FOREIGN KEY (menu_id)    REFERENCES menu(menu_id)
        )
    """)

    # ─────────────────────────────────────────────
    # 7. 인덱스 생성 (조회 성능 최적화)
    # ─────────────────────────────────────────────
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_category   ON menu(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_price      ON menu(price_range_min, price_range_max)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_kakao     ON store(kakao_place_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_store_location  ON store(latitude, longitude)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_session ON recommendation_history(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_date    ON recommendation_history(recommendation_date)")

    print("[DB] 모든 테이블 및 인덱스 생성 완료")


def insert_initial_data():
    """
    초기 메뉴 데이터 삽입
    실제 서비스에서는 관리자 도구나 CSV import로 대체
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    print("[DB] 초기 데이터 삽입 중...")

    # ── 음식 카테고리 삽입 ──────────────────────────
    categories = [
        ("한식", "한국 전통 음식"),
        ("양식", "서양 음식 (파스타, 스테이크 등)"),
        ("중식", "중국 음식 (짜장면, 탕수육 등)"),
        ("일식", "일본 음식 (초밥, 라멘 등)"),
        ("아시안", "동남아 음식 (쌀국수, 팟타이 등)"),
        ("패스트푸드", "버거, 피자, 치킨 등"),
        ("분식", "떡볶이, 순대, 김밥 등"),
        ("카페/디저트", "카페, 케이크, 빙수 등")
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO food_category (category_name, description) VALUES (?, ?)",
        categories
    )

    # ── 카테고리 ID 조회 ────────────────────────────
    cursor.execute("SELECT category_id, category_name FROM food_category")
    cat_map = {row[1]: row[0] for row in cursor.fetchall()}

    # ── 메뉴 데이터 삽입 ────────────────────────────
    # 형식: (메뉴명, 카테고리명, 최소가격, 최대가격, 밥기반, 면기반,
    #        설명, 알레르기JSON, 영양정보JSON, 혼밥가능, 단체가능)
    menus = [
        # ── 한식 ──────────────────────────────────
        ("비빔밥", "한식", 7000, 12000, 1, 0,
         "각종 나물과 고추장을 넣어 비벼먹는 한국 전통 음식",
         json.dumps(["egg", "sesame"], ensure_ascii=False),
         json.dumps({"calories": 550, "protein": 18, "carbs": 80, "fat": 12}, ensure_ascii=False),
         1, 1),
        ("삼겹살", "한식", 12000, 20000, 0, 0,
         "구워먹는 돼지고기 삼겹살. 쌈채소와 함께 즐기는 한국 대표 회식 메뉴",
         json.dumps(["pork"], ensure_ascii=False),
         json.dumps({"calories": 800, "protein": 40, "carbs": 5, "fat": 65}, ensure_ascii=False),
         0, 1),
        ("김치찌개", "한식", 7000, 13000, 1, 0,
         "김치와 돼지고기로 끓인 얼큰한 찌개",
         json.dumps(["pork", "gluten"], ensure_ascii=False),
         json.dumps({"calories": 420, "protein": 22, "carbs": 35, "fat": 18}, ensure_ascii=False),
         1, 1),
        ("된장찌개", "한식", 6000, 11000, 1, 0,
         "된장으로 끓인 구수한 찌개. 한국인의 소울푸드",
         json.dumps(["soy", "gluten"], ensure_ascii=False),
         json.dumps({"calories": 350, "protein": 15, "carbs": 28, "fat": 12}, ensure_ascii=False),
         1, 1),
        ("불고기", "한식", 12000, 20000, 1, 0,
         "간장 양념에 재운 소고기를 구운 달콤한 고기 요리",
         json.dumps(["beef", "soy", "gluten"], ensure_ascii=False),
         json.dumps({"calories": 650, "protein": 35, "carbs": 25, "fat": 38}, ensure_ascii=False),
         1, 1),
        ("냉면", "한식", 8000, 14000, 0, 1,
         "차가운 육수에 메밀면을 넣은 여름 대표 음식",
         json.dumps(["gluten", "beef"], ensure_ascii=False),
         json.dumps({"calories": 450, "protein": 20, "carbs": 70, "fat": 8}, ensure_ascii=False),
         1, 1),
        ("갈비탕", "한식", 12000, 18000, 1, 0,
         "소갈비를 오랫동안 끓인 진한 국물 요리",
         json.dumps(["beef"], ensure_ascii=False),
         json.dumps({"calories": 580, "protein": 42, "carbs": 30, "fat": 22}, ensure_ascii=False),
         1, 1),
        ("제육볶음", "한식", 8000, 13000, 1, 0,
         "고추장 양념에 볶은 돼지고기. 매콤하고 밥반찬으로 최고",
         json.dumps(["pork", "gluten", "soy"], ensure_ascii=False),
         json.dumps({"calories": 520, "protein": 28, "carbs": 40, "fat": 22}, ensure_ascii=False),
         1, 1),
        ("순두부찌개", "한식", 7000, 12000, 1, 0,
         "부드러운 순두부로 끓인 매콤한 찌개",
         json.dumps(["soy", "egg", "shellfish"], ensure_ascii=False),
         json.dumps({"calories": 380, "protein": 20, "carbs": 25, "fat": 18}, ensure_ascii=False),
         1, 1),
        ("설렁탕", "한식", 10000, 16000, 1, 0,
         "소 뼈와 사태를 오랫동안 끓인 뽀얀 국물 요리",
         json.dumps(["beef", "gluten"], ensure_ascii=False),
         json.dumps({"calories": 500, "protein": 38, "carbs": 35, "fat": 20}, ensure_ascii=False),
         1, 1),

        # ── 양식 ──────────────────────────────────
        ("파스타", "양식", 10000, 20000, 0, 1,
         "다양한 소스와 함께 즐기는 이탈리아 면 요리",
         json.dumps(["gluten", "dairy", "egg"], ensure_ascii=False),
         json.dumps({"calories": 650, "protein": 22, "carbs": 80, "fat": 25}, ensure_ascii=False),
         1, 1),
        ("스테이크", "양식", 25000, 50000, 0, 0,
         "두꺼운 소고기를 구운 고급 요리",
         json.dumps(["beef", "dairy"], ensure_ascii=False),
         json.dumps({"calories": 750, "protein": 55, "carbs": 5, "fat": 45}, ensure_ascii=False),
         1, 1),
        ("피자", "양식", 15000, 30000, 0, 0,
         "치즈와 다양한 토핑을 올린 이탈리아 음식",
         json.dumps(["gluten", "dairy"], ensure_ascii=False),
         json.dumps({"calories": 700, "protein": 28, "carbs": 75, "fat": 32}, ensure_ascii=False),
         0, 1),
        ("리소토", "양식", 14000, 22000, 1, 0,
         "쌀을 육수에 끓인 이탈리아 쌀 요리",
         json.dumps(["dairy", "gluten"], ensure_ascii=False),
         json.dumps({"calories": 600, "protein": 18, "carbs": 75, "fat": 22}, ensure_ascii=False),
         1, 1),
        ("함박스테이크", "양식", 12000, 20000, 1, 0,
         "다진 고기로 만든 부드러운 스테이크. 데미글라스 소스와 함께",
         json.dumps(["beef", "pork", "egg", "gluten"], ensure_ascii=False),
         json.dumps({"calories": 680, "protein": 32, "carbs": 45, "fat": 35}, ensure_ascii=False),
         1, 1),

        # ── 중식 ──────────────────────────────────
        ("짜장면", "중식", 6000, 10000, 0, 1,
         "춘장 소스를 넣은 중국 면 요리. 한국화된 대표 외식 메뉴",
         json.dumps(["gluten", "pork", "soy"], ensure_ascii=False),
         json.dumps({"calories": 620, "protein": 18, "carbs": 90, "fat": 18}, ensure_ascii=False),
         1, 1),
        ("짬뽕", "중식", 7000, 12000, 0, 1,
         "해물과 채소를 넣은 매콤한 중국 면 요리",
         json.dumps(["gluten", "shellfish", "pork"], ensure_ascii=False),
         json.dumps({"calories": 550, "protein": 25, "carbs": 75, "fat": 15}, ensure_ascii=False),
         1, 1),
        ("탕수육", "중식", 15000, 25000, 0, 0,
         "바삭하게 튀긴 돼지고기에 새콤달콤한 소스를 뿌린 요리",
         json.dumps(["pork", "gluten", "egg"], ensure_ascii=False),
         json.dumps({"calories": 750, "protein": 32, "carbs": 65, "fat": 38}, ensure_ascii=False),
         0, 1),
        ("마파두부", "중식", 8000, 14000, 1, 0,
         "두부와 다진 고기를 매콤하게 볶은 쓰촨 요리",
         json.dumps(["soy", "pork", "gluten"], ensure_ascii=False),
         json.dumps({"calories": 480, "protein": 22, "carbs": 40, "fat": 25}, ensure_ascii=False),
         1, 1),
        ("북경오리", "중식", 30000, 60000, 0, 0,
         "껍질이 바삭한 오리 요리. 춘장과 함께 먹는 고급 중식",
         json.dumps(["gluten"], ensure_ascii=False),
         json.dumps({"calories": 850, "protein": 48, "carbs": 25, "fat": 55}, ensure_ascii=False),
         0, 1),

        # ── 일식 ──────────────────────────────────
        ("초밥", "일식", 15000, 35000, 1, 0,
         "신선한 생선을 올린 일본 전통 음식",
         json.dumps(["fish", "shellfish", "gluten", "sesame"], ensure_ascii=False),
         json.dumps({"calories": 500, "protein": 30, "carbs": 60, "fat": 10}, ensure_ascii=False),
         1, 1),
        ("라멘", "일식", 9000, 16000, 0, 1,
         "진한 국물에 쫄깃한 면을 넣은 일본 국수",
         json.dumps(["gluten", "pork", "egg", "soy"], ensure_ascii=False),
         json.dumps({"calories": 700, "protein": 28, "carbs": 85, "fat": 28}, ensure_ascii=False),
         1, 1),
        ("돈카츠", "일식", 9000, 16000, 1, 0,
         "두꺼운 돼지고기를 빵가루에 튀긴 요리",
         json.dumps(["pork", "gluten", "egg"], ensure_ascii=False),
         json.dumps({"calories": 720, "protein": 35, "carbs": 65, "fat": 35}, ensure_ascii=False),
         1, 1),
        ("우동", "일식", 7000, 13000, 0, 1,
         "굵은 면을 부드러운 국물에 넣은 일본 면 요리",
         json.dumps(["gluten", "fish"], ensure_ascii=False),
         json.dumps({"calories": 480, "protein": 15, "carbs": 85, "fat": 8}, ensure_ascii=False),
         1, 1),
        ("카레", "일식", 8000, 14000, 1, 0,
         "향신료로 만든 소스를 밥에 얹은 요리",
         json.dumps(["gluten", "dairy"], ensure_ascii=False),
         json.dumps({"calories": 620, "protein": 22, "carbs": 85, "fat": 20}, ensure_ascii=False),
         1, 1),
        ("오마카세", "일식", 50000, 200000, 1, 0,
         "셰프가 선택하는 최고급 일식 코스 요리",
         json.dumps(["fish", "shellfish", "gluten", "sesame", "soy"], ensure_ascii=False),
         json.dumps({"calories": 1200, "protein": 80, "carbs": 120, "fat": 45}, ensure_ascii=False),
         1, 0),

        # ── 아시안 ────────────────────────────────
        ("쌀국수", "아시안", 8000, 14000, 0, 1,
         "베트남 쌀면 국수. 고수와 함께 먹는 담백한 음식",
         json.dumps(["fish"], ensure_ascii=False),
         json.dumps({"calories": 420, "protein": 22, "carbs": 65, "fat": 8}, ensure_ascii=False),
         1, 1),
        ("팟타이", "아시안", 9000, 15000, 0, 1,
         "타이 볶음 쌀국수. 땅콩과 함께 먹는 새콤달콤한 요리",
         json.dumps(["nuts", "shellfish", "fish", "egg"], ensure_ascii=False),
         json.dumps({"calories": 580, "protein": 25, "carbs": 70, "fat": 22}, ensure_ascii=False),
         1, 1),
        ("나시고렝", "아시안", 9000, 15000, 1, 0,
         "인도네시아식 볶음밥. 새우와 채소가 들어간 매콤한 요리",
         json.dumps(["shellfish", "egg", "soy"], ensure_ascii=False),
         json.dumps({"calories": 550, "protein": 20, "carbs": 75, "fat": 18}, ensure_ascii=False),
         1, 1),

        # ── 패스트푸드 ────────────────────────────
        ("버거", "패스트푸드", 5000, 12000, 0, 0,
         "패티와 채소를 빵 사이에 넣은 서양 패스트푸드",
         json.dumps(["gluten", "beef", "dairy", "egg"], ensure_ascii=False),
         json.dumps({"calories": 650, "protein": 28, "carbs": 60, "fat": 35}, ensure_ascii=False),
         1, 1),
        ("치킨", "패스트푸드", 18000, 28000, 0, 0,
         "바삭하게 튀기거나 구운 닭고기",
         json.dumps(["gluten", "egg"], ensure_ascii=False),
         json.dumps({"calories": 750, "protein": 45, "carbs": 40, "fat": 42}, ensure_ascii=False),
         0, 1),

        # ── 분식 ──────────────────────────────────
        ("떡볶이", "분식", 3000, 7000, 0, 0,
         "쫄깃한 떡을 매운 양념에 볶은 한국 대표 간식",
         json.dumps(["gluten", "fish"], ensure_ascii=False),
         json.dumps({"calories": 380, "protein": 8, "carbs": 75, "fat": 6}, ensure_ascii=False),
         1, 1),
        ("김밥", "분식", 2500, 6000, 1, 0,
         "밥과 다양한 재료를 김에 만 간편식",
         json.dumps(["sesame", "egg", "fish"], ensure_ascii=False),
         json.dumps({"calories": 350, "protein": 12, "carbs": 55, "fat": 8}, ensure_ascii=False),
         1, 1),
    ]

    # 메뉴 삽입 (이미 있으면 무시)
    for menu in menus:
        (menu_name, cat_name, price_min, price_max, is_rice, is_noodle,
         desc, allergy, nutrition, solo, group) = menu

        cat_id = cat_map.get(cat_name)
        if not cat_id:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO menu
            (menu_name, category_id, price_range_min, price_range_max,
             is_rice_based, is_noodle_based, description, allergy_info,
             nutrition_info, is_solo_friendly, is_group_friendly)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (menu_name, cat_id, price_min, price_max, is_rice, is_noodle,
              desc, allergy, nutrition, solo, group))

    conn.commit()
    conn.close()
    print(f"[DB] 초기 데이터 삽입 완료: {len(menus)}개 메뉴, {len(categories)}개 카테고리")


def reset_database():
    """개발/테스트용: 데이터베이스를 완전히 초기화하고 재생성"""
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print("[DB] 기존 데이터베이스 삭제 완료")
    create_database()
    insert_initial_data()
    print("[DB] 데이터베이스 초기화 완료!")


if __name__ == "__main__":
    reset_database()
