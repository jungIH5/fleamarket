import os
import sys


def get_app_dir() -> str:
    """DB 파일과 업로드 폴더를 둘 곳을 결정한다.

    PyInstaller로 exe 하나로 묶으면 코드는 실행마다 임시 폴더에 풀렸다가 종료 시 삭제되므로,
    __file__ 기준 상대경로를 쓰면 업로드/DB가 매번 사라진다. 그래서 exe로 실행 중(frozen)일 때는
    실행 파일이 있는 폴더를, 개발 중에는 backend/ 폴더를 데이터 저장 위치로 쓴다.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
