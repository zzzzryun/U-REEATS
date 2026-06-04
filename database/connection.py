"""
database/connection.py
======================
데이터베이스 연결을 중앙에서 관리하는 모듈

설계 원칙:
- 컨텍스트 매니저(with 문)를 통한 안전한 연결 관리
- 커넥션 풀링을 시뮬레이션하는 단순 팩토리 패턴
- Row를 딕셔너리로 반환하여 코드 가독성 향상
"""

import sqlite3
import os
import sys
import logging
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """
    SQLite 데이터베이스 연결을 반환하는 팩토리 함수

    Returns:
        sqlite3.Connection: 설정이 완료된 DB 연결 객체

    주의: 이 함수로 얻은 연결은 반드시 .close() 해야 합니다.
          가능하면 get_db_context()를 사용하세요.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row   # 결과를 딕셔너리처럼 접근 가능하게 설정
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_db_context():
    """
    컨텍스트 매니저를 통한 안전한 DB 연결 관리

    사용 예시:
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM menu")
            rows = cursor.fetchall()

    예외 발생 시 자동 롤백, 정상 종료 시 자동 커밋 및 연결 해제
    """
    conn = None
    try:
        conn = get_connection()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"데이터베이스 오류 발생: {e}")
        raise
    finally:
        if conn:
            conn.close()


def execute_query(query: str, params: tuple = ()) -> list:
    """
    단일 SELECT 쿼리를 실행하고 결과를 딕셔너리 리스트로 반환

    Args:
        query: 실행할 SQL 쿼리 문자열
        params: 바인딩할 파라미터 튜플 (SQL 인젝션 방지)

    Returns:
        list[dict]: 조회 결과 딕셔너리 목록
    """
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        # sqlite3.Row 객체를 일반 dict로 변환
        return [dict(row) for row in rows]


def execute_write(query: str, params: tuple = ()) -> int:
    """
    INSERT/UPDATE/DELETE 쿼리를 실행하고 영향받은 행 수를 반환

    Args:
        query: 실행할 SQL 쿼리 문자열
        params: 바인딩할 파라미터 튜플

    Returns:
        int: 마지막 삽입된 row의 ID (INSERT의 경우) 또는 영향받은 행 수
    """
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def check_database_exists() -> bool:
    """데이터베이스 파일 존재 여부 확인"""
    return os.path.exists(DATABASE_PATH)
