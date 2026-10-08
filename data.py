"""데이터 파일 읽기·쓰기, 값 검사, 무결성 검사, 공통 계산 — 담당 2

기획서 4장(데이터 요소), 5장(데이터 파일)을 구현한다.
다른 파일에서는 이렇게 부른다.

    import data
    users = data.read_users()
    if not data.is_phone(phone): ...

이 파일은 errors.py 만 import 한다.
admin.py 와 enrollment.py 가 둘 다 필요한 계산(수강 인원 세기, 시간 충돌 등)은
여기에 둔다. 둘이 서로를 import 하면 누가 누구에게 기대는지 꼬이고,
"from admin import ..." 처럼 쓰는 순간 실제로 켜지지 않는다.

이미 동작하는 것: read_*, write_*, append_datetime, write_datetime, create_data_dir, cleanup_tmp, now
비어 있는 것: write_all, 값 검사, 비교·계산, 역행 판정, 무결성 검사
"""

import os
from pathlib import Path

import errors


# 데이터 폴더는 이 파일과 같은 폴더 아래의 data 다. (2.2)
# Path("data") 로 쓰면 "지금 터미널이 있는 폴더" 기준이 되어서,
# 다른 폴더에서 실행하면 엉뚱한 곳에 data 가 생긴다.
DATA = Path(__file__).resolve().parent / "data"

USERS       = DATA / "users.txt"
STUDENTS    = DATA / "students.txt"
TEACHERS    = DATA / "teachers.txt"
SUBJECTS    = DATA / "subjects.txt"
CLASSES     = DATA / "classes.txt"
ENROLLMENTS = DATA / "enrollments.txt"
DATETIME    = DATA / "datetime.txt"

HEADERS = {
    USERS:       ["사용자ID", "비밀번호", "사용자역할"],
    STUDENTS:    ["학생ID", "이름", "연락처", "사용자ID", "학생상태"],
    TEACHERS:    ["강사ID", "이름", "연락처", "사용자ID", "강사상태"],
    SUBJECTS:    ["과목ID", "과목명"],
    CLASSES:     ["반ID", "과목ID", "반이름", "강사ID", "요일목록",
                  "시작교시", "종료교시", "시작날짜", "종료날짜", "정원", "반상태"],
    ENROLLMENTS: ["등록ID", "학생ID", "반ID", "등록일시", "등록상태", "취소일시"],
}

EMPTY = "-"              # 5.1.8 빈 값
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]   # 4.11

# 4.1.2 내부 식별자 앞글자.  data.next_id(data.ID_STUDENT) 처럼 쓴다.
# next_id("S") 로 직접 치면 next_id("s") 오타를 아무도 못 잡는다.
ID_STUDENT    = "S"
ID_TEACHER    = "T"
ID_SUBJECT    = "P"
ID_CLASS      = "C"
ID_ENROLLMENT = "E"

# 저장할 때 쓰는 임시 파일 꼬리.  data/users.txt → data/users.txt.tmp
TMP_SUFFIX = ".tmp"


# ---- 파일 읽기 : 레코드 딕셔너리 리스트를 돌려준다 ----

def _read_text(path):
    """파일 전체를 문자열로 읽는다. 없음·권한·인코딩·BOM 을 검사한다. (5.4 ①②)"""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise errors.DataError(errors.E_FILE_MISSING, f"{path.name} 파일이 없습니다")
    except PermissionError:
        raise errors.DataError(errors.E_FILE_READ, f"{path.name} 을 읽을 권한이 없습니다")
    except UnicodeDecodeError:
        raise errors.DataError(errors.E_FILE_FORMAT, f"{path.name} 은 UTF-8 로 읽을 수 없습니다")

    # 5.1.1 BOM 없는 UTF-8.
    # 윈도우 메모장이 기본으로 BOM 을 붙이므로 손으로 고치면 자주 생긴다.
    if text.startswith("﻿"):
        raise errors.DataError(errors.E_FILE_FORMAT, f"{path.name} 맨 앞에 BOM 이 있습니다")
    return text


