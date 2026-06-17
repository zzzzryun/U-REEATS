"""
utils/browser_location.py
==========================
브라우저의 위치 권한(Geolocation API)을 활용한 정밀 위치 감지 모듈

배경:
- 순수 Python 콘솔 앱은 OS의 GPS/Wi-Fi 기반 위치 권한 체계에 직접 접근할 수 없음
- 그러나 모든 PC에는 웹 브라우저가 있고, 브라우저는 navigator.geolocation API로
  Wi-Fi 신호 기반의 정밀한 위치(보통 10~50m 오차)를 얻을 수 있음
- 이 모듈은 Python이 임시 HTML 페이지를 브라우저로 띄우고,
  사용자가 위치 허용을 누르면 그 좌표를 다시 Python으로 돌려받는 다리 역할을 함

동작 흐름:
1. 로컬 PC에서만 동작하는 임시 HTTP 서버를 백그라운드 스레드로 띄움 (예: localhost:8765)
2. 그 서버가 제공하는 HTML 페이지를 기본 브라우저로 자동으로 엶
3. 페이지가 navigator.geolocation.getCurrentPosition()을 호출 → 브라우저가 권한 팝업 표시
4. 사용자가 "허용"을 누르면 좌표를 JavaScript가 서버로 자동 전송
5. Python 쪽에서 좌표를 받으면 서버를 종료하고 결과를 반환

주의:
- 사용자가 권한을 거부하거나 30초 내 응답이 없으면 None을 반환 (타임아웃 처리)
- 이 방식은 외부 네트워크 통신이 필요 없음 (전부 localhost 내부에서만 동작)
"""

import http.server
import threading
import webbrowser
import socket
import time
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 결과를 스레드 간에 안전하게 주고받기 위한 공유 컨테이너
_location_result = {"data": None, "received": False}
_result_lock = threading.Lock()


def _find_free_port(start_port: int = 8765) -> int:
    """
    사용 가능한 빈 포트를 찾는 함수

    다른 프로그램이 8765 포트를 이미 쓰고 있을 경우를 대비해
    8765부터 순서대로 비어있는 포트를 탐색

    Args:
        start_port: 탐색을 시작할 포트 번호

    Returns:
        int: 사용 가능한 포트 번호
    """
    port = start_port
    for _ in range(20):  # 최대 20개 포트까지만 시도
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                port += 1
    return start_port  # 전부 실패하면 기본값 그대로 시도


