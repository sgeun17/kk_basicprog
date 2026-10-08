"""수강 신청·취소, 학생 메뉴, 강사 메뉴 — 담당 4 (중복 수강 검사는 5)

기획서 6.4 학생 메뉴, 6.5 강사 메뉴, 6.6.5 수강 등록 조회·취소를 구현한다.

이 파일은 data.py, ui.py, errors.py 만 import 한다.
admin.py 는 import 하지 않는다. 반 정원과 수업 시간은 data.read_classes() 로 읽고,
수강 인원은 data.count_enrolled(class_id) 로 센다.
admin.py 를 import 하면 둘이 서로 기대게 되어 구조를 설명하기 어려워지고,
"from admin import ..." 로 쓰면 실제로 켜지지 않는다.

메뉴에 연결되는 함수는 로그인한 사용자 레코드를 인자로 받는다.
    def enroll_class(user): ...
함수를 만들면 이름을 노션에 적어서 1 에게 알린다.
"""

import data
import errors
import ui


# ---- 6.4 학생 메뉴 ----


# ---- 6.5 강사 메뉴 ----


# ---- 6.6.5 수강 등록 조회·취소 (원장) ----
