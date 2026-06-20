@echo off
chcp 65001 >nul
REM ============================================================
REM run.bat
REM ============================================================
REM U-RE EATS 더블클릭 실행 스크립트 (Windows 전용)
REM
REM 이 파일을 더블클릭하면 아래 순서로 자동 실행됩니다:
REM   1. Python 설치 여부 확인
REM   2. 가상환경(venv) 존재 확인 -> 없으면 새로 생성 + 라이브러리 설치 (최초 1회만)
REM   3. main.py 실행 (GUI 창이 뜸)
REM
REM 오류가 나도 창이 바로 닫히지 않고 메시지를 보여준 뒤 대기합니다.
REM ============================================================

title U-RE EATS 실행 중...
cd /d "%~dp0"

echo ============================================================
echo   U-RE EATS 를 준비하고 있습니다. 잠시만 기다려주세요...
echo ============================================================
echo.

REM ── 1. Python 설치 여부 확인 ──────────────────────────────
where python >nul 2>nul
if errorlevel 1 (
    echo [오류] Python 이 설치되어 있지 않거나 PATH 에 등록되지 않았습니다.
    echo.
    echo   해결 방법:
    echo   1^) https://www.python.org/downloads/ 에서 Python 을 설치하세요.
    echo   2^) 설치 화면에서 "Add python.exe to PATH" 체크박스를 반드시 체크하세요.
    echo   3^) 설치 후 이 파일을 다시 더블클릭하세요.
    echo.
    pause
    exit /b 1
)

REM ── 2. 가상환경(venv) 확인 및 생성 ─────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo [최초 실행] 가상환경을 새로 만듭니다. 시간이 조금 걸릴 수 있습니다...
    echo.

    python -m venv venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성에 실패했습니다.
        pause
        exit /b 1
    )

    call venv\Scripts\activate.bat

    echo.
    echo [최초 실행] 필요한 라이브러리를 설치합니다...
    echo.

    python -m pip install --upgrade pip >nul
    pip install -r requirements.txt

    if errorlevel 1 (
        echo.
        echo [오류] 라이브러리 설치에 실패했습니다. 인터넷 연결을 확인해주세요.
        pause
        exit /b 1
    )

    echo.
    echo [완료] 최초 설정이 끝났습니다. 다음부터는 더 빠르게 실행됩니다.
    echo.
) else (
    call venv\Scripts\activate.bat
)

REM ── 3. 메인 프로그램 실행 ─────────────────────────────────
echo ============================================================
echo   U-RE EATS 를 실행합니다...
echo ============================================================
echo.

python main.py

REM ── 4. 오류 발생 시 창이 바로 닫히지 않도록 대기 ────────────
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   프로그램이 오류와 함께 종료되었습니다.
    echo   위에 표시된 오류 메시지를 확인해주세요.
    echo ============================================================
    echo.
    pause
)
