from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import PlacementRule, PlacementItem, PlacementArea, FurnitureType
from ..services.placement_engine import grid_placement, FurnitureSpec

router = APIRouter(prefix="/projects/{project_id}", tags=["placement"])


class PlacementItemUpdate(BaseModel):
    """드래그/회전, 기구 종류 변경, 메모 추가 등 부분 수정을 위한 스키마.
    실제로 요청에 포함된 필드만 반영한다 (PATCH와 동일한 의미)."""
    x_mm: Optional[float] = None
    y_mm: Optional[float] = None
    rotation_deg: Optional[float] = None
    furniture_type_id: Optional[int] = None
    notes: Optional[str] = None


@router.get("/rules", response_model=list[PlacementRule])
def list_rules(project_id: int, session: Session = Depends(get_session)):
    return session.exec(select(PlacementRule).where(PlacementRule.project_id == project_id)).all()


@router.post("/rules", response_model=PlacementRule)
def create_rule(project_id: int, rule: PlacementRule, session: Session = Depends(get_session)):
    rule.id = None
    rule.project_id = project_id
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}")
def delete_rule(project_id: int, rule_id: int, session: Session = Depends(get_session)):
    rule = session.get(PlacementRule, rule_id)
    if not rule or rule.project_id != project_id:
        raise HTTPException(404, "배치 조건을 찾을 수 없습니다")
    session.delete(rule)
    session.commit()
    return {"ok": True}


@router.post("/placement/run/{area_id}", response_model=list[PlacementItem])
def run_placement(project_id: int, area_id: int, session: Session = Depends(get_session)):
    area = session.get(PlacementArea, area_id)
    if not area or area.project_id != project_id:
        raise HTTPException(404, "영역을 찾을 수 없습니다")

    rules = session.exec(
        select(PlacementRule).where(
            PlacementRule.project_id == project_id, PlacementRule.area_id == area_id
        )
    ).all()
    if not rules:
        raise HTTPException(400, "이 영역에 등록된 배치 조건이 없습니다")

    specs = []
    for rule in rules:
        ftype = session.get(FurnitureType, rule.furniture_type_id)
        if not ftype:
            continue
        specs.append(
            FurnitureSpec(
                furniture_type_id=ftype.id,
                width_mm=ftype.width_mm,
                height_mm=ftype.height_mm,
                quantity=rule.quantity,
                min_spacing_mm=rule.min_spacing_mm,
                allow_rotation=rule.allow_rotation,
            )
        )

    # 사람이 직접 추가/수정한 자리(행거로 바꾼 자리, 메모를 단 자리 등)는 재실행해도 지우지 않고
    # 오히려 새 자동배치가 그 자리를 피해가도록 제외구역으로 취급한다.
    # 회전 각도가 다양할 수 있어 안전하게 정사각형(한 변 = max(가로,세로))으로 여유 있게 막는다.
    manual_items = session.exec(
        select(PlacementItem).where(
            PlacementItem.project_id == project_id,
            PlacementItem.area_id == area_id,
            PlacementItem.source == "manual",
        )
    ).all()
    obstacle_holes = []
    for mi in manual_items:
        mtype = session.get(FurnitureType, mi.furniture_type_id)
        if not mtype:
            continue
        half = max(mtype.width_mm, mtype.height_mm) / 2
        obstacle_holes.append([
            [mi.x_mm - half, mi.y_mm - half],
            [mi.x_mm + half, mi.y_mm - half],
            [mi.x_mm + half, mi.y_mm + half],
            [mi.x_mm - half, mi.y_mm + half],
        ])

    placed = grid_placement(area.points, specs, (area.holes or []) + obstacle_holes)

    # 자동 생성 자리만 지우고 새로 생성 (수동 자리는 보존)
    old_auto_items = session.exec(
        select(PlacementItem).where(
            PlacementItem.project_id == project_id,
            PlacementItem.area_id == area_id,
            PlacementItem.source == "auto",
        )
    ).all()
    for item in old_auto_items:
        session.delete(item)
    session.commit()

    new_items = []
    for p in placed:
        item = PlacementItem(
            project_id=project_id,
            area_id=area_id,
            furniture_type_id=p.furniture_type_id,
            x_mm=p.x_mm,
            y_mm=p.y_mm,
            rotation_deg=p.rotation_deg,
            source="auto",
        )
        session.add(item)
        new_items.append(item)
    session.commit()
    for item in new_items:
        session.refresh(item)
    # manual_items는 이후의 commit()들로 인해 속성이 만료되어 있으므로 반환 전 다시 채워야 한다
    for item in manual_items:
        session.refresh(item)

    return manual_items + new_items


@router.get("/placement/items", response_model=list[PlacementItem])
def list_items(project_id: int, session: Session = Depends(get_session)):
    return session.exec(select(PlacementItem).where(PlacementItem.project_id == project_id)).all()


@router.post("/placement/items", response_model=PlacementItem)
def create_item(project_id: int, item: PlacementItem, session: Session = Depends(get_session)):
    """자동배치 규칙 없이, 특정 자리 하나를 사용자가 직접 추가한다 (예: 행거, 전자기기가 들어가는 자리)."""
    area = session.get(PlacementArea, item.area_id)
    if not area or area.project_id != project_id:
        raise HTTPException(404, "영역을 찾을 수 없습니다")
    item.id = None
    item.project_id = project_id
    item.source = "manual"
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put("/placement/items/{item_id}", response_model=PlacementItem)
def update_item(
    project_id: int, item_id: int, item: PlacementItemUpdate, session: Session = Depends(get_session)
):
    """드래그/회전 미세조정, 기구 종류 변경(예: 테이블->행거), 특기사항 메모 등을 반영한다.
    사람이 한 번이라도 손댄 자리는 이후 자동배치 재실행에서 보존되도록 manual로 표시한다."""
    existing = session.get(PlacementItem, item_id)
    if not existing or existing.project_id != project_id:
        raise HTTPException(404, "배치 항목을 찾을 수 없습니다")
    for field, value in item.model_dump(exclude_unset=True).items():
        setattr(existing, field, value)
    existing.source = "manual"
    session.add(existing)
    session.commit()
    session.refresh(existing)
    return existing


@router.delete("/placement/items/{item_id}")
def delete_item(project_id: int, item_id: int, session: Session = Depends(get_session)):
    existing = session.get(PlacementItem, item_id)
    if not existing or existing.project_id != project_id:
        raise HTTPException(404, "배치 항목을 찾을 수 없습니다")
    session.delete(existing)
    session.commit()
    return {"ok": True}
