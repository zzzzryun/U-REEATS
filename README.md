# 🍴 U-RE EATS

개인 맞춤형 메뉴 & 음식점 추천 시스템

## 폴더 구조

```
u_re_eats/
├── main.py                  ← 앱 실행 진입점
├── requirements.txt         ← 필요한 라이브러리
│
├── config/                  ← 전역 설정 패키지
│   ├── __init__.py
│   └── settings.py          ← API 키, 상수, 경로 설정
│
├── database/                ← DB 관련 패키지
│   ├── __init__.py
│   ├── schema.py            ← 테이블 생성 & 초기 데이터
│   └── connection.py        ← DB 연결 관리
│
├── modules/                 ← 핵심 기능 패키지
│   ├── __init__.py
│   ├── user_input.py        ← 사용자 입력 수집
│   ├── menu_recommendation.py ← 메뉴 추천 엔진
│   ├── restaurant_search.py ← 음식점 검색 & 랭킹
│   └── output.py            ← 결과 출력 & 이력 저장
│
├── utils/                   ← 공통 유틸 패키지
│   ├── __init__.py
│   ├── helpers.py           ← 거리계산, 포맷팅 등
│   └── kakao_api.py         ← 카카오 API 연동
│
└── tests/                   ← 테스트 패키지
    ├── __init__.py
    └── test_modules.py      ← 단위 테스트
```

## 실행 방법

```bash
# 1. 라이브러리 설치
pip install -r requirements.txt

# 2. 카카오 API 키 설정 (config/settings.py에서 직접 수정하거나 환경변수 사용)
export KAKAO_REST_API_KEY=your_key_here

# 3. 앱 실행
python main.py

# 4. 테스트 실행
python tests/test_modules.py
```

## API 키 없이 실행

카카오 API 키가 없어도 목업(Mock) 데이터로 실행됩니다.
`config/settings.py`의 `KAKAO_REST_API_KEY`가 기본값이면 자동으로 목업 모드로 전환됩니다.
