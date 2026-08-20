from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
