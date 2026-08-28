"""exe로 패키징되는 진입점. 로컬에서 서버를 띄우고 기본 브라우저를 자동으로 연다.

PyInstaller 빌드 예:
  pyinstaller --onefile --name FleaMarketLayout ^
    --add-data "..\\frontend\\dist;static" ^
    run_desktop.py
"""
import threading
import time
import webbrowser

import uvicorn

from app.main import app

HOST = "127.0.0.1"
PORT = 8000


def _open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
