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
    current_count = data.count_enrolled(class_info["반ID"])
    
    if current_count is None:
        print(f"현재 인원/정원: 미구현/{class_info['정원']}")
    else:
        print(f"현재 인원/정원: {current_count}/{class_info['정원']}")
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

        # 정원 확인
        current_count = data.count_enrolled(c["반ID"])

        # 공통 함수가 미구현이면 목록에 포함하지 않는다.
        if current_count is None:
            print("수강 인원 계산 기능이 아직 구현되지 않았습니다.")
            return

        if current_count >= int(c["정원"]):
            continue

        # 기존 수강 반과 시간표 충돌 확인
        has_conflict = False

        for e in enrollments:
            if (
                e["학생ID"] != student["학생ID"]
                or e["등록상태"] != "수강중"
            ):
                continue

            other_class = next(
                (other for other in classes
                 if other["반ID"] == e["반ID"]),
                None
            )

            if other_class is None:
                print(f"[{errors.E_REF_MISSING}] 기존 수강 반을 찾을 수 없습니다.")
                return

            if other_class["반상태"] != "개설":
                continue

            conflict = data.is_schedule_conflict(c, other_class)

            if conflict is None:
                print("시간표 충돌 검사 기능이 아직 구현되지 않았습니다.")
                return

            if conflict:
                has_conflict = True
                break

        if has_conflict:
            continue

        # 모든 조건을 통과한 반만 목록에 추가
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

        print(
            f"{c['반ID']} | {c['반이름']} | {subject_name} | "
            f"{teacher_name} | {c['요일목록']} | "
            f"{c['시작교시']}~{c['종료교시']}교시 | "
            f"{c['시작날짜']}~{c['종료날짜']} | "
            f"{data.count_enrolled(c['반ID'])}/{c['정원']}"
        )

    print()
    while True:
        class_id = ui.ask_target("상세 조회할 반 ID를 입력하세요 (0: 이전 메뉴)")
        if class_id is None or class_id == "0":
            return
        selected = next((c for c in available_classes if c["반ID"] == class_id), None)
        if selected is None:
            print(f"[{errors.E_REF_MISSING}] 목록에 없는 반 ID입니다.")
            continue
        subject = next((x for x in subjects if x["과목ID"] == selected["과목ID"]), None)
        teacher = next((x for x in teachers if x["강사ID"] == selected["강사ID"]), None)
        print("===== 학생 메뉴 > 반 상세 정보 조회 =====")
        print(f"반 ID: {class_id}")
        print(f"반 이름: {selected['반이름']}")
        print(f"과목명: {subject['과목명'] if subject else '정보 없음'}")
        print(f"담당 강사: {teacher['이름'] if teacher else '정보 없음'}")
        print(f"수업 요일: {selected['요일목록']}")
        print(f"교시: {selected['시작교시']}~{selected['종료교시']}교시")
        print(f"수업 기간: {selected['시작날짜']}~{selected['종료날짜']}")
        print(f"현재 수강 인원: {data.count_enrolled(class_id)}")
        print(f"정원: {selected['정원']}")
        print(f"상태: {selected['반상태']}")
        ui.ask_menu_choice([0])
        return


