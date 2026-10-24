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
구현 완료: write_all, 값 검사, 비교·계산, 역행 판정, 무결성 검사
"""

import datetime
from contextvars import ContextVar
from functools import wraps
import os
import re
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

def _read_text_unchecked(path):
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


def _read_table_unchecked(path):
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


def read_users(): return sorted(_read_table(USERS), key=lambda row: row["사용자ID"])
def read_students(): return sorted(_read_table(STUDENTS), key=lambda row: row["학생ID"])
def read_teachers(): return sorted(_read_table(TEACHERS), key=lambda row: row["강사ID"])
def read_subjects(): return sorted(_read_table(SUBJECTS), key=lambda row: row["과목ID"])
def read_classes(): return sorted(_read_table(CLASSES), key=lambda row: row["반ID"])
def read_enrollments(): return sorted(_read_table(ENROLLMENTS), key=lambda row: row["등록ID"])


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

def _write_text_unchecked(path, text):
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


def _write_table_unchecked(path, records):
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


def _write_all_unchecked(changes):
    """여러 파일을 임시 저장한 뒤 교체하고, 처리 가능한 실패 시 원본을 복구한다."""
    contents = {}
    for path, records in changes.items():
        header = HEADERS[path]
        lines = ["\t".join(header)]
        lines.extend("\t".join(rec[field] for field in header) for rec in records)
        contents[path] = "\n".join(lines) + "\n"
    originals, temporary, replaced, backups = {}, [], [], []
    keep_backups = False
    try:
        for path in contents:
            if any(path.with_name(path.name + suffix).exists()
                   for suffix in (".recovery", ".recovery-missing")):
                raise errors.DataError(errors.E_SAVE, f"{path.name}: 이전 저장의 복구 파일을 먼저 확인하세요.")
        for path, text in contents.items():
            originals[path] = path.read_bytes() if path.exists() else None
            tmp = path.with_name(path.name + TMP_SUFFIX)
            temporary.append(tmp)
            with open(tmp, "w", encoding="utf-8", newline="") as file:
                file.write(text)
        for path, original in originals.items():
            suffix = ".recovery" if original is not None else ".recovery-missing"
            backup = path.with_name(path.name + suffix)
            with open(backup, "xb") as file:
                backups.append(backup)
                file.write(original if original is not None else b"")
        keep_backups = True
        for path, tmp in zip(contents, temporary):
            os.replace(tmp, path)
            replaced.append(path)
        keep_backups = False
    except (OSError, UnicodeError, KeyboardInterrupt, EOFError) as failure:
        failed = []
        for path in reversed(replaced):
            try:
                original = originals[path]
                if original is None:
                    path.unlink()
                else:
                    tmp = path.with_name(path.name + TMP_SUFFIX)
                    tmp.write_bytes(original)
                    os.replace(tmp, path)
            except OSError:
                failed.append(path.name)
        if failed:
            keep_backups = True
            locations = ", ".join(str(backup) for backup in backups)
            raise errors.DataError(
                errors.E_SAVE,
                f"{', '.join(failed)}: 원본 복구 실패. 복구 파일을 보존했습니다: {locations}"
            ) from failure
        keep_backups = False
        if isinstance(failure, (KeyboardInterrupt, EOFError)):
            raise
        return False
    finally:
        for tmp in temporary:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
        if not keep_backups:
            for backup in backups:
                try:
                    backup.unlink(missing_ok=True)
                except OSError:
                    pass
    return True


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

# 아래 정규식은 [a-z], [0-9] 처럼 글자를 직접 나열한다.
# \d 는 전각 숫자 '５' 도 숫자로 받아들이므로 쓰지 않는다. (1장 "숫자")
# 검사는 fullmatch 로 한다. match 는 앞부분만, search 는 중간만 맞아도 통과시킨다.

_USER_ID  = re.compile(r"[a-z][a-z0-9]{3,15}")          # 4.1.1  첫 글자 + 나머지 3~15자 = 4~16자
_PASSWORD = re.compile(r"[A-Za-z0-9!@#$%]{8,20}")        # 4.3
_DATE     = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})")   # 4.7
_TIME     = re.compile(r"([0-9]{2}):([0-9]{2})")              # 4.8


def is_user_id(user_id):
    """4.1.1 사용자 ID. 소문자로 시작, 4~16자, 소문자와 숫자만."""
    return _USER_ID.fullmatch(user_id) is not None


def is_inner_id(value, prefix):
    """종류에 맞는 내부 ID 형식과 0000 제외 조건을 검사한다."""
    return (prefix in (ID_STUDENT, ID_TEACHER, ID_SUBJECT, ID_CLASS, ID_ENROLLMENT)
            and isinstance(value, str)
            and re.fullmatch(re.escape(prefix) + r"[0-9]{4}", value) is not None
            and value[1:] != "0000")


def is_person_name(name):
    """사람 이름의 문자, 길이, 공백 규칙을 검사한다."""
    return (isinstance(name, str) and re.fullmatch(r"[가-힣A-Za-z ]{1,20}", name) is not None
            and name == name.strip(" ") and "  " not in name)


def is_subject_name(name):
    """숫자를 포함할 수 있는 과목명의 형식을 검사한다."""
    return (isinstance(name, str) and re.fullmatch(r"[가-힣A-Za-z0-9 ]{1,20}", name) is not None
            and name == name.strip(" ") and "  " not in name)


def is_class_name(name):
    """반 이름이 A반부터 Z반 중 하나인지 검사한다."""
    return isinstance(name, str) and re.fullmatch(r"[A-Z]반", name) is not None


def is_password(password):
    """4.3 비밀번호. 8~20자, 로마자 대소문자·숫자·! @ # $ % 만. 공백·탭은 안 된다."""
    return _PASSWORD.fullmatch(password) is not None


