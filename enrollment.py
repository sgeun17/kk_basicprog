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


# 6.4.3 수강 신청
def enroll_class(user):
    """로그인한 학생이 반을 수강 신청한다."""

    # 로그인한 학생 찾기
    student = None
    for s in data.read_students():
        if s["사용자ID"] == user["사용자ID"]:
            student = s
            break

    if student is None:
        print(f"[{errors.E_REF_MISSING}] 학생 정보를 찾을 수 없습니다.")
        return

    if student["학생상태"] != "재원":
        print("재원 상태인 학생만 수강 신청할 수 있습니다.")
        return

    # 신청할 반 ID 입력
    class_id = ui.ask_target("수강 신청할 반 ID를 입력하세요")
    if class_id is None:
        return

    # 반 정보 찾기
    classes = data.read_classes()
    class_info = None

    for c in classes:
        if c["반ID"] == class_id:
            class_info = c
            break

    if class_info is None:
        print(f"[{errors.E_REF_MISSING}] 해당 반을 찾을 수 없습니다.")
        return

    # 반 상태 및 신청 기간 확인
    if class_info["반상태"] != "개설":
        print("개설된 반만 신청할 수 있습니다.")
        return

    if data.now()[:10] >= class_info["시작날짜"]:
        print("수업 시작일 전까지만 신청할 수 있습니다.")
        return

    # 기존 수강 등록 정보 확인
    enrollments = data.read_enrollments()

    for e in enrollments:
        if (
            e["학생ID"] == student["학생ID"]
            and e["반ID"] == class_id
            and e["등록상태"] == "수강중"
        ):
            print("이미 수강 중인 반입니다.")
            return

    # 정원 확인
    current_count = data.count_enrolled(class_id)

    if current_count is None:
        print("수강 인원 계산 기능이 아직 구현되지 않았습니다.")
        return

    if current_count >= int(class_info["정원"]):
        print("정원이 가득 찬 반입니다.")
        return

    # 시간표 충돌 확인
    for e in enrollments:
        if (
            e["학생ID"] != student["학생ID"]
            or e["등록상태"] != "수강중"
        ):
            continue

        other_class = None
        for c in classes:
            if c["반ID"] == e["반ID"]:
                other_class = c
                break

        if other_class is None:
            print(f"[{errors.E_REF_MISSING}] 기존 수강 반을 찾을 수 없습니다.")
            return

        conflict = data.is_schedule_conflict(class_info, other_class)

        if conflict is None:
            print("시간표 충돌 검사 기능이 아직 구현되지 않았습니다.")
            return

        if conflict:
            print("이미 수강 중인 반과 수업 시간이 겹칩니다.")
            return

    # 최종 확인
    if not ui.ask_yes_no(
        f"반 {class_id}({class_info['반이름']})을 수강 신청"
    ):
        return

    # 등록 ID 생성
    enrollment_id = data.next_id(data.ID_ENROLLMENT)

    if enrollment_id is None:
        print("등록 ID 생성 기능이 아직 구현되지 않았습니다.")
        return

    # 등록 정보 생성
    new_enrollment = {
        "등록ID": enrollment_id,
        "학생ID": student["학생ID"],
        "반ID": class_id,
        "등록일시": data.now(),
        "등록상태": "수강중",
        "취소일시": data.EMPTY,
    }

    enrollments.append(new_enrollment)

    # 저장
    if not data.write_enrollments(enrollments):
        print(f"[{errors.E_SAVE}] 저장하지 못했습니다.")
        return

    print("수강 신청이 완료되었습니다.")


# 6.4.4 내 수강 목록 조회
def list_my_enrollments(user):
    """로그인한 학생의 수강 등록 내역을 조회한다."""

    student = None
    for s in data.read_students():
        if s["사용자ID"] == user["사용자ID"]:
            student = s
            break

    if student is None:
        print(f"[{errors.E_REF_MISSING}] 학생 정보를 찾을 수 없습니다.")
        return

    enrollments = data.read_enrollments()
    classes = data.read_classes()
    subjects = data.read_subjects()
    teachers = data.read_teachers()

    my_enrollments = [
        e for e in enrollments
        if e["학생ID"] == student["학생ID"]
    ]

    print()
    print("===== 학생 메뉴 > 내 수강 목록 조회 =====")

    if not my_enrollments:
        print("수강 등록 내역이 없습니다.")
        return

    for e in my_enrollments:
        class_info = next(
            (c for c in classes if c["반ID"] == e["반ID"]),
            None
        )

        if class_info is None:
            print(f"[{errors.E_REF_MISSING}] 반 정보를 찾을 수 없습니다.")
            continue

        subject = next(
            (s for s in subjects
             if s["과목ID"] == class_info["과목ID"]),
            None
        )
        teacher = next(
            (t for t in teachers
             if t["강사ID"] == class_info["강사ID"]),
            None
        )

        subject_name = subject["과목명"] if subject else "정보 없음"
        teacher_name = teacher["이름"] if teacher else "정보 없음"

        print()
        print(f"등록 ID: {e['등록ID']}")
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
        print(f"등록 상태: {e['등록상태']}")


# 6.4.5 수강 취소
def cancel_enrollment(user):
    """로그인한 학생의 수강 등록을 취소한다."""

    # 로그인한 학생 찾기
    student = None
    for s in data.read_students():
        if s["사용자ID"] == user["사용자ID"]:
            student = s
            break

    if student is None:
        print(f"[{errors.E_REF_MISSING}] 학생 정보를 찾을 수 없습니다.")
        return

    # 취소할 반 ID 입력
    class_id = ui.ask_target("수강 취소할 반 ID를 입력하세요")

    if class_id is None:
        return

    enrollments = data.read_enrollments()
    classes = data.read_classes()

    # 해당 학생의 수강 중인 등록 찾기
    target = None

    for e in enrollments:
        if (
            e["학생ID"] == student["학생ID"]
            and e["반ID"] == class_id
            and e["등록상태"] == "수강중"
        ):
            target = e
            break

    if target is None:
        print("해당 반의 수강 중인 등록 내역이 없습니다.")
        return

    # 반 정보 찾기
    class_info = next(
        (c for c in classes if c["반ID"] == class_id),
        None
    )

    if class_info is None:
        print(f"[{errors.E_REF_MISSING}] 반 정보를 찾을 수 없습니다.")
        return

    # 수강 취소 대상 확인
    print()
    print("===== 학생 메뉴 > 수강 취소 =====")
    print(f"반 ID: {class_id}")
    print(f"반 이름: {class_info['반이름']}")
    print(f"등록 ID: {target['등록ID']}")
    print(f"등록 상태: {target['등록상태']}")

    # 최종 확인
    if not ui.ask_yes_no(
        f"반 {class_id}({class_info['반이름']})의 수강을 취소"
    ):
        return

    # 기존 기록을 삭제하지 않고 상태만 변경
    target["등록상태"] = "취소"
    target["취소일시"] = data.now()

    # 저장
    if not data.write_enrollments(enrollments):
        print(f"[{errors.E_SAVE}] 저장하지 못했습니다.")
        return

    print("수강 취소가 완료되었습니다.")


# ---- 6.5 강사 메뉴 ----


# ---- 6.6.5 수강 등록 조회·취소 (원장) ----
