"""오류 코드와 오류 메시지 — 담당 5

기획서에 적힌 오류 코드 27개와, 문장까지 정해진 메시지 22개를 그대로 옮겼다.
새로 지어내지 않는다. 다른 파일에서는 문자열을 직접 치지 말고 이 상수를 쓴다.

    import errors
    print(f"[{errors.E_AUTH_FAIL}] {errors.ERROR_MESSAGES[errors.E_AUTH_FAIL]}")

이 파일은 다른 파일을 import 하지 않는다. 맨 아래층이다.
"""


# 5.4 무결성 검사 ①~⑧ — 전부 즉시 종료
E_FILE_MISSING     = "E_FILE_MISSING"       # ①   파일이 없다
E_FILE_READ        = "E_FILE_READ"          # ①   읽을 수 없다 (권한 등)
E_FILE_FORMAT      = "E_FILE_FORMAT"        # ②③④ 인코딩·필드 수·빈 줄·값 형식 위반
E_DUP_ID           = "E_DUP_ID"             # ⑤   식별자 중복
E_REF_MISSING      = "E_REF_MISSING"        # ⑥   참조 대상이 없다
E_TEACHER_CONFLICT = "E_TEACHER_CONFLICT"   # ⑦   강사 수업 시간 충돌
E_STUDENT_CONFLICT = "E_STUDENT_CONFLICT"   # ⑦   학생 수업 시간 충돌
E_CLASS_FULL       = "E_CLASS_FULL"         # ⑦   정원 초과
E_TIME_BACKWARD    = "E_TIME_BACKWARD"      # ⑧   가상 현재 일시 역행

# 입력 · 로그인 · 권한
E_MENU_CHOICE   = "E_MENU_CHOICE"
E_INPUT_EMPTY   = "E_INPUT_EMPTY"
E_AUTH_FAIL     = "E_AUTH_FAIL"
E_NO_PERMISSION = "E_NO_PERMISSION"
E_ROLE_INVALID  = "E_ROLE_INVALID"

# 저장
E_SAVE            = "E_SAVE"
E_CONCURRENT_EDIT = "E_CONCURRENT_EDIT"

# 반 · 수강 등록
E_CLASS_CLOSED             = "E_CLASS_CLOSED"
E_CLASS_ALREADY_CLOSED     = "E_CLASS_ALREADY_CLOSED"
E_CLASS_NAME_DUPLICATE     = "E_CLASS_NAME_DUPLICATE"
E_CAPACITY_UNDER           = "E_CAPACITY_UNDER"
E_DATE_PAST                = "E_DATE_PAST"
E_TEACHER_RETIRED          = "E_TEACHER_RETIRED"
E_ALREADY_ENROLLED         = "E_ALREADY_ENROLLED"
E_ENROLL_ALREADY_CANCELLED = "E_ENROLL_ALREADY_CANCELLED"

# 삭제 제약
E_STUDENT_HAS_HISTORY = "E_STUDENT_HAS_HISTORY"
E_SUBJECT_IN_USE      = "E_SUBJECT_IN_USE"
E_TEACHER_IN_USE      = "E_TEACHER_IN_USE"


# 기획서에 메시지 문장까지 정해져 있는 것들.
# 7.1.1 기능 테스트는 화면에 나온 문장을 보고 판정하므로
# 문장을 고쳐 쓰지 말고 이 표를 그대로 쓴다.
#
#     print(f"[{errors.E_AUTH_FAIL}] {errors.ERROR_MESSAGES[errors.E_AUTH_FAIL]}")
#
# 여기 없는 코드(E_FILE_FORMAT, E_REF_MISSING, E_FILE_MISSING,
# E_FILE_READ, E_TIME_BACKWARD)는 상황마다 문장이 달라서
# 기획서의 해당 절에 적힌 문장을 그때그때 쓴다.
# E_DUP_ID, E_CLASS_FULL, E_STUDENT_CONFLICT, E_TEACHER_CONFLICT 는
# 무결성 검사(5.4 ⑤⑦)에서도 쓰인다. 위 문장은 메뉴에서 작업할 때의 문장이고,
# 무결성 검사에서는 "students.txt 3행: ..." 처럼 파일과 행 번호를 붙인 문장을 쓴다. (6.7.4)
ERROR_MESSAGES = {
    E_MENU_CHOICE:    "잘못된 입력입니다. 화면에 표시된 번호 중 하나만 입력하세요.",
    E_INPUT_EMPTY:    "필수 값을 입력하세요.",
    E_AUTH_FAIL:      "로그인 정보가 올바르지 않습니다.",
    E_NO_PERMISSION:  "해당 반의 수강생 정보를 조회할 권한이 없습니다.",
    E_ROLE_INVALID:   "학생 또는 강사 계정만 초기화할 수 있습니다.",
    E_DUP_ID:         "이미 존재하는 사용자 ID입니다.",

    E_SAVE:           "저장하지 못했습니다.",
    # 6.3 가상 현재 일시 변경 실패 때만 뒤에 한 문장이 더 붙는다
    #     "저장하지 못했습니다. 가상 현재 일시는 변경되지 않았습니다."
    E_CONCURRENT_EDIT: "데이터 파일이 변경되었습니다. 다시 조회한 뒤 시도하세요.",

    E_CLASS_FULL:               "해당 반의 정원이 가득 찼습니다. 수강 신청할 수 없습니다.",
    E_STUDENT_CONFLICT:         "기존 수강 반과 수업 시간이 겹칩니다.",
    E_TEACHER_CONFLICT:         "담당 강사의 다음 반과 수업 시간이 충돌합니다:",  # 뒤에 반 목록
    E_CLASS_CLOSED:             "폐강된 반은 수정할 수 없습니다.",
    E_CLASS_ALREADY_CLOSED:     "이미 폐강된 반입니다.",
    E_CLASS_NAME_DUPLICATE:     "같은 과목에 같은 이름의 반이 이미 있습니다.",
    E_CAPACITY_UNDER:           "새 정원은 현재 수강중 학생 등록 수보다 작을 수 없습니다.",
    E_TEACHER_RETIRED:          "퇴직 상태의 강사는 새 반에 배정할 수 없습니다.",
    E_ALREADY_ENROLLED:         "이미 수강 중인 반입니다.",
    E_ENROLL_ALREADY_CANCELLED: "이미 취소된 수강 등록입니다.",

    E_STUDENT_HAS_HISTORY: "이 학생에게는 수강 등록 이력이 있어 삭제할 수 없습니다.",
    E_SUBJECT_IN_USE:      "이 과목을 참조하는 반이 있어 삭제할 수 없습니다.",
    E_TEACHER_IN_USE:      "이 강사를 참조하는 반이 있어 삭제할 수 없습니다.",

    # {가상현재날짜} 를 실제 값으로 바꿔 넣는다
    E_DATE_PAST: "시작 날짜는 현재 날짜({가상현재날짜}) 이후여야 합니다.",
}


class DataError(Exception):
    """데이터 파일이 규칙을 어겼을 때 던진다.

    받는 쪽:
        try:
            users = data.read_users()
        except errors.DataError as e:
            print(e.code)      # "E_FILE_FORMAT"
            print(e.message)   # "users.txt 3행: 필드 수가 3개가 아니라 2개입니다"
    """

    def __init__(self, code, message, stage=None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        # 5.4 무결성 검사 몇 단계(1~8)에서 나온 오류인지.
        # 6.6.6 화면이 "[3/8] ... FAIL" 처럼 단계별로 출력하므로 필요하다.
        self.stage = stage