def _split_lines(path):
    """헤더가 있는 파일을 줄 목록으로 나눈다.

    여기서 검사하는 것은 BOM·인코딩·빈 파일뿐이다.
    빈 줄·필드 수·헤더는 _read_table 이 보고, 필드 값(빈 값은 "-", ID 형식 등)과
    레코드 수 상한(5.1, 최대 10,000개)은 무결성 검사 ④단계에서 본다.

    마지막 개행은 있어도 되고 없어도 된다. (5.1.10)
    그래서 끝의 빈 문자열 하나만 떼고, 그 뒤에 남은 빈 줄은 위반으로 본다.
    """
    text = _read_text(path)
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()                     # 5.1.10 마지막 개행 — 허용

    if not lines:
        raise errors.DataError(errors.E_FILE_FORMAT, f"{path.name} 이 비어 있습니다")

    return lines


def _read_table(path):
    """헤더가 있는 탭 구분 파일을 읽어 딕셔너리 리스트로 돌려준다. (5.1, 5.2)"""
    header = HEADERS[path]
    lines = _split_lines(path)

    # 5.2 첫 줄은 정해진 헤더여야 한다
    if lines[0] != "\t".join(header):
        raise errors.DataError(
            errors.E_FILE_FORMAT,
            f"{path.name} 1행: 헤더가 '{chr(9).join(header)}' 가 아닙니다",
        )

    records = []
    for lineno, line in enumerate(lines[1:], start=2):
        # 5.1.6 중간에 빈 줄을 두지 않는다
        if line == "":
            raise errors.DataError(errors.E_FILE_FORMAT, f"{path.name} {lineno}행: 빈 줄은 허용하지 않습니다")

        values = line.split("\t")
        # 5.1.5 필드 수가 헤더와 같아야 한다.
        #       여기서 막지 않으면 zip 이 짧은 쪽에서 끊어서
        #       키가 조용히 사라지고, 엉뚱한 데서 KeyError 가 난다.
        if len(values) != len(header):
            raise errors.DataError(
                errors.E_FILE_FORMAT,
                f"{path.name} {lineno}행: 필드 수가 {len(header)}개가 아니라 {len(values)}개입니다",
            )

        records.append(dict(zip(header, values)))

    return records


def read_users():        return _read_table(USERS)        # 5.2.1
def read_students():     return _read_table(STUDENTS)     # 5.2.2
def read_teachers():     return _read_table(TEACHERS)     # 5.2.3
def read_subjects():     return _read_table(SUBJECTS)     # 5.2.4
def read_classes():      return _read_table(CLASSES)      # 5.2.5
def read_enrollments():  return _read_table(ENROLLMENTS)  # 5.2.6


def read_datetime():
    """가상 현재 일시 이력. 한 줄에 한 일시, 헤더 없음. (5.2.7)

    마지막 줄이 지금의 가상 현재 일시다.
    """
    # 5.4 — "datetime.txt 의 이력 줄 자체가 손상된 경우(형식 위반·비정렬·
    # 마지막 줄이 이력보다 과거) 역시 E_TIME_BACKWARD 오류로 처리한다."
    # 그래서 빈 파일·빈 줄은 다른 파일과 달리 E_TIME_BACKWARD 다.
    # 파일이 없거나 UTF-8 이 아니면 다른 파일과 같다. (①②)
    lines = _read_text(DATETIME).split("\n")
    if lines and lines[-1] == "":
        lines.pop()                     # 5.1.10 마지막 개행 — 허용
    if not lines:
        raise errors.DataError(errors.E_TIME_BACKWARD, "datetime.txt 가 비어 있습니다")
    for lineno, line in enumerate(lines, start=1):
        if line == "":
            raise errors.DataError(errors.E_TIME_BACKWARD, f"datetime.txt {lineno}행: 빈 줄이 있습니다")
    return lines


def now():
    """지금의 가상 현재 일시. (README 팀 합의)

    담아두지 말고 쓸 때마다 이걸 부른다.
    변수에 담으면 6.3 에서 바꿨을 때 갱신을 잊고 틀린 값을 쓰게 된다.
    """
    return read_datetime()[-1]


