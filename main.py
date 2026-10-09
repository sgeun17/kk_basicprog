"""학원 운영 관리 프로그램 — 실행 시작점 — 담당 1

    python main.py

프로그램 시작과 종료, 최초 실행, 로그인, 역할별 메뉴를 맡는다.
기획서 2.3.1, 2.4, 6.1, 6.2, 6.7 을 구현한다.

이 파일이 맨 위층이다. 다른 파일을 전부 import 하고,
다른 어떤 파일도 main.py 를 import 하지 않는다.

    main.py
       ↓
    admin.py   enrollment.py   virtual_time.py     ← 셋은 서로 import 하지 않는다
       ↓
    ui.py      data.py
       ↓
    errors.py

메뉴에 연결되는 기능 함수는 로그인한 사용자 레코드를 인자로 받는다.
    enrollment.enroll_class(user)
user["사용자ID"], user["사용자역할"] 로 누가 로그인했는지 안다.
아직 만들어지지 않은 기능은 메뉴에서 "준비 중" 으로 표시하고,
최종 통합 전에 전부 연결한다.
"""

import getpass
import sys

import data
import errors
import ui

import admin
import enrollment
import virtual_time


TITLE = "===== 학원 운영 관리 프로그램 ====="

# 6.7.5 종료 코드 — 정상 종료(6.7.1)는 성공, 그 외(6.7.2~6.7.4)는 실패
EXIT_OK = 0
EXIT_FAIL = 1

MAX_LOGIN_FAILURES = 5      # 6.2.3

# 6.7.4 시작할 때 무결성 검사에 걸렸을 때의 마지막 문장
START_FAIL_MESSAGE = "필수 데이터 파일에 오류가 있어 프로그램을 시작할 수 없습니다. 파일을 수정한 뒤 다시 실행하세요."
# 6.6.6 실행 중에 데이터 파일 오류를 발견했을 때의 마지막 문장
RUN_FAIL_MESSAGE = "데이터 파일에 오류가 있어 프로그램을 종료합니다. 파일을 수정한 뒤 다시 실행하세요."


def print_error(code, message=None):
    """[코드] 메시지 형식으로 출력한다. message 를 안 주면 errors.ERROR_MESSAGES 의 문장을 쓴다."""
    if message is None:
        message = errors.ERROR_MESSAGES[code]
    print(f"[{code}] {message}")


# ============================================================
# 시작 · 최초 실행 (2.3.1, 6.7.4)
# ============================================================

def read_or_empty(read):
    """read_* 함수를 불러 본다. 파일이 없으면 [], 그 밖의 오류면 None 을 돌려준다.

    최초 실행이 끝났는지 판단할 때만 쓴다. 여기서 오류를 출력하지 않는 것은,
    판단이 끝난 뒤 무결성 검사가 같은 오류를 제대로 출력하기 때문이다.
    """
    try:
        return read()
    except errors.DataError as e:
        if e.code == errors.E_FILE_MISSING:
            return []
        return None


def is_first_run_unfinished():
    """data 폴더는 있지만 최초 실행이 끝나지 않은 상태인지. (2.3.1 — 수정 1판)

    2.3.1 — "data 디렉토리는 존재하지만 users.txt에 원장 계정이 없거나
    datetime.txt가 없는 경우, 최초 실행이 완료되지 않은 것으로 보고
    생성된 파일을 모두 삭제한 뒤 본 절차를 처음부터 다시 수행한다."

    다만 학생·강사·과목·반·수강 등록 기록이 하나라도 있으면 끊긴 최초 실행이 아니다.
    그때 모두 지우면 실수로 datetime.txt 하나 지운 것 때문에 학원 데이터가 전부 날아간다.
    그래서 기록이 있으면 False 를 돌려주고, 무결성 검사가 E_FILE_MISSING 등으로 종료시킨다. (6.7.4)
    """
    users = read_or_empty(data.read_users)
    if users is None:
        return False
    has_admin = any(user["사용자역할"] == "원장" for user in users)
    if has_admin and data.DATETIME.exists():
        return False                                    # 최초 실행이 끝난 정상 상태

    # 원장이 아닌 계정이 있으면 학생·강사를 등록한 적이 있다는 뜻이다
    if any(user["사용자역할"] != "원장" for user in users):
        return False
    for read in (data.read_students, data.read_teachers, data.read_subjects,
                 data.read_classes, data.read_enrollments):
        records = read_or_empty(read)
        if records is None or records:
            return False
    return True


