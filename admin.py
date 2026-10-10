"""원장 기능: 학생·강사·과목·반 관리 — 담당 3 (학생 관리는 5)

기획서 6.6.1 학생 관리, 6.6.2 강사 관리, 6.6.3 과목 관리, 6.6.4 반 관리를 구현한다.
6.6.8 계정 비밀번호 관리는 아직 담당이 정해지지 않았다.

이 파일은 data.py, ui.py, errors.py 만 import 한다.
enrollment.py 는 import 하지 않는다. 반 폐강·학생 퇴원 때 수강 등록을 취소하거나
정원을 바꿀 때 수강 인원을 세는 일은 data.py 의 함수로 한다.
enrollment.py 를 import 하면 둘이 서로 기대게 되어 구조를 설명하기 어려워지고,
"from enrollment import ..." 로 쓰면 실제로 켜지지 않는다.

메뉴에 연결되는 함수는 로그인한 사용자 레코드를 인자로 받는다.
    def list_students(user): ...
함수를 만들면 이름을 노션에 적어서 1 에게 알린다.

노션에 적을 이름 — main.py 가 메뉴에 거는 함수
    manage_students   6.6.1
    manage_teachers   6.6.2
    manage_subjects   6.6.3
    manage_classes    6.6.4

값 검사(data.is_*)와 공통 계산(data.next_id, data.count_enrolled,
data.is_schedule, data.is_schedule_conflict, data.sort_weekday_list,
data.display_class_status, data.write_all)은 담당 2 가 data.py 에 채운다.
여기서는 그 함수들을 약속된 이름 그대로 부른다. 아직 비어 있는 동안에는
돌려주는 값이 None 이라 검사에 걸리거나 화면에 "-" 로 보인다.
"""

import data
import errors
import ui


# ---- 이 파일 안에서만 쓰는 도움 함수 ----

def _print_error(code, message=None):
    """[코드] 메시지 형식으로 출력한다. message 를 안 주면 errors.ERROR_MESSAGES 의 문장을 쓴다."""
    if message is None:
        message = errors.ERROR_MESSAGES[code]
    print(f"[{code}] {message}")


def _find(records, key, value):
    """key 필드가 value 인 레코드를 돌려준다. 없으면 None."""
    for record in records:
        if record[key] == value:
            return record
    return None


def _sorted_by(records, key):
    """6.1.6 조회 결과는 내부 식별자 오름차순으로 출력한다."""
    return sorted(records, key=lambda record: record[key])


def _ask_id(label, records, key, missing_message):
    """대상 ID 를 받는다. 없는 ID 면 오류를 출력하고 다시 묻는다. 빈 입력이면 None. (6.1.5)"""
    while True:
        target_id = ui.ask_target(label)
        if target_id is None:
            return None
        record = _find(records, key, target_id)
        if record is None:
            _print_error(errors.E_REF_MISSING, missing_message)
            continue
        return record


def _ask_valid(label, is_valid, field_name, strip=True):
    """형식이 맞을 때까지 다시 묻는다. /cancel 이면 ui.InputCancelled 가 그대로 올라간다. (6.1.5)"""
    while True:
        value = ui.ask_required(label, strip=strip)
        if is_valid(value):
            return value
        _print_error(errors.E_FILE_FORMAT, f"{field_name} 형식이 올바르지 않습니다.")


def _ask_new_user_id():
    """새 계정의 사용자 ID 를 받는다. 형식(4.1.1)과 중복(users.txt)을 본다."""
    while True:
        user_id = _ask_valid("사용자 ID", data.is_user_id, "사용자 ID")
        if _find(data.read_users(), "사용자ID", user_id) is not None:
            _print_error(errors.E_DUP_ID)
            continue
        return user_id


def _run_submenu(screen, actions, user):
    """하위 메뉴 화면을 보여주고 고른 기능을 실행한다. 0 이면 이전 메뉴로 돌아간다. (6.1.1, 6.1.2)"""
    valid = list(actions) + [0]
    while True:
        print()
        print(screen)
        choice = ui.ask_menu_choice(valid)
        if choice is None:
            continue
        if choice == 0:
            return
        actions[choice](user)


def _subject_name(subjects, subject_id):
    """과목 ID 로 과목명을 찾는다. 참조가 깨져 있으면 빈 값("-")으로 보여 준다. (5.1.8)"""
    subject = _find(subjects, "과목ID", subject_id)
    return data.EMPTY if subject is None else subject["과목명"]


def _teacher_name(teachers, teacher_id):
    teacher = _find(teachers, "강사ID", teacher_id)
    return data.EMPTY if teacher is None else teacher["이름"]


def _class_title(class_, subjects):
    """4.2.3 — 화면에는 과목명과 반 이름을 붙여 "수학 A반" 으로 보여 준다."""
    return f"{_subject_name(subjects, class_['과목ID'])} {class_['반이름']}"


def _periods(class_):
    return f"{class_['시작교시']}~{class_['종료교시']}교시"


def _term(class_):
    return f"{class_['시작날짜']} ~ {class_['종료날짜']}"


def _class_status(class_):
    """4.6.3 표시 상태(모집중/진행중/종료/폐강).

    data.display_class_status 가 아직 비어 있으면 저장된 반 상태를 그대로 보여 준다.
    """
    shown = data.display_class_status(class_)
    return class_["반상태"] if shown is None else shown


def _enroll_status(enrollment, class_):
    """4.6.4 표시 상태(수강중/수강 완료/취소)."""
    if enrollment["등록상태"] == "취소":
        return "취소"
    if class_ is not None and _class_status(class_) == "종료":
        return "수강 완료"
    return "수강중"


def _enrolled(class_id):
    """4.13 그 반의 "수강중" 등록 수. data.count_enrolled 가 비어 있으면 None."""
    return data.count_enrolled(class_id)


def _enrolled_text(class_id):
    count = _enrolled(class_id)
    return data.EMPTY if count is None else str(count)


