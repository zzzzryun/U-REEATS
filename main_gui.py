"""
main.py
========
U-RE EATS GUI 버전의 진입점

기존 CLI 버전(input() 기반)에서 Tkinter GUI 버전으로 전환됨.
실행 방법은 동일: python main.py

실행 흐름:
1. DB 초기화 확인 (없으면 자동 생성 - 기존 CLI와 동일한 로직)
2. tk.Tk() 메인 윈도우 생성
3. gui.app.App 인스턴스 생성 (1단계 화면부터 시작)
4. root.mainloop()로 이벤트 루프 시작 (여기서부터는 모든 동작이
   버튼 클릭 등의 이벤트에 의해 트리거됨 - input()으로 멈춰서 기다리던
   CLI와는 근본적으로 다른 실행 모델)
"""

import os
import sys
import tkinter as tk
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.schema import create_database, insert_initial_data
from database.connection import check_database_exists
from gui.app import App

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(name)s: %(message)s")
logger = logging.getLogger("main")


def initialize_database():
    """앱 시작 전 DB 존재 여부를 확인하고 없으면 자동 생성 (CLI 버전과 동일한 로직)"""
    if not check_database_exists():
        logger.info("처음 실행을 감지했습니다. 데이터베이스를 초기화합니다...")
        create_database()
        insert_initial_data()
        logger.info("데이터베이스 초기화 완료!")


def main():
    """GUI 애플리케이션의 진입점"""
    initialize_database()

    root = tk.Tk()
    app = App(root)

    # mainloop() 호출 시점부터 프로그램은 이벤트 루프 안으로 들어가서
    # 사용자의 버튼 클릭, 창 닫기 등의 이벤트를 계속 기다리며 반응함.
    # CLI 버전의 while True + input() 루프와 동일한 역할을 하지만,
    # 콘솔 입력이 아니라 GUI 이벤트에 반응한다는 점이 다름.
    root.mainloop()


if __name__ == "__main__":
    main()