# 6.4.4 수강 신청
def enroll_class(user):
    """로그인한 학생이 반을 수강 신청한다."""
    student = None
    for s in data.read_students():
        if s["사용자ID"] == user["사용자ID"]:
            student = s
            break
    if student is None:
        print(f"[{errors.E_REF_MISSING}] 학생 정보를 찾을 수 없습니다.")
        return

    while True:
        class_id = ui.ask_target("수강 신청할 반 ID를 입력하세요")
        if class_id is None or class_id == "0":
            return
        if len(class_id) != 5 or not class_id.startswith("C") or not class_id[1:].isdigit():
            print("반 ID 형식이 올바르지 않습니다.")
            continue

        classes = data.read_classes()
        class_info = next((c for c in classes if c["반ID"] == class_id), None)
        if class_info is None:
            print(f"[{errors.E_REF_MISSING}] 해당 반을 찾을 수 없습니다.")
            continue
        if student["학생상태"] != "재원":
            print("재원 상태인 학생만 수강 신청할 수 있습니다.")
            return
        if class_info["반상태"] != "개설":
            print("개설된 반만 신청할 수 있습니다.")
            continue
        if data.now()[:10] >= class_info["시작날짜"]:
            print("수업 시작일 전까지만 신청할 수 있습니다.")
            continue

        enrollments = data.read_enrollments()
        my_enrollments = [e for e in enrollments if e["학생ID"] == student["학생ID"] and e["등록상태"] == "수강중"]
        if any(e["반ID"] == class_id for e in my_enrollments):
            print(f"[{errors.E_ALREADY_ENROLLED}] 이미 수강 중인 반입니다.")
            continue
        current_count = data.count_enrolled(class_id)
        if current_count is None:
            print("수강 인원 계산 기능이 아직 구현되지 않았습니다.")
            return
        if current_count >= int(class_info["정원"]):
            print(f"[{errors.E_CLASS_FULL}] 해당 반의 정원이 가득 찼습니다. 수강 신청할 수 없습니다.")
            continue

        conflict_class = None
        for e in my_enrollments:
            other_class = next((c for c in classes if c["반ID"] == e["반ID"]), None)
            if other_class is None:
                print(f"[{errors.E_REF_MISSING}] 기존 수강 반을 찾을 수 없습니다.")
                return
            if other_class["반상태"] != "개설":
                continue
            conflict = data.is_schedule_conflict(class_info, other_class)
            if conflict is None:
                print("시간표 충돌 검사 기능이 아직 구현되지 않았습니다.")
                return
            if conflict:
                conflict_class = other_class
                break
        if conflict_class is not None:
            print(f"[{errors.E_STUDENT_CONFLICT}] 기존 수강 반 {conflict_class['반ID']}({conflict_class['반이름']})과 수업 시간이 겹칩니다.")
            continue

        subject = next((s for s in data.read_subjects() if s["과목ID"] == class_info["과목ID"]), None)
        teacher = next((t for t in data.read_teachers() if t["강사ID"] == class_info["강사ID"]), None)
        print(f"===== 학생 메뉴 > 수업 신청 > {class_id} =====")
        print(f"반 ID: {class_id}")
        print(f"반 이름: {class_info['반이름']}")
        print(f"과목명: {subject['과목명'] if subject else '정보 없음'}")
        print(f"담당 강사: {teacher['이름'] if teacher else '정보 없음'}")
        print(f"수업 요일: {class_info['요일목록']}")
        print(f"교시: {class_info['시작교시']}~{class_info['종료교시']}교시")
        print(f"현재 수강 인원: {current_count} / {class_info['정원']}")
        if not ui.ask_yes_no("수강 신청"):
            return

        enrollment_id = data.next_id(data.ID_ENROLLMENT)
        if enrollment_id is None:
            print("등록 ID 생성 기능이 아직 구현되지 않았습니다.")
            return
        enrollments.append({
            "등록ID": enrollment_id, "학생ID": student["학생ID"], "반ID": class_id,
            "등록일시": data.now(), "등록상태": "수강중", "취소일시": data.EMPTY,
        })
        if not data.write_enrollments(enrollments):
            print(f"[{errors.E_SAVE}] 저장하지 못했습니다.")
            return
        print("수강 신청이 완료되었습니다.")
        return


# 6.4.5 내 수강 목록 조회
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
        if (
            e["학생ID"] == student["학생ID"]
            and e["등록상태"] == "수강중"
        )
    ]

    print()
    print("===== 학생 메뉴 > 내 수강 목록 조회 =====")

    if not my_enrollments:
        print("현재 수강 중인 반이 없습니다.")
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


# 6.4.6 수강 취소
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
        print(f"[{errors.E_REF_MISSING}] 해당 수강 정보를 찾을 수 없습니다.")
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
    subject = next((s for s in data.read_subjects() if s["과목ID"] == class_info["과목ID"]), None)
    teacher = next((t for t in data.read_teachers() if t["강사ID"] == class_info["강사ID"]), None)
    print(f"과목명: {subject['과목명'] if subject else '정보 없음'}")
    print(f"담당 강사: {teacher['이름'] if teacher else '정보 없음'}")
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