def _active_enrollments(enrollments, key, value):
    """그 학생(또는 반)의 "수강중" 수강 등록만 고른다."""
    return [e for e in enrollments if e[key] == value and e["등록상태"] == "수강중"]


def _cancel(enrollment):
    """수강 등록 한 건을 취소 상태로 바꾼다. 취소 일시는 가상 현재 일시다. (6.6.1.5, 6.6.4.5)"""
    enrollment["등록상태"] = "취소"
    enrollment["취소일시"] = data.now()


def _save(changes):
    """여러 파일을 함께 바꾼다. 실패하면 [E_SAVE] 를 출력하고 False. (5.4)"""
    if not data.write_all(changes):
        _print_error(errors.E_SAVE)
        return False
    return True


def _save_one(write, records):
    """파일 하나를 바꾼다. 실패하면 [E_SAVE] 를 출력하고 False."""
    if not write(records):
        _print_error(errors.E_SAVE)
        return False
    return True


# ---- 검색어 합치 판정 (4.2.1, 4.2.2, 4.5) ----
#
# 검색 규칙은 화면 기능마다 쓰는 것이라 data.py 가 아니라 여기에 둔다.
# data.same_phone 은 두 연락처가 같은 번호인지(동치)를 보는 함수고,
# 아래 _match_phone 은 검색어가 번호의 일부인지(부분문자열)를 본다.

def _fold(text):
    """4.2.1·4.2.2 검색 — 표준공백을 지우고 로마자 대소문자를 구분하지 않는다."""
    return text.replace(" ", "").lower()


def _match_name(query, name):
    """4.2.1 사람 이름 검색. 공백·대소문자를 무시한 부분문자열이면 합치."""
    return _fold(query) in _fold(name)


def _match_subject_name(query, subject_name):
    """4.2.2 과목명 검색. 규칙은 사람 이름과 같다."""
    return _fold(query) in _fold(subject_name)


def _match_phone(query, phone):
    """4.5 연락처 검색. 양쪽에서 "-" 를 지운 뒤 부분문자열이면 합치."""
    return query.replace("-", "") in phone.replace("-", "")


# ============================================================
# 6.6.1 학생 관리 — 5
# ============================================================

STUDENT_SCREEN = """===== 원장 메뉴 > 학생 관리 =====
1. 목록 조회
2. 상세 조회
3. 검색
4. 등록
5. 수정
6. 삭제
0. 이전 메뉴"""

STUDENT_SEARCH_SCREEN = """===== 학생 검색 =====
1. 이름으로 검색
2. 연락처로 검색
3. 이전 메뉴"""


def manage_students(user):
    """6.6.1 학생 관리 메뉴."""
    _run_submenu(STUDENT_SCREEN, {
        1: list_students,
        2: show_student,
        3: search_students,
        4: add_student,
        5: update_student,
        6: delete_student,
    }, user)


def _print_student_rows(students):
    """6.6.1.1 학생 목록 한 줄씩. 수강 반 수는 "수강중" 등록만 센다. (4.6.4)"""
    enrollments = data.read_enrollments()
    print(" 학생ID  이름                  연락처           사용자ID      상태  수강반수")
    for student in students:
        count = len(_active_enrollments(enrollments, "학생ID", student["학생ID"]))
        print(f" {student['학생ID']:<7}{student['이름']:<16}{student['연락처']:<17}"
              f"{student['사용자ID']:<14}{student['학생상태']:<6}{count}")


def list_students(user):
    """6.6.1.1 목록 조회. 재원·퇴원을 모두 학생 ID 오름차순으로 출력한다."""
    students = _sorted_by(data.read_students(), "학생ID")
    print()
    if not students:
        print("등록된 학생이 없습니다.")
        return
    _print_student_rows(students)


def show_student(user):
    """6.6.1.2 상세 조회. 수강 내역까지 보여 준다."""
    student = _ask_id("학생 ID를 입력하세요", data.read_students(),
                      "학생ID", "존재하지 않는 학생 ID입니다. 재입력")
    if student is None:
        return

    classes = data.read_classes()
    subjects = data.read_subjects()
    enrollments = [e for e in data.read_enrollments() if e["학생ID"] == student["학생ID"]]

    print()
    print(f"===== 학생 상세 ({student['학생ID']}) =====")
    print(f" 학생ID:    {student['학생ID']}")
    print(f" 이름:      {student['이름']}")
    print(f" 연락처:    {student['연락처']}")
    print(f" 사용자ID:  {student['사용자ID']}")
    print(f" 상태:      {student['학생상태']}")
    print(" 수강 내역:")
    if not enrollments:
        print("   수강 내역이 없습니다.")
        return
    for enrollment in _sorted_by(enrollments, "등록ID"):
        class_ = _find(classes, "반ID", enrollment["반ID"])
        if class_ is None:
            print(f"   {enrollment['등록ID']}  {enrollment['반ID']}  {data.EMPTY}")
            continue
        print(f"   {enrollment['등록ID']}  {class_['반ID']}  "
              f"{_class_title(class_, subjects):<14}{class_['요일목록']:<8}"
              f"{_periods(class_):<10}{_enroll_status(enrollment, class_):<8}"
              f"{enrollment['등록일시']}")


def search_students(user):
    """6.6.1.3 학생 검색. 이름 또는 연락처로 찾는다."""
    while True:
        print()
        print(STUDENT_SEARCH_SCREEN)
        choice = ui.ask_menu_choice([1, 2, 3])
        if choice is None:
            continue
        if choice == 3:
            return

        label = "검색할 이름을 입력하세요" if choice == 1 else "검색할 연락처를 입력하세요"
        query = ui.ask_target(label)
        if query is None:
            continue

        students = _sorted_by(data.read_students(), "학생ID")
        if choice == 1:
            found = [s for s in students if _match_name(query, s["이름"])]
        else:
            found = [s for s in students if _match_phone(query, s["연락처"])]

        print()
        if not found:
            print("검색 조건에 맞는 학생이 없습니다.")
            continue
        _print_student_rows(found)