# ---- 파일 쓰기 : 성공하면 True, 실패하면 False ----
#
# 실패해도 예외를 던지지 않는다. 부르는 쪽에서
#     if not data.write_students(students):
#         print(f"[{errors.E_SAVE}] {errors.ERROR_MESSAGES[errors.E_SAVE]}")

def _write_text(path, text):
    """임시 파일에 쓴 뒤 os.replace() 로 교체한다. (6.7)

    open(path, "w") 로 원본을 바로 열면 그 순간 내용이 비워진다.
    쓰는 중에 프로그램이 죽으면 반만 남은 파일이 된다.
    임시 파일에 다 쓰고 한 번에 바꾸면 중간 상태가 없어서,
    죽어도 원본은 이전 상태 그대로 남는다.
    """
    tmp = path.with_name(path.name + TMP_SUFFIX)
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, path)
    except Exception:
        # 5.4 — 실패하면 임시 파일을 지우고 원본은 건드리지 않는다.
        # 부르는 쪽은 False 를 받으면 [E_SAVE] 를 출력한다.
        try:
            os.remove(tmp)
        except OSError:
            pass
        return False
    return True


def _write_table(path, records):
    header = HEADERS[path]
    lines = ["\t".join(header)]
    for rec in records:
        lines.append("\t".join(rec[field] for field in header))
    return _write_text(path, "\n".join(lines) + "\n")


def write_users(records):        return _write_table(USERS, records)
def write_students(records):     return _write_table(STUDENTS, records)
def write_teachers(records):     return _write_table(TEACHERS, records)
def write_subjects(records):     return _write_table(SUBJECTS, records)
def write_classes(records):      return _write_table(CLASSES, records)
def write_enrollments(records):  return _write_table(ENROLLMENTS, records)


def create_data_dir():
    """최초 실행 2.3.1 의 1~2단계. data 폴더와 헤더만 있는 파일 6개를 만든다.

    이미 있으면 지우고 헤더만 있는 파일로 새로 쓴다. datetime.txt 와 남은 임시 파일도 지운다.
    최초 실행이 중간에 끊겨서 처음부터 다시 하는 경우(2.3.1 마지막 문단)를 위해서다.

    datetime.txt 는 여기서 만들지 않는다. 4단계에서 첫 가상 일시를 받아
    write_datetime 으로 만든다. 2.3.1 은 "datetime.txt 가 생성된 시점"을
    최초 실행 완료로 보기 때문에, 빈 datetime.txt 를 미리 만들면
    끊긴 최초 실행을 알아볼 수 없게 된다.
    """
    try:
        DATA.mkdir(exist_ok=True)
    except OSError:
        return False                    # 2.3 — 권한이 없으면 부르는 쪽이 메시지를 출력하고 종료
    # 2.3.1 — 다시 할 때는 "생성된 파일을 모두 삭제한 뒤" 처음부터 한다.
    # datetime.txt 를 남겨두면, 다시 하다가 또 끊겼을 때 옛날 값 때문에
    # 최초 실행이 끝난 것처럼 보인다.
    for leftover in [DATETIME] + [p.with_name(p.name + TMP_SUFFIX) for p in list(HEADERS) + [DATETIME]]:
        try:
            if leftover.exists():
                os.remove(leftover)
        except OSError:
            return False
    for path in HEADERS:
        if not _write_table(path, []):
            return False
    return True


def write_datetime(lines):
    """datetime.txt 를 통째로 쓴다.

    최초 실행 4단계에서 data.write_datetime([첫 가상 일시]) 로 부른다.
    실행 중에 가상 일시를 바꿀 때는 이 함수가 아니라 append_datetime 을 쓴다.
    """
    return _write_text(DATETIME, "\n".join(lines) + "\n")


