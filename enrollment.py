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
# 6.4.1
def show_my_info(user):
    """로그인한 학생의 ID와 이름을 조회한다."""

    # 학생 데이터 파일에서 모든 학생 정보를 읽는다.
    students = data.read_students()

    # 로그인한 계정의 사용자 ID와 일치하는 학생을 찾는다.
    student = None
    for s in students:
        if s["사용자ID"] == user["사용자ID"]:
            student = s
            break

    # 연결된 학생 정보가 없으면 오류를 발생시킨다.
    if student is None:
        raise errors.DataError(
            errors.E_REF_MISSING,
            f"students.txt: 사용자 ID {user['사용자ID']}와 연결된 학생 레코드가 없습니다"
        )

    # 기획서에 지정된 화면을 출력한다.
    print()
    print(f"===== 학생 메뉴 ({student['이름']}님) > 내 정보 조회 =====")
    print()
    print(f"학생 ID: {student['학생ID']}")
    print(f"이름: {student['이름']}")
    print()

    # 0을 입력하면 이전 메뉴로 돌아간다.
    while True:
        print("0. 이전 메뉴")
        choice = ui.ask_menu_choice([0])

        if choice == 0:
            return

# 6.4.2
def show_class_detail(user):
    """선택한 반의 상세 정보를 조회한다."""

    # 반 ID를 입력받는다.
    class_id = ui.ask_target("상세 조회할 반 ID를 입력하세요")

    # 빈 입력이면 아무것도 하지 않고 돌아간다.
    if class_id is None:
        return

    # 반 목록에서 입력한 ID와 일치하는 반을 찾는다.
    classes = data.read_classes()
    class_info = None

    for c in classes:
        if c["반ID"] == class_id:
            class_info = c
            break

    # 존재하지 않는 반이면 오류를 출력한다.
    if class_info is None:
        print(
            f"[{errors.E_REF_MISSING}] "
            f"해당 반을 찾을 수 없습니다."
        )
        return

    # 과목 정보와 강사 정보를 불러온다.
    subjects = data.read_subjects()
    teachers = data.read_teachers()

    subject_name = "정보 없음"
    teacher_name = "정보 없음"

    for subject in subjects:
        if subject["과목ID"] == class_info["과목ID"]:
            subject_name = subject["과목명"]
            break

    for teacher in teachers:
        if teacher["강사ID"] == class_info["강사ID"]:
            teacher_name = teacher["이름"]
            break

    # 반 정보를 출력한다.
    print()
    print("===== 학생 메뉴 > 반 상세 정보 조회 =====")
    print(f"반 ID: {class_info['반ID']}")
    print(f"반 이름: {class_info['반이름']}")
    print(f"과목명: {subject_name}")
    print(f"담당 강사: {teacher_name}")
    print(f"수업 요일: {class_info['요일목록']}")
    print(
        f"교시: {class_info['시작교시']}~"
        f"{class_info['종료교시']}교시"
    )
    print(
        f"수업 기간: {class_info['시작날짜']}~"
        f"{class_info['종료날짜']}"
    )
    print(f"정원: {class_info['정원']}")
    print(f"반 상태: {class_info['반상태']}")



def list_open_classes(user):
    """학생이 수강 신청할 수 있는 반 목록을 조회한다."""

    # 로그인한 학생의 정보 확인
    students = data.read_students()
    student = None

    for s in students:
        if s["사용자ID"] == user["사용자ID"]:
            student = s
            break

    if student is None:
        print(f"[{errors.E_REF_MISSING}] 연결된 학생 정보를 찾을 수 없습니다.")
        return

    # 재원 상태인 학생만 신청 가능
    if student["학생상태"] != "재원":
        print("수강 신청할 수 있는 반이 없습니다.")
        return

    # 반, 과목, 강사, 수강 등록 정보 불러오기
    classes = data.read_classes()
    subjects = data.read_subjects()
    teachers = data.read_teachers()
    enrollments = data.read_enrollments()

    # 현재 수강 신청 가능한 반을 모을 목록
    available_classes = []

    today = data.now()[:10]

    for c in classes:
        # 폐강된 반은 제외
        if c["반상태"] != "개설":
            continue

        # 수업 시작일 당일 또는 그 이후에는 신청 불가
        if today >= c["시작날짜"]:
            continue

        # 이미 수강 중인 같은 반이 있으면 제외
        already_enrolled = False

        for e in enrollments:
            if (
                e["학생ID"] == student["학생ID"]
                and e["반ID"] == c["반ID"]
                and e["등록상태"] == "수강중"
            ):
                already_enrolled = True
                break

        if already_enrolled:
            continue

        # 정원 및 시간 충돌 검사는 공통 데이터 함수 구현 후 연결
        available_classes.append(c)

    # 신청 가능한 반이 없는 경우
    if not available_classes:
        print("현재 수강 신청할 수 있는 반이 없습니다.")
        return

    # 반 목록 출력
    print()
    print("===== 학생 메뉴 > 수강 가능한 반 조회 =====")
    print(
        "반 ID | 반 이름 | 과목명 | 담당 강사 | "
        "수업 요일 | 교시 | 수업 기간 | 현재 인원/정원"
    )

    for c in available_classes:
        subject_name = "정보 없음"
        teacher_name = "정보 없음"

        for s in subjects:
            if s["과목ID"] == c["과목ID"]:
                subject_name = s["과목명"]
                break

        for t in teachers:
            if t["강사ID"] == c["강사ID"]:
                teacher_name = t["이름"]
                break

        # count_enrolled() 구현 전에는 현재 인원을 계산할 수 없음
        print(
            f"{c['반ID']} | {c['반이름']} | {subject_name} | "
            f"{teacher_name} | {c['요일목록']} | "
            f"{c['시작교시']}~{c['종료교시']}교시 | "
            f"{c['시작날짜']}~{c['종료날짜']} | "
            f"미구현/{c['정원']}"
        )

    print()
    print("상세 조회할 반 ID를 입력하세요.")





# ---- 6.5 강사 메뉴 ----


# ---- 6.6.5 수강 등록 조회·취소 (원장) ----