def add_student(user):
    """6.6.1.4 등록. students.txt 와 users.txt 에 함께 추가한다."""
    try:
        name = _ask_valid("이름", data.is_person_name, "이름")
        phone = _ask_valid("연락처", data.is_phone, "연락처")
        user_id = _ask_new_user_id()
        # 5.3 비밀번호는 앞뒤 표준공백을 떼지 않고 입력값 그대로 검사한다
        password = _ask_valid("비밀번호", data.is_password, "비밀번호", strip=False)
    except ui.InputCancelled:
        return

    student_id = data.next_id(data.ID_STUDENT)
    if not ui.ask_yes_no(f"학생 {name}({student_id})을(를) 등록"):
        return

    students = data.read_students()
    users = data.read_users()
    students.append({"학생ID": student_id, "이름": name, "연락처": phone,
                     "사용자ID": user_id, "학생상태": "재원"})
    users.append({"사용자ID": user_id, "비밀번호": password, "사용자역할": "학생"})

    if _save({data.STUDENTS: students, data.USERS: users}):
        print(f"[OK_STUDENT_ADD] 학생 {student_id}({name})이 등록되었습니다.")


STUDENT_FIELD_SCREEN = """1. 이름
2. 연락처
3. 학생 상태 (재원 <-> 퇴원)
0. 이전 메뉴"""


def update_student(user):
    """6.6.1.5 수정. 이름·연락처·학생 상태만 바꿀 수 있다."""
    students = data.read_students()
    student = _ask_id("수정할 학생 ID를 입력하세요", students,
                      "학생ID", "존재하지 않는 학생 ID입니다. 재입력")
    if student is None:
        return

    while True:
        print()
        print(STUDENT_FIELD_SCREEN)
        choice = ui.ask_menu_choice([1, 2, 3, 0])
        if choice is None:
            continue
        if choice == 0:
            return

        try:
            if choice == 1:
                student["이름"] = _ask_valid("이름", data.is_person_name, "이름")
            elif choice == 2:
                student["연락처"] = _ask_valid("연락처", data.is_phone, "연락처")
            else:
                _change_student_status(student, students)
                return
        except ui.InputCancelled:
            return

        if _save_one(data.write_students, students):
            print(f"[OK_STUDENT_UPDATE] 학생 {student['학생ID']}의 정보가 수정되었습니다.")
        return


def _change_student_status(student, students):
    """6.6.1.5 학생 상태 재원 <-> 퇴원.

    퇴원으로 바꿀 때 그 학생의 "수강중" 수강 등록이 있으면 경고하고 확인을 받는다.
    확인하면 그 등록을 모두 취소 처리한다. 재원으로 되돌려도 취소된 등록은 복원하지 않는다.
    """
    if student["학생상태"] == "재원":
        new_status = "퇴원"
    else:
        new_status = "재원"

    enrollments = data.read_enrollments()
    targets = []
    if new_status == "퇴원":
        targets = _active_enrollments(enrollments, "학생ID", student["학생ID"])
        if targets:
            classes = data.read_classes()
            subjects = data.read_subjects()
            # 경고 코드(W_*)는 오류가 아니라서 errors.py 에 없다. 기획서 문장을 그대로 쓴다.
            print("[W_STUDENT_HAS_ENROLLMENTS] 이 학생은 다음 반에 수강중 수강 등록되어 있습니다:")
            for enrollment in _sorted_by(targets, "반ID"):
                class_ = _find(classes, "반ID", enrollment["반ID"])
                title = data.EMPTY if class_ is None else _class_title(class_, subjects)
                print(f"  {enrollment['반ID']}  {title}")
            print("퇴원 처리 시 위 수강 등록은 모두 자동으로 취소 처리됩니다.")
            if not ui.ask_yes_no("계속"):
                return

    student["학생상태"] = new_status
    if not targets:
        if _save_one(data.write_students, students):
            print(f"[OK_STUDENT_UPDATE] 학생 {student['학생ID']}의 정보가 수정되었습니다.")
        return

    for enrollment in targets:
        _cancel(enrollment)
    if _save({data.STUDENTS: students, data.ENROLLMENTS: enrollments}):
        print(f"[OK_STUDENT_UPDATE] 학생 {student['학생ID']}의 정보가 수정되었습니다. "
              f"수강중 수강 등록 {len(targets)}건이 함께 취소되었습니다.")


def delete_student(user):
    """6.6.1.6 삭제. 수강 등록 이력(수강중·취소)이 하나라도 있으면 삭제하지 않는다."""
    students = data.read_students()
    student = _ask_id("삭제할 학생 ID를 입력하세요", students,
                      "학생ID", "존재하지 않는 학생 ID입니다. 재입력")
    if student is None:
        return

    history = [e for e in data.read_enrollments() if e["학생ID"] == student["학생ID"]]
    if history:
        _print_error(errors.E_STUDENT_HAS_HISTORY)
        print("기존 기록을 유지하려면 학생 수정 메뉴에서 상태를 '퇴원'으로 변경하세요.")
        return

    if not ui.ask_yes_no(f"학생 {student['학생ID']}({student['이름']})을(를) 삭제"):
        return

    users = [u for u in data.read_users() if u["사용자ID"] != student["사용자ID"]]
    students = [s for s in students if s["학생ID"] != student["학생ID"]]
    if _save({data.STUDENTS: students, data.USERS: users}):
        print(f"[OK_STUDENT_DELETE] 학생 {student['학생ID']}이 삭제되었습니다.")


# ============================================================
# 6.6.2 강사 관리 — 3
# ============================================================

TEACHER_SCREEN = """===== 원장 메뉴 > 강사 관리 =====
1. 목록 조회
2. 상세 조회
3. 검색
4. 등록
5. 수정
6. 삭제
0. 이전 메뉴"""

