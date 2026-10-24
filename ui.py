"""공통 입력 — 담당 1

메뉴 번호, 확인(Y/N), 필수 값 입력처럼 모든 메뉴가 똑같이 쓰는 입력을 모았다.
기획서 6.1.2, 6.1.3, 6.1.5 를 구현한다.

다른 파일에서는 이렇게 부른다.

    import ui
    if not ui.ask_yes_no("반 C0001(수학 A반)을 폐강"):
        return

이 파일은 errors.py 만 import 한다.
"""

import errors
import getpass
import re


class InputCancelled(errors.OperationCancelled):
    """여러 값을 입력받는 도중 /cancel 이 들어왔을 때 던진다. (6.1.5)

    받는 쪽은 입력한 값을 전부 버리고 파일을 바꾸지 않은 채
    상위 메뉴로 돌아간다.

        try:
            name = ui.ask_required("이름")
            phone = ui.ask_required("연락처")
        except ui.InputCancelled:
            return
    """


def ask_menu_choice(valid):
    """메뉴 번호 하나를 입력받는다. (6.1.2)

    valid  화면에 보이는 번호 목록. 예) [1, 2, 3, 4, 5, 6, 7, 9, 0]

    프롬프트는 "번호를 입력하세요: " 이다. (6.1.1)
    앞뒤 표준공백(스페이스)은 떼고 본다. (5.3) 탭은 떼지 않는다.
    번호 하나만 허용한다. 01, +1, 1.0, 1,2, 빈 입력은 모두 잘못된 입력이다.

    올바르면 그 번호를 int 로 돌려준다.
    잘못되면 [E_MENU_CHOICE] 메시지를 출력하고 None 을 돌려준다.
    None 을 받은 쪽은 같은 메뉴를 다시 출력하고 다시 묻는다.
    """
    # strip() 은 탭·전각 공백까지 떼므로 표준공백 " " 만 지정한다. (5.3, 1장 "표준공백")
    text = input("번호를 입력하세요: ").strip(" ")

    # int(text) 로 바꿔 비교하지 않고, 화면 번호를 글자로 바꿔 통째로 비교한다.
    # int() 는 "01", "+1", " 1", "５" 를 전부 1 로 받아들이지만,
    # "1" == "01" 은 거짓이라 6.1.2 가 막으라는 입력이 저절로 걸러진다.
    for number in valid:
        if text == str(number):
            return number

    print(f"[{errors.E_MENU_CHOICE}] {errors.ERROR_MESSAGES[errors.E_MENU_CHOICE]}")
    return None


def ask_yes_no(action, cancel_message="작업을 취소했습니다. 변경된 내용이 없습니다."):
    """결과가 중요한 작업 직전에 확인을 받는다. (6.1.3)

    action          작업 설명. 예) "반 C0001(수학 A반)을 폐강"
    cancel_message  N 일 때 출력할 문장. 보통은 그대로 둔다.
                    6.3 가상 일시 변경은 문장이 달라서 이렇게 넘긴다.
                    "작업을 취소했습니다. 가상 현재 일시가 변경되지 않았습니다."

    "{action}하시겠습니까? (Y/N, 기본값 N): " 로 묻는다.
    Y 또는 y 면 True 를 돌려준다.
    그 밖의 모든 입력(Enter 만 친 것 포함)은 N 으로 보고
    cancel_message 를 출력한 뒤 False 를 돌려준다.

    취소 메시지는 이 함수가 출력한다. 부르는 쪽에서 또 출력하지 않는다.
    """
    answer = input(f"{action}하시겠습니까? (Y/N, 기본값 N): ").strip(" ")
    if answer in ("Y", "y"):
        return True
    print(cancel_message)
    return False


def ask_required(label, strip=True):
    """빈 값을 허용하지 않는 항목을 입력받는다. (6.1.5)

    label  항목 이름. 예) "이름"
    strip  앞뒤 표준공백(스페이스)을 뗄지. (5.3)
           비밀번호는 "앞뒤 표준공백을 제거하지 않고 입력값 그대로 검사"하므로 False 로 부른다.
           탭은 떼지 않는다. 탭이 들어 있으면 부르는 쪽의 형식 검사에서 걸린다.

    빈 입력이면 "[E_INPUT_EMPTY] 필수 값을 입력하세요." 를 출력하고 다시 받는다.
    /cancel 이 들어오면 InputCancelled 를 던진다.
    그 밖에는 입력한 문자열을 돌려준다. 형식 검사는 부르는 쪽이 data.is_* 로 한다.

    로그인(6.2.1)에는 쓰지 않는다. 로그인은 "0 이면 6.7.1 종료 절차 → 빈 입력 → 형식 → 계정 확인"
    순서가 따로 정해져 있고, 비밀번호는 getpass 로 받으며, /cancel 이 없다.
    """
    while True:
        text = (getpass.getpass(f"{label}: ") if not strip and "비밀번호" in label
                else input(f"{label}: "))
        if strip:
            text = text.strip(" ")
        if text == "/cancel":
            raise InputCancelled()
        if text == "":
            print(f"[{errors.E_INPUT_EMPTY}] {errors.ERROR_MESSAGES[errors.E_INPUT_EMPTY]}")
            continue
        return text


def ask_target(label):
    """빈 입력은 이전 메뉴. 내부 식별자는 ASCII 접두사+4자리로 검사한다."""
    prefixes = {"반 ID": "C", "학생 ID": "S", "강사 ID": "T", "과목 ID": "P", "등록 ID": "E"}
    prefix = next((value for key, value in prefixes.items() if key in label), None)
    while True:
        value = input(f"{label}: ").strip(" ")
        if value == "":
            return None
        if value == "/cancel":
            raise InputCancelled()
        if value == "0" or prefix is None:
            return value
        if re.fullmatch(prefix + r"[0-9]{4}", value) and value[1:] != "0000":
            return value
        print(f"[{errors.E_FILE_FORMAT}] ID 형식이 올바르지 않습니다.")





def wait_for_back():
    """조회 화면에서 유효한 0을 입력할 때까지 기다린다."""
    while True:
        print("0. 이전 메뉴")
        if ask_menu_choice([0]) == 0:
            return