def first_run():
    """2.3.1 최초 실행. data 폴더·파일을 만들고 원장 계정과 첫 가상 일시를 받는다.

    5단계 무결성 검사와 6단계 로그인 화면은 main() 이 이어서 한다.
    저장에 실패하면 [E_SAVE] 를 출력하고 종료한다. (2.3)
    """
    print(TITLE)
    # 기획서에 없는 안내 문장이다. 수정 1판에서 2.3.1 에 추가한다.
    print("최초 실행입니다. 원장 계정을 만듭니다.")

    # 1~2단계 — data 폴더와 헤더만 있는 파일. 끊긴 최초 실행이면 남은 파일을 지우고 새로 만든다.
    if not data.create_data_dir():
        print_error(errors.E_SAVE)
        sys.exit(EXIT_FAIL)

    # 3단계 — 원장 계정. 화면 문장은 6.2.1 로그인 화면과 같다.
    while True:
        user_id = input("사용자 ID: ").strip(" ")
        if user_id == "":
            print_error(errors.E_INPUT_EMPTY)
        elif not data.is_user_id(user_id):
            print_error(errors.E_FILE_FORMAT, "사용자 ID 형식이 올바르지 않습니다.")
        else:
            break
    while True:
        password = getpass.getpass("비밀번호: ")          # 5.3 비밀번호는 공백을 떼지 않는다
        if password == "":
            print_error(errors.E_INPUT_EMPTY)
        elif not data.is_password(password):
            print_error(errors.E_FILE_FORMAT, "비밀번호 형식이 올바르지 않습니다.")   # 6.6.1.4 형식
        else:
            break
    if not data.write_users([{"사용자ID": user_id, "비밀번호": password, "사용자역할": "원장"}]):
        print_error(errors.E_SAVE)
        sys.exit(EXIT_FAIL)

    # 4단계 — 첫 가상 현재 일시. 화면 문장은 6.3.1·6.3.2 와 같다. 생략할 수 없다.
    while True:
        first_dt = input("새 가상 일시를 입력하세요 (형식: YYYY-MM-DD HH:MM): ").strip(" ")
        if first_dt == "":
            print_error(errors.E_INPUT_EMPTY)
        elif not data.is_datetime(first_dt):
            print_error(errors.E_FILE_FORMAT, "일시 형식이 올바르지 않습니다. 예: 2026-09-27 15:30")
        else:
            break
    if not data.write_datetime([first_dt]):
        print_error(errors.E_SAVE)
        sys.exit(EXIT_FAIL)


def start():
    """프로그램 시작. 남은 임시 파일 정리 → 필요하면 최초 실행 → 무결성 검사. (6.7.3, 2.3.1, 6.7.4)"""
    data.cleanup_tmp()

    if not data.DATA.exists() or is_first_run_unfinished():
        first_run()

    # check_integrity 는 아직 비어 있어서 None 을 돌려준다. None 과 [] 는 둘 다 통과로 본다.
    problems = data.check_integrity()
    if problems:
        for e in problems:
            print_error(e.code, e.message)
        print(START_FAIL_MESSAGE)
        sys.exit(EXIT_FAIL)


# ============================================================
# 로그인 · 로그아웃 (6.2)
# ============================================================

def find_person(user):
    """계정에 연결된 학생·강사 레코드를 찾는다. 원장은 None.

    6.2.2 — "계정과 학생·강사의 연결 자체가 잘못된 경우에는 비활성 계정으로
    처리하지 않고 데이터 무결성 오류로 처리한다."
    그래서 연결된 레코드가 없으면 DataError 를 던진다. main() 이 받아서 종료한다.
    """
    role = user["사용자역할"]
    if role == "원장":
        return None
    if role == "학생":
        people, file_name = data.read_students(), "students.txt"
    elif role == "강사":
        people, file_name = data.read_teachers(), "teachers.txt"
    else:
        raise errors.DataError(errors.E_FILE_FORMAT,
                               f"users.txt: 사용자 ID {user['사용자ID']} 의 역할 '{role}' 이 올바르지 않습니다")
    for person in people:
        if person["사용자ID"] == user["사용자ID"]:
            return person
    raise errors.DataError(errors.E_REF_MISSING,
                           f"{file_name}: 사용자 ID {user['사용자ID']} 와 연결된 {role} 레코드가 없습니다")


def is_active(user):
    """6.2.2 비활성 계정이 아닌지. 학생은 재원, 강사는 재직이어야 로그인할 수 있다."""
    person = find_person(user)
    if person is None:
        return True                                     # 원장
    if user["사용자역할"] == "학생":
        return person["학생상태"] == "재원"
    return person["강사상태"] == "재직"