def is_role(role):
    """사용자 역할을 검사한다."""
    return role in ("원장", "강사", "학생")


def is_phone(phone):
    """연락처의 숫자 개수와 하이픈 위치를 검사한다."""
    return (isinstance(phone, str) and re.fullmatch(r"[0-9]+(?:-[0-9]+)*", phone) is not None
            and 9 <= len(phone.replace("-", "")) <= 11)


def is_student_status(status):
    """학생의 저장 상태를 검사한다."""
    return status in ("재원", "퇴원")


def is_teacher_status(status):
    """강사의 저장 상태를 검사한다."""
    return status in ("재직", "퇴직")


def is_class_status(status):
    """반의 저장 상태를 검사한다."""
    return status in ("개설", "폐강")


def is_enroll_status(status):
    """수강 등록의 저장 상태를 검사한다."""
    return status in ("수강중", "취소")
def is_date(date):
    """4.7 날짜. 문법(YYYY-MM-DD)과 의미(실제로 있는 날짜)를 둘 다 본다.

    datetime.strptime 만으로 검사하지 않는다. strptime 은 "2026-9-27" 처럼
    한 자리 월도 받아들이는데, 4.7 은 이걸 틀린 날짜라고 한다.
    그래서 형식은 정규식으로 먼저 정확히 보고, 실제로 있는 날짜인지는
    datetime.date 를 만들어 보는 것으로 확인한다. (2026-02-30 은 만들 수 없다)
    """
    found = _DATE.fullmatch(date)
    if found is None:
        return False
    year, month, day = (int(part) for part in found.groups())
    try:
        datetime.date(year, month, day)
    except ValueError:
        return False
    return True


def is_time(time):
    """4.8 시각. HH:MM, 시는 00~23, 분은 00~59."""
    found = _TIME.fullmatch(time)
    if found is None:
        return False
    hour, minute = (int(part) for part in found.groups())
    return hour <= 23 and minute <= 59


def is_datetime(dt):
    """4.9 일시. 〈날짜〉␣〈시각〉 — 날짜 10자, 표준공백 하나, 시각 5자."""
    return len(dt) == 16 and dt[10] == " " and is_date(dt[:10]) and is_time(dt[11:])
def is_period(period):
    """교시 문자열의 문법을 검사한다."""
    return isinstance(period, str) and re.fullmatch(r"0|[1-9][0-9]?", period) is not None


def is_valid_period(period):
    """교시가 올바른 형식이며 1~10인지 검사한다."""
    return is_period(period) and 1 <= int(period) <= 10