# ---- 6.5 강사 메뉴 ----

# 6.5.1 담당 반 조회
def list_teacher_classes(user):
    """로그인한 강사가 담당하는 반 목록을 조회한다."""

    teacher = next(
        (t for t in data.read_teachers()
         if t["사용자ID"] == user["사용자ID"]),
        None
    )

    if teacher is None:
        print(f"[{errors.E_REF_MISSING}] 강사 정보를 찾을 수 없습니다.")
        return

    classes = data.read_classes()
    subjects = data.read_subjects()

    my_classes = [
        c for c in classes
        if c["강사ID"] == teacher["강사ID"]
    ]

    print()
    print("===== 강사 메뉴 > 담당 반 조회 =====")

    if not my_classes:
        print("담당하는 반이 없습니다.")
        return

    for c in my_classes:
        subject = next(
            (s for s in subjects if s["과목ID"] == c["과목ID"]),
            None
        )
        subject_name = subject["과목명"] if subject else "정보 없음"

        print()
        print(f"반 ID: {c['반ID']}")
        print(f"반 이름: {c['반이름']}")
        print(f"과목명: {subject_name}")
        print(f"요일: {c['요일목록']}")
        print(f"교시: {c['시작교시']}~{c['종료교시']}교시")
        print(f"기간: {c['시작날짜']}~{c['종료날짜']}")
        current_count = data.count_enrolled(c["반ID"])
        print(f"현재 인원/정원: {current_count if current_count is not None else '미구현'}/{c['정원']}")
        print(f"반 상태: {c['반상태']}")


# 6.5.2 담당 반 수강생 조회
def list_class_students(user):
    """강사가 담당하는 반의 수강생을 조회한다."""
    teacher = next((t for t in data.read_teachers() if t["사용자ID"] == user["사용자ID"]), None)
    if teacher is None:
        print(f"[{errors.E_REF_MISSING}] 강사 정보를 찾을 수 없습니다.")
        return
    classes = data.read_classes()
    my_classes = [c for c in classes if c["강사ID"] == teacher["강사ID"]]
    if not my_classes:
        print("담당하고 있는 반이 없습니다.")
        return
    subjects = data.read_subjects()
    while True:
        print(f"===== 강사 메뉴 ({teacher['이름']}님) > 담당 반 수강생 조회 =====")
        print("반 ID | 반 이름 | 과목명 | 요일 | 교시")
        for c in my_classes:
            subject = next((s for s in subjects if s["과목ID"] == c["과목ID"]), None)
            print(f"{c['반ID']} | {c['반이름']} | {subject['과목명'] if subject else '정보 없음'} | {c['요일목록']} | {c['시작교시']}~{c['종료교시']}교시")
        class_id = ui.ask_target("조회할 반 ID를 입력하세요 (0: 이전 메뉴)")
        if class_id is None or class_id == "0":
            return
        if len(class_id) != 5 or not class_id.startswith("C") or not class_id[1:].isdigit():
            print("반 ID 형식이 올바르지 않습니다.")
            continue
        class_info = next((c for c in classes if c["반ID"] == class_id), None)
        if class_info is None:
            print(f"[{errors.E_REF_MISSING}] 해당 반을 찾을 수 없습니다.")
            continue
        if class_info["강사ID"] != teacher["강사ID"]:
            print(f"[{errors.E_NO_PERMISSION}] 해당 반의 수강생 정보를 조회할 권한이 없습니다.")
            continue
        subject = next((s for s in subjects if s["과목ID"] == class_info["과목ID"]), None)
        print(f"반 ID: {class_id} / 반 이름: {class_info['반이름']} / 과목명: {subject['과목명'] if subject else '정보 없음'}")
        print("학생 ID | 학생 이름 | 수강 상태")
        students = data.read_students()
        active = [e for e in data.read_enrollments() if e["반ID"] == class_id and e["등록상태"] == "수강중"]
        if not active:
            print("현재 수강 중인 학생이 없습니다.")
        for e in active:
            student = next((s for s in students if s["학생ID"] == e["학생ID"]), None)
            if student is None:
                print(f"[{errors.E_REF_MISSING}] 학생 정보를 찾을 수 없습니다.")
                continue
            print(f"{student['학생ID']} | {student['이름']} | {e['등록상태']}")


