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