def is_weekday(weekday):
    """요일 하나가 유효한지 검사한다."""
    return weekday in WEEKDAYS


def is_weekday_list(weekdays):
    """요일 목록이 표준공백 하나로 구분되는지 검사한다."""
    return isinstance(weekdays, str) and re.fullmatch(r"[월화수목금토일](?: [월화수목금토일])*", weekdays) is not None


def is_valid_weekday_list(weekdays):
    """요일 목록의 문법과 중복 여부를 검사한다."""
    return is_weekday_list(weekdays) and len(weekdays.split(" ")) == len(set(weekdays.split(" ")))


def is_schedule(schedule):
    """일정의 날짜·교시 범위와 첫날·마지막 날의 요일을 검사한다."""
    fields = ("시작날짜", "종료날짜", "요일목록", "시작교시", "종료교시")
    if not all(isinstance(schedule.get(field), str) for field in fields):
        return False
    start, end = schedule["시작날짜"], schedule["종료날짜"]
    weekdays = schedule["요일목록"]
    if not (is_date(start) and is_date(end) and start <= end
            and is_valid_weekday_list(weekdays)
            and is_valid_period(schedule["시작교시"])
            and is_valid_period(schedule["종료교시"])):
        return False
    return (int(schedule["시작교시"]) <= int(schedule["종료교시"])
            and WEEKDAYS[datetime.date.fromisoformat(start).weekday()] in weekdays.split(" ")
            and WEEKDAYS[datetime.date.fromisoformat(end).weekday()] in weekdays.split(" "))


def is_capacity(capacity):
    """정원 문자열의 문법을 검사한다."""
    return isinstance(capacity, str) and re.fullmatch(r"0|[1-9][0-9]?", capacity) is not None


def is_valid_capacity(capacity):
    """정원이 올바른 형식이며 1~99인지 검사한다."""
    return is_capacity(capacity) and 1 <= int(capacity) <= 99


# ---- 비교 · 계산 ----
#
# 두 개를 받는 함수는 1, 2 를 붙였다.
# compare_datetime(a, b) 가 -1 을 돌려줄 때 a 가 먼저인지 b 가 먼저인지
# 문서를 봐야 알게 되는 걸 막으려는 것이다.

def same_phone(phone1, phone2):
    """하이픈을 제외한 연락처를 비교한다."""
    return phone1.replace("-", "") == phone2.replace("-", "")


def same_weekday_list(weekdays1, weekdays2):
    """순서를 무시하고 요일 목록을 비교한다."""
    return set(weekdays1.split(" ")) == set(weekdays2.split(" "))


def sort_weekday_list(weekdays):
    """검증된 요일 목록을 월요일부터 일요일 순서로 정렬한다."""
    return " ".join(sorted(weekdays.split(" "), key=WEEKDAYS.index))


def compare_datetime(dt1, dt2):
    """검증된 일시 두 개를 비교해 -1, 0, 1을 반환한다."""
    return (dt1 > dt2) - (dt1 < dt2)


def is_schedule_conflict(schedule1, schedule2):
    """검증된 두 일정이 실제 수업 날짜와 교시를 공유하는지 판단한다."""
    start = max(schedule1["시작날짜"], schedule2["시작날짜"])
    end = min(schedule1["종료날짜"], schedule2["종료날짜"])
    if start > end:
        return False
    if max(int(schedule1["시작교시"]), int(schedule2["시작교시"])) > min(
            int(schedule1["종료교시"]), int(schedule2["종료교시"])):
        return False
    common = set(schedule1["요일목록"].split(" ")) & set(schedule2["요일목록"].split(" "))
    first = datetime.date.fromisoformat(start)
    days = (datetime.date.fromisoformat(end) - first).days
    return any((WEEKDAYS.index(day) - first.weekday()) % 7 <= days for day in common)


def display_class_status(class_):
    """가상 현재 날짜를 기준으로 반의 표시 상태를 반환한다."""
    if class_["반상태"] == "폐강":
        return "폐강"
    today = now()[:10]
    if today < class_["시작날짜"]:
        return "모집중"
    if today <= class_["종료날짜"]:
        return "진행중"
    return "종료"