def ask_login_id():
    """6.2.1 사용자 ID 를 받는다. 0 이면 종료 확인, N 이면 None.

    6.2.1 — "종료 명령 확인 → 빈 입력 확인 → 사용자 ID 문법 형식 검사 → 계정 존재 여부 확인"
    빈 입력·형식 오류는 같은 항목을 다시 받는다. 실패 횟수에 넣지 않는다. (6.2.3)
    """
    while True:
        user_id = input("사용자 ID: ").strip(" ")
        if user_id == "0":
            if confirm_exit():
                exit_program()
            return None                                 # 로그인 화면부터 다시
        if user_id == "":
            print_error(errors.E_INPUT_EMPTY)
        elif not data.is_user_id(user_id):
            print_error(errors.E_FILE_FORMAT, "사용자 ID 형식이 올바르지 않습니다.")
        else:
            return user_id


def ask_login_password():
    """6.2.1 비밀번호를 받는다. 화면에 보이지 않게 getpass 로 받고, 앞뒤 공백을 떼지 않는다. (5.3)

    빈 입력이면 같은 항목을 다시 받는다. 형식이 틀리면 None — 로그인 화면부터 다시 받는다.
    (3장 그림 1 — "입력 형식이 유효한가? N → 입력 오류 메시지 출력(실패 횟수 증가 없음)")
    """
    while True:
        password = getpass.getpass("비밀번호: ")
        if password == "":
            print_error(errors.E_INPUT_EMPTY)
            continue
        if not data.is_password(password):
            print_error(errors.E_FILE_FORMAT, "비밀번호 형식이 올바르지 않습니다.")
            return None
        return password


def login():
    """6.2 로그인. 성공하면 users.txt 의 그 사용자 레코드를 돌려준다.

    6.2.3 — 실패 횟수에 넣는 것: 없는 ID, 비밀번호 불일치, 비활성 계정.
            넣지 않는 것: 빈 입력, 형식 오류.
            연속 5회면 확인 없이 종료한다.
    실패 횟수는 이 함수 안의 변수라서, 로그아웃 후 다시 부르면 0 부터 센다. (6.2.4)
    """
    failures = 0
    while True:
        print()
        print(TITLE)
        user_id = ask_login_id()
        if user_id is None:
            continue
        password = ask_login_password()
        if password is None:
            continue

        user = None
        for candidate in data.read_users():
            if candidate["사용자ID"] == user_id:
                user = candidate
                break

        # 6.2.2 — "ID 없음"과 "비밀번호 불일치"는 같은 메시지를 쓴다.
        # 어느 쪽이 틀렸는지 알려주면 남의 ID 가 있는지 알아낼 수 있어서다.
        if user is None or user["비밀번호"] != password:
            failures += 1
            print_error(errors.E_AUTH_FAIL)
        elif not is_active(user):
            failures += 1
            print("사용할 수 없는 계정입니다.")
        else:
            person = find_person(user)
            name = "원장" if person is None else person["이름"]
            print(f"로그인되었습니다. 안녕하세요, {name}님.")
            return user

        if failures >= MAX_LOGIN_FAILURES:
            print("로그인 시도 횟수를 초과했습니다. 프로그램을 종료합니다.")
            sys.exit(EXIT_FAIL)                         # 6.7.2 확인 없이 종료


# ============================================================
# 역할별 메뉴 (6.1.1, 2.4, 6.6)
# ============================================================

def not_ready(user):
    # 기획서에 없는 문장이다. 팀원 기능이 다 연결되면 이 함수와 함께 지운다.
    print("준비 중입니다.")


def feature(module, name):
    """팀원 파일에 그 이름의 함수가 있으면 그 함수를, 아직 없으면 not_ready 를 돌려준다.

    팀원이 노션에 적힌 이름 그대로 함수를 만들면 main.py 를 고치지 않아도 메뉴에 연결된다.
    최종 통합 때 not_ready 를 지우면서 getattr 도 직접 호출로 바꾼다.
    """
    return getattr(module, name, not_ready)


# 메뉴 번호 → (기능 파일, 함수 이름). 함수 이름은 노션에 적힌 이름과 같아야 한다.
ADMIN_FEATURES = {
    1: (admin, "manage_students"),               # 6.6.1  학생 관리        — 5
    2: (admin, "manage_teachers"),               # 6.6.2  강사 관리        — 3
    3: (admin, "manage_subjects"),               # 6.6.3  과목 관리        — 3
    4: (admin, "manage_classes"),                # 6.6.4  반 관리          — 3
    5: (enrollment, "manage_enrollments"),       # 6.6.5  수강 등록 조회·취소 — 4
    6: (virtual_time, "change_virtual_time"),    # 6.3    가상 현재 일시 변경 — 5
    7: (admin, "run_integrity_check"),           # 6.6.6  무결성 검사      — 5
    8: (admin, "manage_passwords"),              # 6.6.8  비밀번호 관리    — 담당 미정
}
TEACHER_FEATURES = {
    1: (enrollment, "list_my_classes"),          # 6.5.1  담당 반 조회
    2: (enrollment, "list_class_students"),      # 6.5.2  담당 반 수강생 조회
    3: (enrollment, "show_teaching_schedule"),   # 6.5.3  수업 일정 조회
}
STUDENT_FEATURES = {
    1: (enrollment, "show_my_info"),             # 6.4.1  내 정보 조회
    2: (enrollment, "list_open_classes"),        # 6.4.2  수강 가능한 반 조회
    3: (enrollment, "show_class_detail"),        # 6.4.3  반 상세 조회
    4: (enrollment, "enroll_class"),             # 6.4.4  수강 신청
    5: (enrollment, "list_my_enrollments"),      # 6.4.5  내 수강 목록 조회
    6: (enrollment, "cancel_enrollment"),        # 6.4.6  수강 취소
}

