import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import projects, drawings, areas, furniture, placement

app = FastAPI(title="도면 배치 자동화")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(projects.router)
app.include_router(drawings.router)
app.include_router(areas.router)
app.include_router(furniture.router)
app.include_router(placement.router)


@app.get("/health")
def health():
    return {"status": "ok"}


def _frontend_dist_dir() -> str:
    """빌드된 프론트엔드 정적 파일 위치. exe로 묶였을 때는 PyInstaller가 풀어놓은 임시 폴더 안,
    개발 중에는 frontend/dist. 둘 다 없으면(=Docker+Vite dev 환경) 정적 서빙을 하지 않는다."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "static")
    return os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")


_dist_dir = _frontend_dist_dir()
if os.path.isdir(_dist_dir):
    app.mount("/", StaticFiles(directory=_dist_dir, html=True), name="frontend")