def count_enrolled(class_id):
    """해당 반에서 취소되지 않은 수강 등록 수를 반환한다."""
    return sum(e["반ID"] == class_id and e["등록상태"] == "수강중" for e in read_enrollments())


def next_id(prefix):
    """현재 최대 번호 다음의 내부 ID를 반환한다."""
    paths = {ID_STUDENT: STUDENTS, ID_TEACHER: TEACHERS, ID_SUBJECT: SUBJECTS,
             ID_CLASS: CLASSES, ID_ENROLLMENT: ENROLLMENTS}
    if prefix not in paths:
        raise ValueError("정의되지 않은 내부 ID 종류입니다.")
    path = paths[prefix]
    records = _read_table(path)
    problems = check_duplicate_ids(path, records)
    if problems:
        raise problems[0]
    field = HEADERS[path][0]
    maximum = 0
    for lineno, record in enumerate(records, start=2):
        value = record[field]
        if not is_inner_id(value, prefix):
            raise errors.DataError(errors.E_FILE_FORMAT, f"{path.name} {lineno}행: ID 형식 오류", 4)
        maximum = max(maximum, int(value[1:]))
    if maximum == 9999:
        raise errors.DataError(errors.E_SAVE, f"{path.name}: ID 번호가 9999에 도달하여 등록할 수 없습니다.")
    return f"{prefix}{maximum + 1:04d}"

# display_class_status 는 가상 일시를 인자로 받지 않는다.
# README 팀 합의대로 함수 안에서 now() 를 부른다.
# 인자로 받으면 부르는 쪽이 가상 일시를 변수에 담아두게 되고,
# 6.3 에서 값이 바뀌었을 때 갱신을 잊은 값으로 판정하게 된다.


# ---- 시간 역행 판정 — WBS 상 1 이 작성 ----
#
# 무결성 검사 ⑧(2·5)과 가상 일시 변경(5)이 둘 다 써서 여기에 둔다.
# main.py 에 두면 virtual_time.py 가 main.py 를 import 해야 하는데,
# main.py 는 아무도 import 하지 않는 게 규칙이다.

#
# 일시끼리는 문자열 그대로 < 로 비교한다.
# 4.9 형식("2026-09-27 14:30")은 자릿수가 고정이고 큰 단위부터 적혀 있어서,
# 형식이 맞는 두 일시는 글자 순서와 시간 순서가 같다.

def backward_limit():
    """4.14 역행 판정 기준 일시.

    4.14 — "역행 판정 기준 일시는 '기록 일시' 집합의 최댓값과 현재 저장된
    가상 현재 일시 중 더 나중의 일시를 말한다."
    기록 일시는 세 가지뿐이다.
        ① enrollments.txt 의 등록 일시
        ② enrollments.txt 의 취소 일시 (취소 상태인 레코드만)
        ③ datetime.txt 의 모든 줄 (이력 + 지금의 가상 일시)
    classes.txt 의 시작일·종료일은 아직 오지 않은 예정이라 넣지 않는다.

    형식이 틀린 값은 건너뛴다. 그런 값은 무결성 검사가 따로 오류로 잡는다.
    """
    candidates = list(read_datetime())                    # ③
    for enrollment in read_enrollments():
        candidates.append(enrollment["등록일시"])          # ①
        if enrollment["등록상태"] == "취소":
            candidates.append(enrollment["취소일시"])      # ②
    # 올바른 값이 하나도 없으면 "" 를 돌려준다. 어떤 일시도 "" 보다 이전이 아니므로 역행으로 막지 않는다.
    return max((dt for dt in candidates if is_datetime(dt)), default="")


def is_backward(new_dt):
    """6.3.3 new_dt 가 역행 판정 기준 일시보다 이전이면 True. 같은 일시는 허용한다."""
    return new_dt < backward_limit()


# ---- 무결성 검사 — 개별 검사는 2, 전체 연결은 5 ----

def _problem(path, lineno, code, message, stage):
    """파일·행·검사 단계를 포함한 오류를 만든다."""
    return errors.DataError(code, f"{path.name} {lineno}행: {message}", stage)


