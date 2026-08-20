from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Project, FurnitureType

router = APIRouter(prefix="/projects", tags=["projects"])

DEFAULT_FURNITURE = [
    {"name": "테이블 1500", "width_mm": 1500, "height_mm": 1500, "shape": "circle", "color": "#4a90d9"},
    {"name": "테이블 1800", "width_mm": 1800, "height_mm": 1800, "shape": "circle", "color": "#4a90d9"},
    {"name": "파라솔", "width_mm": 2500, "height_mm": 2500, "shape": "circle", "color": "#e8a33d"},
]


@router.get("", response_model=list[Project])
def list_projects(session: Session = Depends(get_session)):
    return session.exec(select(Project)).all()


@router.post("", response_model=Project)
def create_project(project: Project, session: Session = Depends(get_session)):
    project.id = None
    session.add(project)
    session.commit()
    session.refresh(project)

    for preset in DEFAULT_FURNITURE:
        session.add(FurnitureType(project_id=project.id, **preset))
    session.commit()
    session.refresh(project)

    return project


@router.get("/{project_id}", response_model=Project)
def get_project(project_id: int, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "프로젝트를 찾을 수 없습니다")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, session: Session = Depends(get_session)):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "프로젝트를 찾을 수 없습니다")
    session.delete(project)
    session.commit()
    return {"ok": True}
