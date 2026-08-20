from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import PlacementArea

router = APIRouter(prefix="/projects/{project_id}/areas", tags=["areas"])


@router.get("", response_model=list[PlacementArea])
def list_areas(project_id: int, session: Session = Depends(get_session)):
    return session.exec(select(PlacementArea).where(PlacementArea.project_id == project_id)).all()


@router.post("", response_model=PlacementArea)
def create_area(project_id: int, area: PlacementArea, session: Session = Depends(get_session)):
    if len(area.points) < 3:
        raise HTTPException(400, "영역은 최소 3개의 점으로 이루어진 폴리곤이어야 합니다")
    area.id = None
    area.project_id = project_id
    session.add(area)
    session.commit()
    session.refresh(area)
    return area


@router.put("/{area_id}", response_model=PlacementArea)
def update_area(project_id: int, area_id: int, area: PlacementArea, session: Session = Depends(get_session)):
    existing = session.get(PlacementArea, area_id)
    if not existing or existing.project_id != project_id:
        raise HTTPException(404, "영역을 찾을 수 없습니다")
    existing.points = area.points
    existing.holes = area.holes
    existing.name = area.name
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


@router.delete("/{area_id}")
def delete_area(project_id: int, area_id: int, session: Session = Depends(get_session)):
    existing = session.get(PlacementArea, area_id)
    if not existing or existing.project_id != project_id:
        raise HTTPException(404, "영역을 찾을 수 없습니다")
    session.delete(existing)
    session.commit()
    return {"ok": True}