# 6.5.3 수업 일정 조회
def show_teacher_schedule(user):
    """강사가 현재 진행 중인 담당 반의 수업 일정을 조회한다."""

    teacher = next(
        (t for t in data.read_teachers()
         if t["사용자ID"] == user["사용자ID"]),
        None
    )

    if teacher is None:
        print(f"[{errors.E_REF_MISSING}] 강사 정보를 찾을 수 없습니다.")
        return

    today = data.now()[:10]

    classes = [
        c for c in data.read_classes()
        if (
            c["강사ID"] == teacher["강사ID"]
            and c["반상태"] == "개설"
            and c["시작날짜"] <= today <= c["종료날짜"]
        )
    ]

    weekday_order = {
        "월": 0, "화": 1, "수": 2, "목": 3,
        "금": 4, "토": 5, "일": 6
    }

    def schedule_key(c):
        days = [
            weekday_order[d]
            for d in c["요일목록"]
            if d in weekday_order
        ]
        return (
            min(days) if days else 7,
            int(c["시작교시"]),
            c["반ID"]
        )

    classes.sort(key=schedule_key)

    print()
    print("===== 강사 메뉴 > 수업 일정 조회 =====")

    if not classes:
        print("현재 진행 중인 수업이 없습니다.")
        return

    for c in classes:
        print(
            f"{c['요일목록']} | "
            f"{c['시작교시']}~{c['종료교시']}교시 | "
            f"{c['반ID']} | {c['반이름']}"
        )



# ---- 6.6.5 원장 메뉴: 수강 등록 관리 ----

# 전체 수강 등록 조회
def list_all_enrollments(user):
    """원장이 전체 수강 등록 기록을 조회한다."""

    enrollments = data.read_enrollments()
    students = data.read_students()
    classes = data.read_classes()

    print()
    print("===== 원장 메뉴 > 전체 수강 등록 조회 =====")

    if not enrollments:
        print("등록된 수강 등록이 없습니다.")
        return

    # 등록 ID 순서로 정렬
    for e in sorted(enrollments, key=lambda x: x["등록ID"]):
        student = next(
            (s for s in students if s["학생ID"] == e["학생ID"]),
            None
        )
        class_info = next(
            (c for c in classes if c["반ID"] == e["반ID"]),
            None
        )

        student_name = student["이름"] if student else "정보 없음"
        class_name = class_info["반이름"] if class_info else "정보 없음"

        print(
            f"{e['등록ID']} | "
            f"{e['학생ID']}({student_name}) | "
            f"{e['반ID']}({class_name}) | "
            f"{e['등록일시']} | "
            f"{e['등록상태']} | "
            f"취소일시: {e['취소일시']}"
        )


# 반별 수강 등록 조회
def list_enrollments_by_class(user):
    """원장이 특정 반의 수강 등록 기록을 조회한다."""

    while True:
        class_id = ui.ask_target("조회할 반 ID를 입력하세요")
        if class_id is None or class_id == "0":
            return
        if any(c["반ID"] == class_id for c in data.read_classes()):
            break
        print(f"[{errors.E_REF_MISSING}] 존재하지 않는 반 ID입니다.")

    classes = data.read_classes()
    class_info = next(
        (c for c in classes if c["반ID"] == class_id),
        None
    )

    if class_info is None:
        print(f"[{errors.E_REF_MISSING}] 해당 반을 찾을 수 없습니다.")
        return

    enrollments = [
        e for e in data.read_enrollments()
        if e["반ID"] == class_id
    ]
    students = data.read_students()

    print()
    print(f"===== {class_info['반이름']} 수강 등록 조회 =====")

    if not enrollments:
        print("해당 반에 수강 등록이 없습니다.")

    for e in sorted(enrollments, key=lambda x: x["등록ID"]):
        student = next(
            (s for s in students if s["학생ID"] == e["학생ID"]),
            None
        )
        student_name = student["이름"] if student else "정보 없음"

        print(
            f"{e['등록ID']} | "
            f"{e['학생ID']}({student_name}) | "
            f"{e['등록일시']} | "
            f"{e['등록상태']} | "
            f"취소일시: {e['취소일시']}"
        )

    current_count = data.count_enrolled(class_id)
    print(f"수강중 인원: {current_count if current_count is not None else '미구현'} / 정원: {class_info['정원']}")


