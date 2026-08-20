from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import FurnitureType

router = APIRouter(prefix="/projects/{project_id}/furniture", tags=["furniture"])


@router.get("", response_model=list[FurnitureType])
def list_furniture(project_id: int, session: Session = Depends(get_session)):
    return session.exec(select(FurnitureType).where(FurnitureType.project_id == project_id)).all()


@router.post("", response_model=FurnitureType)
def create_furniture(project_id: int, item: FurnitureType, session: Session = Depends(get_session)):
    item.id = None
    item.project_id = project_id
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/{furniture_id}", response_model=FurnitureType)
def update_furniture(
    project_id: int, furniture_id: int, item: FurnitureType, session: Session = Depends(get_session)
):
    existing = session.get(FurnitureType, furniture_id)
    if not existing or existing.project_id != project_id:
        raise HTTPException(404, "기구를 찾을 수 없습니다")
    existing.name = item.name
    existing.width_mm = item.width_mm
    existing.height_mm = item.height_mm
    existing.shape = item.shape
    existing.color = item.color
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


@router.delete("/{furniture_id}")
def delete_furniture(project_id: int, furniture_id: int, session: Session = Depends(get_session)):
    existing = session.get(FurnitureType, furniture_id)
    if not existing or existing.project_id != project_id:
        raise HTTPException(404, "기구를 찾을 수 없습니다")
    session.delete(existing)
    session.commit()
    return {"ok": True}