def append_datetime(new_dt):
    """datetime.txt 끝에 한 줄 추가. 기존 줄은 건드리지 않는다. (4.14 저장)

    "a" 모드로 그냥 붙이면 안 된다.
    5.1.10 이 마지막 개행 없는 파일을 허용하므로,
    그런 파일에 붙이면 마지막 줄과 새 줄이 한 줄로 이어붙는다.
    그래서 읽어서 목록 끝에 더하고 전체를 다시 쓴다.
    """
    lines = read_datetime()
    # 4.14 — "변경 직전의 값과 동일한 값으로 재지정하는 것은 허용하며,
    # 이 경우 이력에 중복해서 기록하지 않는다."
    if lines[-1] == new_dt:
        return True
    lines.append(new_dt)
    return _write_text(DATETIME, "\n".join(lines) + "\n")


def cleanup_tmp():
    """지난 실행이 저장 도중 끊겨 남은 임시 파일을 지운다. (6.7.3)

    6.7.3 — "남은 임시 파일은 다음 실행 시작 시 정리한다."
    main.py 가 프로그램 시작 때 한 번 부른다.
    """
    if not DATA.exists():
        return True
    for tmp in DATA.glob("*" + TMP_SUFFIX):
        try:
            os.remove(tmp)
        except OSError:
            return False
    return True


def write_all(changes):
    """여러 파일을 함께 바꾼다. 전부 성공해야 교체한다. (5.4)

    5.4 — "변경 대상 파일 전부의 새 내용을 각각 임시 파일에 먼저 기록하고,
    모든 기록에 성공한 경우에만 교체를 시작한다. 하나라도 실패하면
    임시 파일을 모두 삭제하고 작업 전체를 실패로 처리한다."

    _write_text 는 파일 하나를 쓰고 바로 교체하므로 여기서 쓸 수 없다.
    쓰기 단계와 교체 단계를 나눠야 한다.
    """
    pass


# ---- 값 검증 : True / False ----
#
# 최초 실행과 로그인에 필요한 다섯 개(is_user_id, is_password, is_date, is_time, is_datetime)는
# 1 이 먼저 작성한다. 나머지는 2.
#
# 숫자 판정에 str.isdigit() 를 쓰지 않는다. 전각 숫자 '５', 동그라미 숫자 '①' 도
# 숫자로 통과시킨다. 1장 "숫자" 는 '0'~'9' 열 개뿐이다.
#
# 매개변수 이름은 검사하는 대상의 이름으로 맞췄다.
# is_phone(s) 라고 하면 함수 안에서 s.replace("-", "") 가 뭘 하는지
# 알 수 없다. is_phone(phone) 이면 읽힌다.

def is_user_id(user_id):            pass   # 4.1.1  소문자 시작, 4~16자, 소문자+숫자   ← 1 이 먼저 작성
def is_inner_id(value, prefix):     pass   # 4.1.2  앞글자(ID_* 상수) + 숫자 4개. 숫자 부분 0000 은 틀린 값
def is_person_name(name):           pass   # 4.2.1  1~20자, 한글·로마자·공백
def is_subject_name(name):          pass   # 4.2.2  1~20자, 숫자도 허용
def is_class_name(name):            pass   # 4.2.3  정확히 2글자, 대문자 + "반"
def is_password(password):          pass   # 4.3    8~20자, 영문·숫자·! @ # $ %       ← 1 이 먼저 작성
def is_role(role):                  pass   # 4.4    원장 / 강사 / 학생
def is_phone(phone):                pass   # 4.5    숫자 9~11개, "-" 허용
def is_student_status(status):      pass   # 4.6.1  재원 / 퇴원
def is_teacher_status(status):      pass   # 4.6.2  재직 / 퇴직
def is_class_status(status):        pass   # 4.6.3  개설 / 폐강
def is_enroll_status(status):       pass   # 4.6.4  수강중 / 취소
def is_date(date):                  pass   # 4.7    YYYY-MM-DD                  ← 1 이 먼저 작성
def is_time(time):                  pass   # 4.8    HH:MM                       ← 1 이 먼저 작성
def is_datetime(dt):                pass   # 4.9    날짜 공백 시각              ← 1 이 먼저 작성
def is_period(period):              pass   # 4.10   문법 — 숫자 1~2자, 선행 0 불가
def is_valid_period(period):        pass   # 4.10   의미 — 1 이상 10 이하
def is_weekday(weekday):            pass   # 4.11
def is_weekday_list(weekdays):      pass   # 4.11.1 문법 — 공백 하나로 나열
def is_valid_weekday_list(weekdays): pass  # 4.11.1 의미 — 중복 없음, 최소 1개
def is_schedule(schedule):          pass   # 4.12   시작 ≤ 종료 (날짜·교시). 시작·종료 날짜의 요일이 요일 목록에 있어야 함
def is_capacity(capacity):          pass   # 4.13   문법 — 숫자 1~2자, 선행 0 불가
def is_valid_capacity(capacity):    pass   # 4.13   의미 — 1 이상