TEACHER_SEARCH_SCREEN = """===== 강사 검색 =====
1. 이름으로 검색
2. 연락처로 검색
3. 이전 메뉴"""


def manage_teachers(user):
    """6.6.2 강사 관리 메뉴."""
    _run_submenu(TEACHER_SCREEN, {
        1: list_teachers,
        2: show_teacher,
        3: search_teachers,
        4: add_teacher,
        5: update_teacher,
        6: delete_teacher,
    }, user)


def _teacher_classes(classes, teacher_id, only_open=False):
    """그 강사를 담당 강사로 참조하는 반. only_open 이면 "개설" 상태만."""
    found = [c for c in classes if c["강사ID"] == teacher_id]
    if only_open:
        found = [c for c in found if c["반상태"] == "개설"]
    return _sorted_by(found, "반ID")


def _print_teacher_rows(teachers):
    """6.6.2.1 강사 목록 한 줄씩. 담당 반 수는 "개설" 상태 반만 센다."""
    classes = data.read_classes()
    print(" 강사ID  이름                  연락처           사용자ID      상태  담당반수")
    for teacher in teachers:
        count = len(_teacher_classes(classes, teacher["강사ID"], only_open=True))
        print(f" {teacher['강사ID']:<7}{teacher['이름']:<16}{teacher['연락처']:<17}"
              f"{teacher['사용자ID']:<14}{teacher['강사상태']:<6}{count}")


def list_teachers(user):
    """6.6.2.1 목록 조회. 강사 ID 오름차순."""
    teachers = _sorted_by(data.read_teachers(), "강사ID")
    print()
    if not teachers:
        print("등록된 강사가 없습니다.")
        return
    _print_teacher_rows(teachers)


def show_teacher(user):
    """6.6.2.2 상세 조회. 담당 반 목록까지 보여 준다."""
    teacher = _ask_id("강사 ID를 입력하세요", data.read_teachers(),
                      "강사ID", "존재하지 않는 강사 ID입니다. 재입력")
    if teacher is None:
        return

    subjects = data.read_subjects()
    classes = _teacher_classes(data.read_classes(), teacher["강사ID"])

    print()
    print(f"===== 강사 상세 ({teacher['강사ID']}) =====")
    print(f" 강사ID:    {teacher['강사ID']}")
    print(f" 이름:      {teacher['이름']}")
    print(f" 연락처:    {teacher['연락처']}")
    print(f" 사용자ID:  {teacher['사용자ID']}")
    print(f" 상태:      {teacher['강사상태']}")
    print(" 담당 반:")
    if not classes:
        print("   담당 중인 반이 없습니다.")
        return
    for class_ in classes:
        print(f"   {class_['반ID']}  {_class_title(class_, subjects):<14}"
              f"{class_['요일목록']:<8}{_periods(class_):<10}{_class_status(class_)}")


def search_teachers(user):
    """6.6.2.3 강사 검색. 이름 또는 연락처로 찾는다."""
    while True:
        print()
        print(TEACHER_SEARCH_SCREEN)
        choice = ui.ask_menu_choice([1, 2, 3])
        if choice is None:
            continue
        if choice == 3:
            return

        label = "검색할 이름을 입력하세요" if choice == 1 else "검색할 연락처를 입력하세요"
        query = ui.ask_target(label)
        if query is None:
            continue

        teachers = _sorted_by(data.read_teachers(), "강사ID")
        if choice == 1:
            found = [t for t in teachers if _match_name(query, t["이름"])]
        else:
            found = [t for t in teachers if _match_phone(query, t["연락처"])]

        print()
        if not found:
            print("검색 조건에 맞는 강사가 없습니다.")
            continue
        _print_teacher_rows(found)


def add_teacher(user):
    """6.6.2.4 등록. teachers.txt 와 users.txt 에 함께 추가한다."""
    try:
        name = _ask_valid("이름", data.is_person_name, "이름")
        phone = _ask_valid("연락처", data.is_phone, "연락처")
        user_id = _ask_new_user_id()
        password = _ask_valid("비밀번호", data.is_password, "비밀번호", strip=False)
    except ui.InputCancelled:
        return

    teacher_id = data.next_id(data.ID_TEACHER)
    if not ui.ask_yes_no(f"강사 {name}({teacher_id})을(를) 등록"):
        return

    teachers = data.read_teachers()
    users = data.read_users()
    teachers.append({"강사ID": teacher_id, "이름": name, "연락처": phone,
                     "사용자ID": user_id, "강사상태": "재직"})
    users.append({"사용자ID": user_id, "비밀번호": password, "사용자역할": "강사"})

    if _save({data.TEACHERS: teachers, data.USERS: users}):
        print(f"[OK_TEACHER_ADD] 강사 {teacher_id}({name})이 등록되었습니다.")


TEACHER_FIELD_SCREEN = """1. 이름
2. 연락처
3. 강사 상태 (재직 <-> 퇴직)
0. 이전 메뉴"""


def update_teacher(user):
    """6.6.2.5 수정. 이름·연락처·강사 상태만 바꿀 수 있다."""
    teachers = data.read_teachers()
    teacher = _ask_id("수정할 강사 ID를 입력하세요", teachers,
                      "강사ID", "존재하지 않는 강사 ID입니다. 재입력")
    if teacher is None:
        return

    while True:
        print()
        print(TEACHER_FIELD_SCREEN)
        choice = ui.ask_menu_choice([1, 2, 3, 0])
        if choice is None:
            continue
        if choice == 0:
            return

        try:
            if choice == 1:
                teacher["이름"] = _ask_valid("이름", data.is_person_name, "이름")
            elif choice == 2:
                teacher["연락처"] = _ask_valid("연락처", data.is_phone, "연락처")
            else:
                if not _change_teacher_status(teacher):
                    return
        except ui.InputCancelled:
            return

        if _save_one(data.write_teachers, teachers):
            print(f"[OK_TEACHER_UPDATE] 강사 {teacher['강사ID']}의 정보가 수정되었습니다.")
        return