ADMIN_SCREEN = """===== 원장 메뉴 =====
1. 학생 관리
2. 강사 관리
3. 과목 관리
4. 반 관리
5. 수강 등록 조회·취소
6. 가상 현재 일시 변경
7. 무결성 검사
8. 비밀번호 관리
9. 로그아웃
0. 프로그램 종료"""

TEACHER_SCREEN = """===== 강사 메뉴 ({name}님) =====
1. 담당 반 조회
2. 담당 반 수강생 조회
3. 수업 일정 조회
9. 로그아웃
0. 프로그램 종료"""

# 6.4 화면의 "수강 가능한 수업 조회" 는 오타라서 6.1.1 대로 "반" 으로 썼다. (수정 1판)
STUDENT_SCREEN = """===== 학생 메뉴 ({name}님) =====
1. 내 정보 조회
2. 수강 가능한 반 조회
3. 반 상세 조회
4. 수강 신청
5. 내 수강 목록 조회
6. 수강 취소
9. 로그아웃
0. 프로그램 종료"""


def run_menu(user, screen, features):
    """메뉴 화면을 보여주고 고른 기능을 실행한다. 로그아웃하면 돌아간다.

    9 로그아웃, 0 종료는 모든 역할이 같다. (6.1.1, 6.2.5, 6.1.4)
    잘못된 번호면 ui.ask_menu_choice 가 오류를 출력하고, 여기서 같은 메뉴를 다시 보여준다. (6.1.2)
    역할마다 보여주는 기능만 다르게 해서 2.4 의 권한을 나눈다.
    """
    valid = list(features) + [9, 0]
    while True:
        print()
        print(screen)
        choice = ui.ask_menu_choice(valid)
        if choice is None:
            continue
        if choice == 9:
            print("로그아웃되었습니다.")                 # 6.2.5 확인 없이 즉시
            return
        if choice == 0:
            if confirm_exit():
                exit_program()
            continue
        module, name = features[choice]
        feature(module, name)(user)


def admin_menu(user):
    run_menu(user, ADMIN_SCREEN, ADMIN_FEATURES)


def teacher_menu(user):
    run_menu(user, TEACHER_SCREEN.format(name=find_person(user)["이름"]), TEACHER_FEATURES)


def student_menu(user):
    run_menu(user, STUDENT_SCREEN.format(name=find_person(user)["이름"]), STUDENT_FEATURES)


ROLE_MENUS = {"원장": admin_menu, "강사": teacher_menu, "학생": student_menu}


# ============================================================
# 종료 (6.1.4, 6.7)
# ============================================================

def confirm_exit():
    """6.1.4 "프로그램을 종료하시겠습니까?" Y 면 True. N 이면 취소 문장을 출력하고 False. (6.7.1)"""
    return ui.ask_yes_no("프로그램을 종료")


def exit_program():
    """6.7.1 정상 종료."""
    print("프로그램을 종료합니다.")
    sys.exit(EXIT_OK)


def main():
    try:
        start()
        while True:
            user = login()
            ROLE_MENUS[user["사용자역할"]](user)
    except (KeyboardInterrupt, EOFError):
        # 6.7.3 — Ctrl+C, 또는 입력 끝(맥 Ctrl+D, 윈도우 Ctrl+Z 후 Enter)
        print()
        print("입력이 중단되었습니다. 저장되지 않은 변경 사항 없이 프로그램을 종료합니다.")
        sys.exit(EXIT_FAIL)
    except errors.DataError as e:
        # 실행 중에 깨진 데이터 파일을 만난 경우. 무결성 검사가 다 만들어지면 시작 때 먼저 걸러진다.
        print_error(e.code, e.message)
        print(RUN_FAIL_MESSAGE)
        sys.exit(EXIT_FAIL)


if __name__ == "__main__":
    main()