# ---- 비교 · 계산 ----
#
# 두 개를 받는 함수는 1, 2 를 붙였다.
# compare_datetime(a, b) 가 -1 을 돌려줄 때 a 가 먼저인지 b 가 먼저인지
# 문서를 봐야 알게 되는 걸 막으려는 것이다.

def same_phone(phone1, phone2):                pass  # 4.5    "-" 떼고 비교
def same_weekday_list(weekdays1, weekdays2):   pass  # 4.11.1 순서 무시
def sort_weekday_list(weekdays):               pass  # 4.11.1 표준형 (월 수 금)
def compare_datetime(dt1, dt2):                pass  # 4.9    dt1 이 먼저면 -1, 같으면 0, 나중이면 1
def is_schedule_conflict(schedule1, schedule2): pass # 4.12.1
def display_class_status(class_):              pass  # 4.6.3  모집중/진행중/종료/폐강
def count_enrolled(class_id):                  pass  # 4.13   "수강중" 등록 수
def next_id(prefix):                           pass  # 5.1.13 최대값 + 1, 없으면 0001

# display_class_status 는 가상 일시를 인자로 받지 않는다.
# README 팀 합의대로 함수 안에서 now() 를 부른다.
# 인자로 받으면 부르는 쪽이 가상 일시를 변수에 담아두게 되고,
# 6.3 에서 값이 바뀌었을 때 갱신을 잊은 값으로 판정하게 된다.


# ---- 시간 역행 판정 — WBS 상 1 이 작성 ----
#
# 무결성 검사 ⑧(2·5)과 가상 일시 변경(5)이 둘 다 써서 여기에 둔다.
# main.py 에 두면 virtual_time.py 가 main.py 를 import 해야 하는데,
# main.py 는 아무도 import 하지 않는 게 규칙이다.

def backward_limit():          pass  # 4.14   역행 판정 기준 일시 (기록 일시의 최댓값)   ← 1, 10/10
def is_backward(new_dt):       pass  # 6.3.3  new_dt 가 backward_limit() 보다 이전이면 True


# ---- 무결성 검사 — 개별 검사는 2, 전체 연결은 5 ----

def check_integrity():
    """5.4 의 ①~⑧ 을 검사한다.

    오류를 찾으면 바로 멈추지 말고 errors.DataError 를 목록에 모아서 돌려준다.
    오류가 없으면 빈 목록을 돌려준다.

    6.7.4 — "여러 파일에 걸쳐 오류가 있는 경우, 발견되는 오류를 모두 모아
    한 번에 출력한 뒤 종료한다. 다만 어떤 파일의 문법 오류로 인해 검사할 수
    없게 된 뒤 단계의 참조 오류는 함께 출력하지 않는다."

    읽기 함수(read_*)는 파일 하나에서 첫 오류를 만나면 DataError 를 던지므로,
    파일마다 try 로 받아서 목록에 넣고 다음 파일로 넘어간다.
    각 오류에는 몇 단계에서 나왔는지 e.stage 에 1~8 을 넣는다.
    6.6.6 화면이 "[3/8] ... FAIL", "(classes.txt 제외)", "오류 2건 (파일 문법 1, 의미 규칙 1)"
    처럼 단계별로 출력하기 때문이다. 문법 오류 때문에 뒤 단계에서 빠진 파일도 알 수 있어야 한다.
    시작할 때의 출력과 종료는 main.py 가, 6.6.6 메뉴 화면은 그 담당이 한다.
    """
    pass