def _change_teacher_status(teacher):
    """6.6.2.5 강사 상태 재직 <-> 퇴직. 바꾸기로 했으면 True.

    퇴직으로 바꿀 때 담당 중인 "개설" 상태 반이 있으면 경고하고 확인을 받는다.
    반의 담당 강사 정보는 그대로 둔다. 새 반 배정 대상에서만 빠진다.
    """
    new_status = "퇴직" if teacher["강사상태"] == "재직" else "재직"

    if new_status == "퇴직":
        classes = _teacher_classes(data.read_classes(), teacher["강사ID"], only_open=True)
        if classes:
            subjects = data.read_subjects()
            print("[W_TEACHER_HAS_CLASSES] 이 강사는 다음 반을 담당 중입니다:")
            for class_ in classes:
                print(f"  {class_['반ID']}  {_class_title(class_, subjects)}")
            print("퇴직 처리 후에도 기존 반 정보는 유지되지만, "
                  "새 반 개설·수정 시 배정 대상에서 제외됩니다.")
            if not ui.ask_yes_no("계속"):
                return False

    teacher["강사상태"] = new_status
    return True


def delete_teacher(user):
    """6.6.2.6 삭제. 그 강사를 참조하는 반이 하나라도 있으면 삭제하지 않는다."""
    teachers = data.read_teachers()
    teacher = _ask_id("삭제할 강사 ID를 입력하세요", teachers,
                      "강사ID", "존재하지 않는 강사 ID입니다. 재입력")
    if teacher is None:
        return

    # 폐강된 반도 강사 ID 를 참조하므로 함께 본다. (4.1.2 참조 무결성)
    classes = _teacher_classes(data.read_classes(), teacher["강사ID"])
    if classes:
        subjects = data.read_subjects()
        _print_error(errors.E_TEACHER_IN_USE)
        for class_ in classes:
            print(f"  {class_['반ID']} {_class_title(class_, subjects)}")
        print("강사 수정 메뉴에서 상태를 '퇴직'으로 변경하세요.")
        return

    if not ui.ask_yes_no(f"강사 {teacher['강사ID']}({teacher['이름']})을(를) 삭제"):
        return

    users = [u for u in data.read_users() if u["사용자ID"] != teacher["사용자ID"]]
    teachers = [t for t in teachers if t["강사ID"] != teacher["강사ID"]]
    if _save({data.TEACHERS: teachers, data.USERS: users}):
        print(f"[OK_TEACHER_DELETE] 강사 {teacher['강사ID']}이 삭제되었습니다.")


# ============================================================
# 6.6.3 과목 관리 — 3
# ============================================================

SUBJECT_SCREEN = """===== 원장 메뉴 > 과목 관리 =====
1. 목록 조회
2. 상세 조회
3. 과목 검색
4. 등록
5. 수정
6. 삭제
0. 이전 메뉴"""


def manage_subjects(user):
    """6.6.3 과목 관리 메뉴."""
    _run_submenu(SUBJECT_SCREEN, {
        1: list_subjects,
        2: show_subject,
        3: search_subjects,
        4: add_subject,
        5: update_subject,
        6: delete_subject,
    }, user)


def _subject_classes(classes, subject_id, only_open=False):
    """그 과목으로 개설된 반. only_open 이면 "개설" 상태만."""
    found = [c for c in classes if c["과목ID"] == subject_id]
    if only_open:
        found = [c for c in found if c["반상태"] == "개설"]
    return _sorted_by(found, "반ID")


def _print_subject_rows(subjects):
    """6.6.3.1 과목 목록 한 줄씩. 개설 반 수는 "개설" 상태 반만 센다."""
    classes = data.read_classes()
    print(" 과목ID   과목명                개설반수")
    for subject in subjects:
        count = len(_subject_classes(classes, subject["과목ID"], only_open=True))
        print(f" {subject['과목ID']:<9}{subject['과목명']:<22}{count}")


def list_subjects(user):
    """6.6.3.1 목록 조회. 과목 ID 오름차순."""
    subjects = _sorted_by(data.read_subjects(), "과목ID")
    print()
    if not subjects:
        print("등록된 과목이 없습니다.")
        return
    _print_subject_rows(subjects)


def show_subject(user):
    """6.6.3.2 상세 조회. 그 과목으로 개설된 반 목록까지 보여 준다."""
    subject = _ask_id("과목 ID를 입력하세요", data.read_subjects(),
                      "과목ID", "존재하지 않는 과목 ID입니다. 재입력")
    if subject is None:
        return

    teachers = data.read_teachers()
    classes = _subject_classes(data.read_classes(), subject["과목ID"], only_open=True)

    print()
    print(f"===== 과목 상세 ({subject['과목ID']}) =====")
    print(f" 과목ID:  {subject['과목ID']}")
    print(f" 과목명:  {subject['과목명']}")
    print(" 개설된 반:")
    if not classes:
        print("   개설된 반이 없습니다.")
        return
    for class_ in classes:
        teacher = f"{class_['강사ID']} {_teacher_name(teachers, class_['강사ID'])}"
        print(f"   {class_['반ID']}  {subject['과목명']} {class_['반이름']:<8}"
              f"{teacher:<14}{class_['요일목록']:<8}{_periods(class_)}")


def search_subjects(user):
    """6.6.3.3 과목 검색. 과목명으로 찾는다. (4.2.2 검색 규칙)"""
    query = ui.ask_target("검색할 과목명을 입력하세요")
    if query is None:
        return

    subjects = _sorted_by(data.read_subjects(), "과목ID")
    found = [s for s in subjects if _match_subject_name(query, s["과목명"])]

    print()
    if not found:
        print("검색 조건에 맞는 과목이 없습니다.")
        return
    _print_subject_rows(found)