def check_fields(path, records):
    """읽기에 성공한 표의 필드 형식과 값 범위를 검사한다."""
    validators = {
        "사용자ID": is_user_id, "비밀번호": is_password, "사용자역할": is_role,
        "이름": is_person_name, "연락처": is_phone, "학생상태": is_student_status,
        "강사상태": is_teacher_status, "과목명": is_subject_name, "반이름": is_class_name,
        "요일목록": is_valid_weekday_list, "시작교시": is_valid_period,
        "종료교시": is_valid_period, "시작날짜": is_date, "종료날짜": is_date,
        "정원": is_valid_capacity, "반상태": is_class_status, "등록일시": is_datetime,
        "등록상태": is_enroll_status,
        "취소일시": lambda value: value == EMPTY or is_datetime(value),
    }
    prefixes = {"학생ID": ID_STUDENT, "강사ID": ID_TEACHER, "과목ID": ID_SUBJECT,
                "반ID": ID_CLASS, "등록ID": ID_ENROLLMENT}
    problems = []
    for lineno, record in enumerate(records, start=2):
        for field in HEADERS[path]:
            value = record.get(field)
            valid = isinstance(value, str)
            if valid:
                valid = (is_inner_id(value, prefixes[field]) if field in prefixes
                         else validators[field](value))
            if not valid:
                problems.append(_problem(path, lineno, errors.E_FILE_FORMAT,
                                         f"{field} 형식 또는 범위 오류", 4))
    return problems


def check_duplicate_ids(path, records):
    """파일의 첫 번째 필드에 중복 ID가 있는지 검사한다."""
    field, seen, problems = HEADERS[path][0], set(), []
    for lineno, record in enumerate(records, start=2):
        value = record[field]
        if value in seen:
            problems.append(_problem(path, lineno, errors.E_DUP_ID, f"{field} 중복: {value}", 5))
        seen.add(value)
    return problems


def check_references(tables):
    """형식·ID 검사를 통과한 파일들의 참조와 계정 연결을 검사한다."""
    problems = []
    indexes = {path: {r[HEADERS[path][0]]: r for r in records}
               for path, records in tables.items()}
    links = ((STUDENTS, "사용자ID", USERS), (TEACHERS, "사용자ID", USERS),
             (CLASSES, "과목ID", SUBJECTS), (CLASSES, "강사ID", TEACHERS),
             (ENROLLMENTS, "학생ID", STUDENTS), (ENROLLMENTS, "반ID", CLASSES))
    for source, field, target in links:
        if source not in tables or target not in tables:
            continue
        for lineno, record in enumerate(tables[source], start=2):
            if record[field] not in indexes[target]:
                problems.append(_problem(source, lineno, errors.E_REF_MISSING,
                                         f"{target.name}에 없는 {field}: {record[field]}", 6))
    for path, role in ((STUDENTS, "학생"), (TEACHERS, "강사")):
        if path not in tables:
            continue
        seen = set()
        for lineno, record in enumerate(tables[path], start=2):
            user_id = record["사용자ID"]
            if user_id in seen:
                problems.append(_problem(path, lineno, errors.E_DUP_ID,
                                         f"사용자ID 중복 연결: {user_id}", 6))
            seen.add(user_id)
            user = indexes.get(USERS, {}).get(user_id)
            if user is not None and user["사용자역할"] != role:
                problems.append(_problem(path, lineno, errors.E_ROLE_INVALID,
                                         f"사용자 {user_id}의 역할이 {role}가 아닙니다.", 6))
    if USERS in tables:
        users = tables[USERS]
        if sum(u["사용자역할"] == "원장" for u in users) != 1:
            problems.append(_problem(USERS, 1, errors.E_ROLE_INVALID,
                                     "원장 계정은 정확히 하나여야 합니다.", 6))
        for lineno, user in enumerate(users, start=2):
            role = user["사용자역할"]
            if role == "원장":
                continue
            path = STUDENTS if role == "학생" else TEACHERS
            if path in tables and not any(r["사용자ID"] == user["사용자ID"] for r in tables[path]):
                problems.append(_problem(USERS, lineno, errors.E_REF_MISSING,
                                         f"{path.name}에 연결된 {role} 레코드가 없습니다.", 6))
    return problems