# 학생별 수강 등록 조회
def list_enrollments_by_student(user):
    """원장이 특정 학생의 수강 등록 기록을 조회한다."""

    while True:
        student_id = ui.ask_target("조회할 학생 ID를 입력하세요")
        if student_id is None or student_id == "0":
            return
        if any(s["학생ID"] == student_id for s in data.read_students()):
            break
        print(f"[{errors.E_REF_MISSING}] 존재하지 않는 학생 ID입니다.")

    students = data.read_students()
    student = next(
        (s for s in students if s["학생ID"] == student_id),
        None
    )

    if student is None:
        print(f"[{errors.E_REF_MISSING}] 해당 학생을 찾을 수 없습니다.")
        return

    enrollments = [
        e for e in data.read_enrollments()
        if e["학생ID"] == student_id
    ]
    classes = data.read_classes()

    print()
    print(f"===== {student['이름']} 학생 수강 등록 조회 =====")

    if not enrollments:
        print("해당 학생의 수강 등록이 없습니다.")
        return

    for e in sorted(enrollments, key=lambda x: x["등록ID"]):
        class_info = next(
            (c for c in classes if c["반ID"] == e["반ID"]),
            None
        )
        class_name = class_info["반이름"] if class_info else "정보 없음"
        schedule = f"{class_info['요일목록']} {class_info['시작교시']}~{class_info['종료교시']}교시" if class_info else "정보 없음"

        print(
            f"{e['등록ID']} | "
            f"{e['반ID']}({class_name}) | "
            f"{schedule} | "
            f"{e['등록일시']} | "
            f"{e['등록상태']} | "
            f"취소일시: {e['취소일시']}"
        )


# 원장 수강 등록 취소
def admin_cancel_enrollment(user):
    """원장이 등록 ID를 지정해 수강 등록을 취소한다."""

    enrollment_id = ui.ask_target("취소할 등록 ID를 입력하세요")
    if enrollment_id is None:
        return

    enrollments = data.read_enrollments()

    target = next(
        (e for e in enrollments if e["등록ID"] == enrollment_id),
        None
    )

    if target is None:
        print(f"[{errors.E_REF_MISSING}] 존재하지 않는 수강 등록 ID입니다.")
        return

    if target["등록상태"] != "수강중":
        print(f"[{errors.E_ENROLL_ALREADY_CANCELLED}] 이미 취소된 수강 등록입니다.")
        return

    print()
    print("===== 취소 대상 확인 =====")
    print(f"등록 ID: {target['등록ID']}")
    student = next((s for s in data.read_students() if s["학생ID"] == target["학생ID"]), None)
    class_info = next((c for c in data.read_classes() if c["반ID"] == target["반ID"]), None)
    print(f"학생: {target['학생ID']} {student['이름'] if student else '정보 없음'}")
    print(f"반: {target['반ID']} {class_info['반이름'] if class_info else '정보 없음'}")
    print(f"등록일시: {target['등록일시']}")
    print(f"등록 상태: {target['등록상태']}")

    if not ui.ask_yes_no(
        f"등록 {enrollment_id}의 수강을 취소"
    ):
        return

    # 기록을 삭제하지 않고 취소 상태로 변경
    target["등록상태"] = "취소"
    target["취소일시"] = data.now()

    if not data.write_enrollments(enrollments):
        print(f"[{errors.E_SAVE}] 저장하지 못했습니다.")
        return

    print(f"[OK_ENROLL_CANCEL] 수강 등록 {enrollment_id}이 취소되었습니다.")