def add_subject(user):
    """6.6.3.4 등록. 과목명 자체의 중복은 허용한다."""
    try:
        name = _ask_valid("과목명", data.is_subject_name, "과목명")
    except ui.InputCancelled:
        return

    subject_id = data.next_id(data.ID_SUBJECT)
    if not ui.ask_yes_no(f'과목 "{name}"({subject_id})을(를) 등록'):
        return

    subjects = data.read_subjects()
    subjects.append({"과목ID": subject_id, "과목명": name})
    if _save_one(data.write_subjects, subjects):
        print(f"[OK_SUBJECT_ADD] 과목 {subject_id}({name})이 등록되었습니다.")


def update_subject(user):
    """6.6.3.5 수정. 과목명만 바꿀 수 있다.

    반은 과목 ID 로 과목을 참조하므로, 이름만 바꾸면 반 화면의 과목명도 함께 바뀐다.
    """
    subjects = data.read_subjects()
    subject = _ask_id("수정할 과목 ID를 입력하세요", subjects,
                      "과목ID", "존재하지 않는 과목 ID입니다. 재입력")
    if subject is None:
        return

    try:
        subject["과목명"] = _ask_valid("새 과목명", data.is_subject_name, "과목명")
    except ui.InputCancelled:
        return

    if _save_one(data.write_subjects, subjects):
        print(f"[OK_SUBJECT_UPDATE] 과목 {subject['과목ID']}의 이름이 수정되었습니다.")


def delete_subject(user):
    """6.6.3.6 삭제. 그 과목을 참조하는 반이 하나라도 있으면 삭제하지 않는다."""
    subjects = data.read_subjects()
    subject = _ask_id("삭제할 과목 ID를 입력하세요", subjects,
                      "과목ID", "존재하지 않는 과목 ID입니다. 재입력")
    if subject is None:
        return

    # 폐강된 반도 과목 ID 를 참조하므로 함께 본다. (4.1.2 참조 무결성)
    classes = _subject_classes(data.read_classes(), subject["과목ID"])
    if classes:
        _print_error(errors.E_SUBJECT_IN_USE)
        for class_ in classes:
            print(f"  {class_['반ID']} {subject['과목명']} {class_['반이름']}")
        return

    if not ui.ask_yes_no(f'과목 "{subject["과목명"]}"({subject["과목ID"]})을(를) 삭제'):
        return

    subjects = [s for s in subjects if s["과목ID"] != subject["과목ID"]]
    if _save_one(data.write_subjects, subjects):
        print(f"[OK_SUBJECT_DELETE] 과목 {subject['과목ID']}이 삭제되었습니다.")


# ============================================================
# 6.6.4 반 관리 — 3
# ============================================================

CLASS_SCREEN = """===== 원장 메뉴 > 반 관리 =====
1. 목록 조회
2. 상세 조회
3. 개설
4. 수정
5. 폐강
0. 이전 메뉴"""


def manage_classes(user):
    """6.6.4 반 관리 메뉴."""
    _run_submenu(CLASS_SCREEN, {
        1: list_classes,
        2: show_class,
        3: open_class,
        4: update_class,
        5: close_class,
    }, user)


def list_classes(user):
    """6.6.4.1 목록 조회. 반 ID 오름차순."""
    classes = _sorted_by(data.read_classes(), "반ID")
    print()
    if not classes:
        print("등록된 반이 없습니다.")
        return

    subjects = data.read_subjects()
    teachers = data.read_teachers()
    print(" 반ID    반이름  과목                  강사            요일      교시       "
          "기간                        상태    인원")
    for class_ in classes:
        print(f" {class_['반ID']:<8}{class_['반이름']:<8}"
              f"{_subject_name(subjects, class_['과목ID']):<22}"
              f"{_teacher_name(teachers, class_['강사ID']):<16}"
              f"{class_['요일목록']:<10}{_periods(class_):<11}{_term(class_):<28}"
              f"{_class_status(class_):<8}"
              f"{_enrolled_text(class_['반ID'])}/{class_['정원']}")


def show_class(user):
    """6.6.4.2 상세 조회. 수강생 목록까지 보여 준다."""
    class_ = _ask_id("반 ID를 입력하세요", data.read_classes(),
                     "반ID", "존재하지 않는 반 ID입니다. 재입력")
    if class_ is None:
        return

    subjects = data.read_subjects()
    teachers = data.read_teachers()
    students = data.read_students()
    enrollments = _active_enrollments(data.read_enrollments(), "반ID", class_["반ID"])

    print()
    print(f"===== 반 상세 ({class_['반ID']}) =====")
    print(f" 반ID:      {class_['반ID']}")
    print(f" 반이름:    {class_['반이름']}")
    print(f" 과목:      {class_['과목ID']} {_subject_name(subjects, class_['과목ID'])}")
    print(f" 담당강사:  {class_['강사ID']} {_teacher_name(teachers, class_['강사ID'])}")
    print(f" 요일:      {class_['요일목록']}")
    print(f" 교시:      {_periods(class_)}")
    print(f" 기간:      {_term(class_)}")
    print(f" 정원:      {class_['정원']}")
    print(f" 현재인원:  {_enrolled_text(class_['반ID'])}")
    print(f" 상태:      {_class_status(class_)}")
    print()
    print(" 수강생:")
    if not enrollments:
        print("   수강생이 없습니다.")
        return
    for enrollment in _sorted_by(enrollments, "학생ID"):
        student = _find(students, "학생ID", enrollment["학생ID"])
        name = data.EMPTY if student is None else student["이름"]
        print(f"   {enrollment['학생ID']}  {name:<16}{_enroll_status(enrollment, class_)}")