def check_relations(tables):
    """형식·ID 검사를 통과한 데이터의 일정·정원·수강 관계를 검사한다."""
    problems, valid_classes, open_classes, names = [], {}, [], set()
    for lineno, class_ in enumerate(tables.get(CLASSES, []), start=2):
        if not is_schedule(class_):
            problems.append(_problem(CLASSES, lineno, errors.E_FILE_FORMAT, "수업 일정의 의미 규칙 오류", 7))
            continue
        valid_classes[class_["반ID"]] = class_
        if class_["반상태"] != "개설":
            continue
        name = (class_["과목ID"], class_["반이름"])
        if name in names:
            problems.append(_problem(CLASSES, lineno, errors.E_CLASS_NAME_DUPLICATE,
                                     "같은 과목의 개설된 반 이름이 중복됩니다.", 7))
        names.add(name)
        for other_line, other in open_classes:
            if class_["강사ID"] == other["강사ID"] and is_schedule_conflict(class_, other):
                problems.append(_problem(CLASSES, lineno, errors.E_TEACHER_CONFLICT,
                                         f"{other_line}행 반과 강사 일정 충돌", 7))
        open_classes.append((lineno, class_))
    students = {s["학생ID"]: s for s in tables.get(STUDENTS, [])}
    classes = {c["반ID"]: c for c in tables.get(CLASSES, [])}
    counts, pairs, student_classes = {}, set(), {}
    for lineno, enrollment in enumerate(tables.get(ENROLLMENTS, []), start=2):
        cancelled = enrollment["등록상태"] == "취소"
        cancel_dt = enrollment["취소일시"]
        if cancelled:
            if cancel_dt == EMPTY or cancel_dt < enrollment["등록일시"]:
                problems.append(_problem(ENROLLMENTS, lineno, errors.E_FILE_FORMAT,
                                         "취소일시가 없거나 등록일시보다 이전입니다.", 7))
            continue
        if cancel_dt != EMPTY:
            problems.append(_problem(ENROLLMENTS, lineno, errors.E_FILE_FORMAT,
                                     "수강중 등록의 취소일시는 '-'여야 합니다.", 7))
        student_id, class_id = enrollment["학생ID"], enrollment["반ID"]
        student = students.get(student_id)
        if student is not None and student["학생상태"] == "퇴원":
            problems.append(_problem(ENROLLMENTS, lineno, errors.E_FILE_FORMAT,
                                     "퇴원 학생의 수강중 등록이 남아 있습니다.", 7))
        related_class = classes.get(class_id)
        if related_class is not None and related_class["반상태"] == "폐강":
            problems.append(_problem(ENROLLMENTS, lineno, errors.E_FILE_FORMAT,
                                     "폐강 반의 수강중 등록이 남아 있습니다.", 7))
        pair = (student_id, class_id)
        if pair in pairs:
            problems.append(_problem(ENROLLMENTS, lineno, errors.E_ALREADY_ENROLLED,
                                     "같은 학생·반의 수강중 등록이 중복됩니다.", 7))
        pairs.add(pair)
        counts[class_id] = counts.get(class_id, 0) + 1
        class_ = valid_classes.get(class_id)
        if class_ is None or class_["반상태"] != "개설":
            continue
        for other_line, other in student_classes.get(student_id, []):
            if class_id != other["반ID"] and is_schedule_conflict(class_, other):
                problems.append(_problem(ENROLLMENTS, lineno, errors.E_STUDENT_CONFLICT,
                                         f"{other_line}행 수강 등록과 학생 일정 충돌", 7))
        student_classes.setdefault(student_id, []).append((lineno, class_))
    if ENROLLMENTS in tables:
        for lineno, class_ in enumerate(tables.get(CLASSES, []), start=2):
            if counts.get(class_["반ID"], 0) > int(class_["정원"]):
                problems.append(_problem(CLASSES, lineno, errors.E_CLASS_FULL, "수강중 인원이 정원을 초과합니다.", 7))
    return problems


