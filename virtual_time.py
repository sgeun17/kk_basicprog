"""가상 현재 일시 조회·변경 — 담당 5

기획서 6.3 을 구현한다.

이 파일은 data.py, ui.py, errors.py 만 import 한다.
    읽기      data.now()
    바꾸기    data.append_datetime(new_dt)
    역행 판정  data.is_backward(new_dt)

메뉴에 연결되는 함수는 로그인한 사용자 레코드를 인자로 받는다.
    def change_virtual_time(user): ...
"""

import data
import errors
import ui


# ---- 5번 담당: 기획서 6.3 가상 현재 일시 조회·변경 ----

def _snapshot_files():
    """변경 작업 중 외부 파일 편집 여부를 확인하기 위한 원본 바이트."""
    try:
        return {path: path.read_bytes() for path in [*data.HEADERS, data.DATETIME]}
    except OSError as exc:
        raise errors.DataError(errors.E_FILE_READ, "데이터 파일을 읽을 수 없습니다.", 1) from exc


def _require_valid_files():
    problems = data.check_integrity()
    if problems:
        first = problems[0]
        raise errors.DataError(first.code, "\n".join(e.message for e in problems), first.stage)


@data.operation("원장")
def change_virtual_time(user):
    """원장 메뉴 6번. 원본 main.py의 기존 연결 이름을 그대로 사용한다."""
    if user.get("사용자역할") != "원장":
        print(f"[{errors.E_NO_PERMISSION}] 가상 현재 일시는 원장만 변경할 수 있습니다.")
        return
    _require_valid_files()
    before = _snapshot_files()
    current = data.now()
    print(f"현재 가상 일시: {current}")
    try:
        while True:
            value = ui.ask_required("새 가상 일시를 입력하세요 (형식: YYYY-MM-DD HH:MM)")
            if not data.is_datetime(value):
                print(f"[{errors.E_FILE_FORMAT}] 일시 형식이 올바르지 않습니다. 예: 2026-09-27 15:30")
                continue
            limit = data.backward_limit()
            if value < limit:
                print(f"[{errors.E_TIME_BACKWARD}] 새 가상 일시는 역행 판정 기준 일시({limit})보다 이전일 수 없습니다.")
                continue
            break
    except ui.InputCancelled:
        print("작업을 취소했습니다. 가상 현재 일시가 변경되지 않았습니다.")
        return
    if not ui.ask_yes_no(f"가상 현재 일시를 {current} → {value}(으)로 변경",
                         "작업을 취소했습니다. 가상 현재 일시가 변경되지 않았습니다."):
        return
    _require_valid_files()
    if _snapshot_files() != before:
        print(f"[{errors.E_CONCURRENT_EDIT}] {errors.ERROR_MESSAGES[errors.E_CONCURRENT_EDIT]}")
        return
    if data.append_datetime(value):
        print(f"[OK_TIME] 가상 현재 일시가 {value}(으)로 변경되었습니다.")
    else:
        print(f"[{errors.E_SAVE}] 저장하지 못했습니다. 가상 현재 일시는 변경되지 않았습니다.")