def _conflicting_classes(class_, teacher_id, classes, except_id=None):
    """4.12.1 그 강사의 "개설" 상태 반 중 수업 일정이 충돌하는 반.

    except_id  일정 충돌을 다시 볼 때 자기 자신은 뺀다. (6.6.4.4 담당 강사 수정)

    data.is_schedule_conflict 에는 반 레코드 모양의 딕셔너리를 넘긴다.
    (시작날짜·종료날짜·요일목록·시작교시·종료교시 — 4.12 수업 일정)
    """
    found = []
    for other in _teacher_classes(classes, teacher_id, only_open=True):
        if except_id is not None and other["반ID"] == except_id:
            continue
        if data.is_schedule_conflict(class_, other):
            found.append(other)
    return found


def _print_conflicts(conflicts, subjects):
    """6.6.4.3 강사 시간 충돌 목록."""
    _print_error(errors.E_TEACHER_CONFLICT)
    for other in conflicts:
        print(f"  {other['반ID']}  {_class_title(other, subjects):<14}"
              f"{other['요일목록']:<8}{_periods(other):<10}{_term(other)}")


def _is_name_taken(classes, subject_id, class_name, except_id=None):
    """4.2.3 같은 과목의 폐강되지 않은 반 중에 같은 이름이 있는지."""
    for other in classes:
        if other["과목ID"] != subject_id or other["반상태"] == "폐강":
            continue
        if except_id is not None and other["반ID"] == except_id:
            continue
        if other["반이름"] == class_name:
            return True
    return False


def _ask_period(label):
    """4.10 교시. 문법(선행 0 없는 숫자 1~2자)과 의미(1~10)를 둘 다 본다."""
    while True:
        value = ui.ask_required(label)
        if data.is_period(value) and data.is_valid_period(value):
            return value
        _print_error(errors.E_FILE_FORMAT, "교시는 1 이상 10 이하의 정수여야 합니다.")


def _ask_capacity(label):
    """4.13 정원. 문법과 의미(1~99)를 둘 다 본다."""
    while True:
        value = ui.ask_required(label)
        if data.is_capacity(value) and data.is_valid_capacity(value):
            return value
        _print_error(errors.E_FILE_FORMAT, "정원은 1 이상 99 이하의 정수여야 합니다.")


def _ask_weekdays(label):
    """4.11.1 요일 목록. 저장은 표준형("월 수 금")으로 한다."""
    while True:
        value = ui.ask_required(label)
        if data.is_weekday_list(value) and data.is_valid_weekday_list(value):
            return data.sort_weekday_list(value)
        _print_error(errors.E_FILE_FORMAT, "요일 목록 형식이 올바르지 않습니다. 예: 월 수")


def open_class(user):
    """6.6.4.3 개설. 입력 → 검사 → 요약·확인 → 저장."""
    subjects = data.read_subjects()
    teachers = data.read_teachers()
    classes = data.read_classes()

    try:
        subject = _ask_reference("과목 ID", subjects, "과목ID", "존재하지 않는 과목 ID입니다.")
        class_name = _ask_valid("반 이름", data.is_class_name, "반 이름")
        teacher = _ask_teacher_in_service(teachers)
        weekdays = _ask_weekdays("요일 목록 (예: 월 수)")
        start_period, end_period = _ask_periods()
        start_date, end_date = _ask_term(weekdays, start_period, end_period)
        capacity = _ask_capacity("정원")
    except ui.InputCancelled:
        return

    class_id = data.next_id(data.ID_CLASS)
    new_class = {
        "반ID": class_id,
        "과목ID": subject["과목ID"],
        "반이름": class_name,
        "강사ID": teacher["강사ID"],
        "요일목록": weekdays,
        "시작교시": start_period,
        "종료교시": end_period,
        "시작날짜": start_date,
        "종료날짜": end_date,
        "정원": capacity,
        "반상태": "개설",
    }

    if _is_name_taken(classes, subject["과목ID"], class_name):
        _print_error(errors.E_CLASS_NAME_DUPLICATE)
        return

    conflicts = _conflicting_classes(new_class, teacher["강사ID"], classes)
    if conflicts:
        _print_conflicts(conflicts, subjects)
        return

    print()
    print(f" 과목:      {subject['과목ID']} {subject['과목명']}")
    print(f" 반이름:    {class_name}")
    print(f" 담당강사:  {teacher['강사ID']} {teacher['이름']}")
    print(f" 요일:      {weekdays}")
    print(f" 교시:      {_periods(new_class)}")
    print(f" 기간:      {_term(new_class)}")
    print(f" 정원:      {capacity}")
    print()
    print(" 강사 시간 충돌 검사: 이상 없음")
    print()
    if not ui.ask_yes_no(f"반 {class_id}({subject['과목명']} {class_name})을(를) 개설"):
        return

    classes.append(new_class)
    if _save_one(data.write_classes, classes):
        print(f"[OK_CLASS_ADD] 반 {class_id}({subject['과목명']} {class_name})이 개설되었습니다.")


def _ask_reference(label, records, key, missing_message):
    """존재해야 하는 참조 ID 를 받는다. 없으면 [E_REF_MISSING] 을 출력하고 다시 묻는다."""
    while True:
        value = ui.ask_required(label)
        record = _find(records, key, value)
        if record is not None:
            return record
        _print_error(errors.E_REF_MISSING, missing_message)


def _ask_teacher_in_service(teachers):
    """담당 강사 ID 를 받는다. 새 반에는 재직 강사만 배정할 수 있다. (6.6.4.3)"""
    while True:
        teacher = _ask_reference("담당 강사 ID", teachers, "강사ID", "존재하지 않는 강사 ID입니다.")
        if teacher["강사상태"] == "재직":
            return teacher
        _print_error(errors.E_TEACHER_RETIRED)


def _ask_periods():
    """시작 교시와 종료 교시를 받는다. 시작 ≤ 종료. (4.12)"""
    while True:
        start_period = _ask_period("시작 교시")
        end_period = _ask_period("종료 교시")
        if int(start_period) <= int(end_period):
            return start_period, end_period
        _print_error(errors.E_FILE_FORMAT, "종료 교시는 시작 교시와 같거나 이후여야 합니다.")