def check_time_history(lines, enrollments=None):
    """가상 일시 이력의 형식·순서와 수강 기록보다 과거인지 검사한다."""
    problems = []
    if not lines:
        return [_problem(DATETIME, 1, errors.E_TIME_BACKWARD, "가상 일시 이력이 비어 있습니다.", 8)]
    for lineno, value in enumerate(lines, start=1):
        if not isinstance(value, str) or not is_datetime(value):
            problems.append(_problem(DATETIME, lineno, errors.E_TIME_BACKWARD, "일시 형식 오류", 8))
    if problems:
        return problems
    for lineno in range(2, len(lines) + 1):
        if lines[lineno - 1] < lines[lineno - 2]:
            problems.append(_problem(DATETIME, lineno, errors.E_TIME_BACKWARD, "이전 이력보다 과거입니다.", 8))
    for lineno, enrollment in enumerate(enrollments or [], start=2):
        fields = ["등록일시"]
        if enrollment["등록상태"] == "취소":
            fields.append("취소일시")
        for field in fields:
            value = enrollment[field]
            if is_datetime(value) and value > lines[-1]:
                problems.append(_problem(DATETIME, len(lines), errors.E_TIME_BACKWARD,
                                         f"enrollments.txt {lineno}행 {field}보다 과거입니다.", 8))
    return problems


def check_integrity():
    """전체 파일을 단계별 검사하고, 사용할 수 없는 파일을 제외해 오류를 모은다."""
    problems, readable, tables, excluded = [], [], {}, []
    for path in list(HEADERS) + [DATETIME]:
        for suffix in (".recovery", ".recovery-missing"):
            backup = path.with_name(path.name + suffix)
            if backup.exists():
                problems.append(errors.DataError(errors.E_SAVE,
                    f"{path.name}: 미완료 저장의 복구 파일이 있습니다. 복구 후 다시 실행하세요: {backup}", 1))
        try:
            _read_text(path)
        except errors.DataError as error:
            error.stage = 2 if error.code == errors.E_FILE_FORMAT else 1
            problems.append(error)
            excluded.append(path.name)
        except OSError:
            problems.append(_problem(path, 1, errors.E_FILE_READ, "파일을 읽을 수 없습니다.", 1))
            excluded.append(path.name)
        else:
            readable.append(path)
    for path in HEADERS:
        if path not in readable:
            continue
        try:
            records = _read_table(path)
        except errors.DataError as error:
            error.stage = 3
            problems.append(error)
            excluded.append(path.name)
            continue
        except OSError:
            problems.append(_problem(path, 1, errors.E_FILE_READ, "파일을 읽을 수 없습니다.", 1))
            excluded.append(path.name)
            continue
        field_errors = check_fields(path, records)
        if field_errors:
            problems.extend(field_errors)
            excluded.append(path.name)
            continue
        duplicate_errors = check_duplicate_ids(path, records)
        if duplicate_errors:
            problems.extend(duplicate_errors)
            excluded.append(path.name)
            continue
        tables[path] = records
    problems.extend(check_references(tables))
    problems.extend(check_relations(tables))
    if DATETIME in readable:
        try:
            lines = read_datetime()
        except errors.DataError as error:
            error.stage = 8 if error.code == errors.E_TIME_BACKWARD else 1
            problems.append(error)
            excluded.append(DATETIME.name)
        except OSError:
            problems.append(_problem(DATETIME, 1, errors.E_FILE_READ, "파일을 읽을 수 없습니다.", 1))
            excluded.append(DATETIME.name)
        else:
            problems.extend(check_time_history(lines, tables.get(ENROLLMENTS)))
    for error in problems:
        error.excluded_files = tuple(excluded)
    return sorted(problems, key=lambda error: error.stage)


# ---- 작업 경계 검증: 역할 확인, 외부 수정 감지, 저장 전 관계 검증 ----
_snapshot = ContextVar("operation_snapshot", default=None)


def snapshot():
    try:
        return {p: p.read_bytes() for p in [*HEADERS, DATETIME]}
    except OSError as exc:
        raise errors.DataError(errors.E_FILE_READ, "데이터 파일을 읽을 수 없습니다.", 1) from exc

def require_integrity():
    problems = check_integrity()
    if problems:
        raise errors.DataError(problems[0].code,
                              "\n".join(f"[{e.code}] {e.message}" for e in problems),
                              problems[0].stage)

