"""
gui/state.py
=============
GUI 마법사가 진행되는 동안 사용자 입력을 누적해서 들고 다니는 공유 상태 클래스

CLI 버전에서는 collect_all_user_input()이 함수 호출을 순서대로 실행하면서
딕셔너리를 한 번에 채웠지만, GUI는 화면(Frame)이 하나씩 교체되는 방식이라
"지금까지 입력한 값"을 어딘가에 들고 있어야 함. 이 클래스가 그 역할을 담당.

설계 의도:
- AppState 인스턴스 하나를 모든 화면(Frame)이 공유함
- 각 화면은 '다음' 버튼을 누를 때 자신이 담당하는 항목만 이 객체에 기록
- 마지막 화면(결과 화면)에 도달하면 이 객체를 user_conditions 딕셔너리로 변환해서
  기존 CLI와 동일한 추천 로직(recommend_menu, get_restaurant_recommendation)에 그대로 전달
"""


class AppState:
    """
    마법사 진행 중 사용자가 입력한 값을 누적하는 컨테이너

    속성은 modules/user_input.py의 9개 입력 함수가 반환하던 값과 1:1로 대응됨:
        select_cuisine_type()      → cuisine_type
        select_noodle_or_rice()    → food_base
        input_price_range()        → price_range
        input_excluded_menu()      → excluded_menus
        input_preferred_menu()     → preferred_menus
        input_person_count()       → person_count
        select_location()          → location
        input_additional_profile() → allergies
    """

    def __init__(self):
        self.reset()

    def reset(self):
        """
        새로운 추천 사이클을 시작할 때 모든 입력값을 초기 상태로 되돌림
        ('처음부터 다시 조건 입력하기'를 선택했을 때 호출됨)
        """
        self.cuisine_type: str = "전체"
        self.food_base: str | None = None
        self.price_range: dict = {"label": "전체", "min": 0, "max": 999999}
        self.excluded_menus: list[str] = []
        self.preferred_menus: list[str] = []
        self.person_count: int = 1
        self.location: dict = {}
        self.allergies: list[str] = []

        # 마법사 흐름 제어용 (GUI 전용 - CLI에는 없던 개념)
        self.shown_menu_ids: set = set()   # '다른 메뉴 추천' 시 중복 방지용
        self.last_top_menu: dict | None = None
        self.last_stores: list = []

    def to_user_conditions(self) -> dict:
        """
        AppState를 기존 추천 로직(recommend_menu 등)이 기대하는
        user_conditions 딕셔너리 형식으로 변환

        Returns:
            dict: modules/menu_recommendation.py, modules/restaurant_search.py가
                  바로 받아서 쓸 수 있는 형식
        """
        return {
            "cuisine_type": self.cuisine_type,
            "food_base": self.food_base,
            "price_range": self.price_range,
            "excluded_menus": self.excluded_menus,
            "preferred_menus": self.preferred_menus,
            "person_count": self.person_count,
            "location": self.location,
            "allergies": self.allergies,
        }