def _ask_term(weekdays, start_period, end_period):
    """시작 날짜와 종료 날짜를 받는다.

    시작 ≤ 종료, 시작 날짜는 가상 현재 일시의 날짜 이후,
    그리고 4.12 의 수업 일정 조건(시작·종료 날짜의 요일이 요일 목록에 있어야 함)을 본다.
    """
    while True:
        start_date = _ask_valid("시작 날짜 (YYYY-MM-DD)", data.is_date, "시작 날짜")
        end_date = _ask_valid("종료 날짜 (YYYY-MM-DD)", data.is_date, "종료 날짜")

        if end_date < start_date:
            _print_error(errors.E_FILE_FORMAT, "종료 날짜는 시작 날짜와 같거나 이후여야 합니다.")
            continue

        today = data.now()[:10]
        if start_date < today:
            _print_error(errors.E_DATE_PAST,
                         errors.ERROR_MESSAGES[errors.E_DATE_PAST].replace("{가상현재날짜}", today))
            continue

        schedule = {"시작날짜": start_date, "종료날짜": end_date, "요일목록": weekdays,
                    "시작교시": start_period, "종료교시": end_period}
        if not data.is_schedule(schedule):
            _print_error(errors.E_FILE_FORMAT,
                         "시작 날짜와 종료 날짜의 요일은 요일 목록에 포함되어야 합니다.")
            continue

        return start_date, end_date


CLASS_FIELD_SCREEN = """1. 반 이름
2. 담당 강사
3. 정원
0. 이전 메뉴"""


def update_class(user):
    """6.6.4.4 수정. 반 이름·담당 강사·정원만 바꿀 수 있다.

    수업 일정(요일·교시·기간)은 바꾸지 않는다. 바꾸려면 폐강한 뒤 새로 개설한다.
    """
    classes = data.read_classes()
    class_ = _ask_id("수정할 반 ID를 입력하세요", classes,
                     "반ID", "존재하지 않는 반 ID입니다. 재입력")
    if class_ is None:
        return

    if class_["반상태"] == "폐강":
        _print_error(errors.E_CLASS_CLOSED)
        return

    while True:
        print()
        print(CLASS_FIELD_SCREEN)
        choice = ui.ask_menu_choice([1, 2, 3, 0])
        if choice is None:
            continue
        if choice == 0:
            return

        try:
            if choice == 1:
                changed = _change_class_name(class_, classes)
            elif choice == 2:
                changed = _change_class_teacher(class_, classes)
            else:
                changed = _change_class_capacity(class_)
        except ui.InputCancelled:
            return

        if not changed:
            return
        if _save_one(data.write_classes, classes):
            print(f"[OK_CLASS_UPDATE] 반 {class_['반ID']}의 정보가 수정되었습니다.")
        return


def _change_class_name(class_, classes):
    """6.6.4.4 반 이름. 같은 과목 안에서 중복될 수 없다. (4.2.3)"""
    class_name = _ask_valid("새 반 이름", data.is_class_name, "반 이름")
    if _is_name_taken(classes, class_["과목ID"], class_name, except_id=class_["반ID"]):
        _print_error(errors.E_CLASS_NAME_DUPLICATE)
        return False
    class_["반이름"] = class_name
    return True


def _change_class_teacher(class_, classes):
    """6.6.4.4 담당 강사. 재직 강사여야 하고, 새 강사 기준으로 시간 충돌을 다시 본다."""
    teachers = data.read_teachers()
    teacher = _ask_teacher_in_service(teachers)

    conflicts = _conflicting_classes(class_, teacher["강사ID"], classes, except_id=class_["반ID"])
    if conflicts:
        _print_conflicts(conflicts, data.read_subjects())
        return False

    class_["강사ID"] = teacher["강사ID"]
    return True


def _change_class_capacity(class_):
    """6.6.4.4 정원. 1~99 이고, 현재 "수강중" 등록 수보다 작을 수 없다."""
    capacity = _ask_capacity("새 정원")
    enrolled = _enrolled(class_["반ID"])
    if enrolled is not None and int(capacity) < enrolled:
        _print_error(errors.E_CAPACITY_UNDER)
        return False
    class_["정원"] = capacity
    return True


def close_class(user):
    """6.6.4.5 폐강. 그 반의 "수강중" 수강 등록을 모두 취소 처리한다."""
    classes = data.read_classes()
    class_ = _ask_id("폐강할 반 ID를 입력하세요", classes,
                     "반ID", "존재하지 않는 반 ID입니다. 재입력")
    if class_ is None:
        return

    if class_["반상태"] == "폐강":
        _print_error(errors.E_CLASS_ALREADY_CLOSED)
        return

    enrollments = data.read_enrollments()
    targets = _active_enrollments(enrollments, "반ID", class_["반ID"])
    if targets:
        print(f"[W_CLASS_HAS_STUDENTS] 이 반에는 현재 수강중 수강생 {len(targets)}명이 있습니다.")
        print("폐강 시 해당 학생들의 수강 등록은 자동으로 취소 처리됩니다.")

    title = _class_title(class_, data.read_subjects())
    if not ui.ask_yes_no(f"반 {class_['반ID']}({title})을(를) 폐강"):
        return

    class_["반상태"] = "폐강"
    for enrollment in targets:
        _cancel(enrollment)

    if not targets:
        if _save_one(data.write_classes, classes):
            print(f"[OK_CLASS_CLOSE] 반 {class_['반ID']}이 폐강되었습니다.")
        return

    if _save({data.CLASSES: classes, data.ENROLLMENTS: enrollments}):
        print(f"[OK_CLASS_CLOSE] 반 {class_['반ID']}이 폐강되었습니다. "
              f"수강중 수강 등록 {len(targets)}건이 함께 취소되었습니다.")