def _read_text(path):
    try:
        return _read_text_unchecked(path)
    except OSError as exc:
        raise errors.DataError(errors.E_FILE_READ, f"{path.name}: 파일을 읽을 수 없습니다.", 1) from exc

def _read_table(path):
    rows = _read_table_unchecked(path)
    for lineno, row in enumerate(rows, 2):
        for field, value in row.items():
            if not value or value != value.strip(" ") or "  " in value:
                raise errors.DataError(errors.E_FILE_FORMAT,
                                       f"{path.name} {lineno}행: {field} 빈 값 또는 공백 문법 오류", 3)
    return rows

def require_unchanged():
    before = _snapshot.get()
    if before is not None and snapshot() != before:
        # 깨진 파일은 계속 진행하지 않고, 정상적인 외부 수정은 해당 작업만 취소한다.
        require_integrity()
        raise errors.DataError(errors.E_CONCURRENT_EDIT,
                               errors.ERROR_MESSAGES[errors.E_CONCURRENT_EDIT])

def validate_changes(changes):
    tables = {p: changes.get(p, _read_table(p)) for p in HEADERS}
    problems = []
    for path, rows in tables.items():
        problems.extend(check_fields(path, rows))
        if not problems:
            problems.extend(check_duplicate_ids(path, rows))
    if not problems:
        problems.extend(check_references(tables))
        problems.extend(check_relations(tables))
        problems.extend(check_time_history(read_datetime(), tables[ENROLLMENTS]))
    if problems:
        raise problems[0]

def write_all(changes):
    if _snapshot.get() is None:
        return _write_all_unchecked(changes)
    require_unchanged()
    validate_changes(changes)
    result = _write_all_unchecked(changes)
    if result:
        _snapshot.set(snapshot())
    return result

def _write_table(path, records):
    if _snapshot.get() is None:
        return _write_table_unchecked(path, records)  # 최초 실행의 헤더 생성도 지원
    return write_all({path: records})

def _write_text(path, text):
    if _snapshot.get() is not None:
        require_unchanged()
        if path == DATETIME:
            lines = text.rstrip("\n").split("\n")
            old = read_datetime()
            if lines != old and lines[:len(old)] != old:
                raise errors.DataError(errors.E_TIME_BACKWARD, "기존 가상 일시 이력은 변경할 수 없습니다.", 8)
            problems = check_time_history(lines, read_enrollments())
            if problems:
                raise problems[0]
    result = _write_text_unchecked(path, text)
    if result and _snapshot.get() is not None:
        _snapshot.set(snapshot())
    return result

def _guard_operation(function, role):
    """단일 화면 작업에 적용한다. 긴 하위 메뉴 루프 전체에는 적용하지 않는다."""
    @wraps(function)
    def guarded(user):
        require_integrity()
        actual = next((u for u in read_users() if u["사용자ID"] == user.get("사용자ID")), None)
        if actual is None or actual["사용자역할"] != role or user.get("사용자역할") != role:
            print(f"[{errors.E_NO_PERMISSION}] 이 기능을 사용할 권한이 없습니다.")
            return
        if role != "원장":
            reader, state, active = ((read_students, "학생상태", "재원") if role == "학생"
                                      else (read_teachers, "강사상태", "재직"))
            person = next(p for p in reader() if p["사용자ID"] == actual["사용자ID"])
            if person[state] != active:
                print(f"[{errors.E_NO_PERMISSION}] 사용할 수 없는 계정입니다.")
                return
        token = _snapshot.set(snapshot())
        try:
            return function(actual)
        except errors.OperationCancelled:
            print("작업을 취소했습니다. 변경된 내용이 없습니다.")
        except errors.DataError as exc:
            if exc.code == errors.E_CONCURRENT_EDIT:
                print(f"[{exc.code}] {exc.message}")
                return
            # ID 소진은 파일 손상이 아니라 해당 등록 작업의 실패다.
            if exc.code == errors.E_SAVE and "9999" in exc.message:
                print(f"[{exc.code}] {exc.message}")
                return
            raise
        finally:
            _snapshot.reset(token)
    return guarded

def operation(role):
    """업무 함수에 @data.operation(역할)로 적용한다."""
    return lambda function: _guard_operation(function, role)
