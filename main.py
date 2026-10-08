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

import data
import errors
import ui

import admin
import enrollment
import virtual_time


def first_run():          pass  # 2.3.1  data.create_data_dir → 원장 계정 → data.write_datetime → 무결성 검사
def login():              pass  # 6.2    성공하면 users.txt 레코드. 연속 5회 실패면 종료 (6.2.3)
def admin_menu(user):     pass  # 6.6    원장 메뉴 1~8, 9 로그아웃, 0 종료 (6.1.1 에는 8 이 빠져 있음)
def teacher_menu(user):   pass  # 6.1.1  강사 메뉴
def student_menu(user):   pass  # 6.1.1  학생 메뉴
def confirm_exit():       pass  # 6.1.4  "프로그램을 종료하시겠습니까?" Y 면 True


# 종료 코드 (6.7.5) — 정상 종료(6.7.1)는 0, 나머지(6.7.2~6.7.4)는 1 로 sys.exit 한다.
# 6.7.3 — Ctrl+C·EOF 는 main() 에서 KeyboardInterrupt, EOFError 를 한 번에 받아
#         "입력이 중단되었습니다. 저장되지 않은 변경 사항 없이 프로그램을 종료합니다." 출력 후 종료.
# 시작할 때 data.cleanup_tmp() 로 남은 임시 파일을 지운다. (6.7.3)


def main():
    pass


if __name__ == "__main__":
    main()