def _build_location_html() -> str:
    """
    브라우저에서 위치 권한을 요청하고 결과를 서버로 전송하는 HTML 페이지를 생성

    Returns:
        str: 완성된 HTML 문자열
    """
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>U-RE EATS 위치 확인</title>
<style>
  body {
    font-family: -apple-system, "Malgun Gothic", sans-serif;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; height: 90vh; margin: 0; text-align: center;
    background: #fafaf8; color: #2c2c2a;
  }
  .icon { font-size: 48px; margin-bottom: 16px; }
  h2 { margin: 0 0 8px; }
  p { color: #5f5e5a; max-width: 320px; line-height: 1.6; }
  .status { margin-top: 24px; font-size: 14px; color: #888780; }
</style>
</head>
<body>
  <div class="icon">📍</div>
  <h2>U-RE EATS</h2>
  <p id="message">현재 위치를 확인하기 위해 브라우저의 위치 권한이 필요합니다.<br>
     화면에 뜨는 팝업에서 <b>'허용'</b>을 눌러주세요.</p>
  <div class="status" id="status">권한 요청 중...</div>

<script>
function sendResult(payload) {
  fetch('/location', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  }).then(() => {
    document.getElementById('message').innerHTML =
      payload.success
        ? '위치 확인이 완료되었습니다.<br>이 창은 닫으셔도 됩니다.'
        : '위치 확인에 실패했습니다.<br>이 창을 닫고 콘솔로 돌아가주세요.';
    document.getElementById('status').innerText = '';
  }).catch(() => {
    document.getElementById('status').innerText = '서버 연결 오류';
  });
}

if (!navigator.geolocation) {
  document.getElementById('status').innerText = '이 브라우저는 위치 기능을 지원하지 않습니다.';
  sendResult({success: false, error: 'unsupported'});
} else {
  navigator.geolocation.getCurrentPosition(
    function(position) {
      sendResult({
        success: true,
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy
      });
    },
    function(error) {
      // error.code: 1=권한거부, 2=위치확인불가, 3=시간초과
      document.getElementById('status').innerText = '권한이 거부되었거나 위치를 확인할 수 없습니다.';
      sendResult({success: false, error: 'denied', code: error.code});
    },
    {enableHighAccuracy: true, timeout: 15000, maximumAge: 0}
  );
}
</script>
</body>
</html>"""


class _LocationRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    브라우저 요청을 처리하는 내부 HTTP 핸들러

    두 가지 경로를 처리:
    - GET  /         → 위치 권한을 요청하는 HTML 페이지 응답
    - POST /location  → 브라우저가 보낸 좌표 데이터를 수신
    """

    def log_message(self, format, *args):
        # 콘솔에 불필요한 HTTP 서버 로그가 출력되지 않도록 무시
        pass

    def do_GET(self):
        if self.path == "/":
            html = _build_location_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/location":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                payload = {"success": False, "error": "invalid_json"}

            with _result_lock:
                _location_result["data"] = payload
                _location_result["received"] = True

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": true}')
        else:
            self.send_response(404)
            self.end_headers()


def get_precise_location_via_browser(timeout_seconds: int = 30) -> Optional[dict]:
    """
    브라우저의 위치 권한을 통해 정밀한 현재 위치를 가져오는 함수

    동작 과정:
    1. 로컬호스트에 임시 웹서버 실행
    2. 기본 브라우저로 위치 요청 페이지를 자동으로 엶
    3. 사용자가 브라우저 팝업에서 '허용'을 누르면 좌표 수신
    4. 좌표를 받으면 즉시 서버 종료 후 반환

    Args:
        timeout_seconds: 사용자 응답을 기다리는 최대 시간 (초)

    Returns:
        Optional[dict]: 성공 시 {'latitude': float, 'longitude': float, 'accuracy': float}
                        실패/타임아웃/거부 시 None
    """
    global _location_result
    _location_result = {"data": None, "received": False}

    port = _find_free_port()
    server = http.server.HTTPServer(("localhost", port), _LocationRequestHandler)

    # 서버를 백그라운드 스레드에서 실행 (메인 스레드는 사용자 응답을 기다림)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://localhost:{port}/"
    print(f"  🌐 브라우저를 열어 위치 권한을 요청합니다...")
    print(f"     (자동으로 열리지 않으면 이 주소를 브라우저에 직접 입력하세요: {url})")

    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"  ⚠️  브라우저를 자동으로 열지 못했습니다: {e}")
        print(f"     위 주소를 직접 브라우저에 입력해주세요.")

    # 사용자가 권한을 허용/거부할 때까지 대기 (0.5초 간격으로 확인)
    waited = 0.0
    while waited < timeout_seconds:
        with _result_lock:
            if _location_result["received"]:
                break
        time.sleep(0.5)
        waited += 0.5

    server.shutdown()
    server.server_close()

    with _result_lock:
        result = _location_result["data"]

    if result is None:
        print(f"  ⚠️  {timeout_seconds}초 동안 응답이 없어 시간 초과되었습니다.")
        return None

    if not result.get("success"):
        error_type = result.get("error", "unknown")
        if error_type == "denied":
            print(f"  ⚠️  위치 권한이 거부되었습니다.")
        else:
            print(f"  ⚠️  위치 확인에 실패했습니다. (오류: {error_type})")
        return None

    latitude = result.get("latitude")
    longitude = result.get("longitude")
    accuracy = result.get("accuracy", 0)

    print(f"  ✅ 정밀 위치 확인 완료! (오차 범위: 약 {accuracy:.0f}m)")

    return {
        "latitude": float(latitude),
        "longitude": float(longitude),
        "accuracy": float(accuracy)
    }
