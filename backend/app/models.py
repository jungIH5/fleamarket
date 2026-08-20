from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, JSON, Column


class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Drawing(SQLModel, table=True):
    """업로드된 원본 도면 파일 (DXF/DWG/PDF/이미지)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    filename: str
    file_type: str  # "dxf" | "dwg" | "pdf" | "image"
    storage_path: str
    # 자동 인식 실패 시 백그라운드 이미지로만 쓰기 위한 래스터 미리보기 경로
    preview_image_path: Optional[str] = None
    # PDF/이미지는 실제 축척 정보가 없으므로 사용자가 기준선을 긋고 실제 길이(mm)를 입력해 보정한다.
    # DXF/DWG는 도면 좌표가 곧 실치수(mm 가정)라 기본값 1.0을 사용한다.
    scale_mm_per_unit: float = 1.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlacementArea(SQLModel, table=True):
    """배치 가능 영역 폴리곤. 자동 인식 결과 또는 사용자가 직접 수정한 좌표."""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    drawing_id: Optional[int] = Field(default=None, foreign_key="drawing.id")
    name: str = "배치 영역"
    # [[x_mm, y_mm], ...] 폴리곤 꼭짓점, 도면 좌표계 기준
    points: list = Field(sa_column=Column(JSON))
    # 제외구역(데드존) 목록. 각 항목은 points와 같은 형식의 폴리곤.
    # 기둥/동선/기존 구조물처럼 기구를 배치하면 안 되는 내부 구멍을 표현한다.
    # 외곽만 둘러 배치(도넛형)하려면 안쪽 전체를 덮는 제외구역 하나를 넣으면 된다.
    holes: list = Field(default_factory=list, sa_column=Column(JSON))
    source: str = "manual"  # "auto" | "manual"


class FurnitureType(SQLModel, table=True):
    """기구 카탈로그 항목. 프로젝트별로 사용자가 자유롭게 추가."""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    name: str  # 예: "테이블 1500", "파라솔"
    width_mm: float
    height_mm: float
    shape: str = "rect"  # "rect" | "circle"
    color: str = "#4a90d9"


class PlacementRule(SQLModel, table=True):
    """자동배치 조건: 어느 영역에 어떤 기구를 몇 개, 어떤 간격으로."""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    area_id: int = Field(foreign_key="placementarea.id")
    furniture_type_id: int = Field(foreign_key="furnituretype.id")
    quantity: int
    min_spacing_mm: float = 300.0
    allow_rotation: bool = True


class PlacementItem(SQLModel, table=True):
    """실제 배치된 기구 인스턴스 좌표 (자동배치 결과 + 수동 미세조정 반영)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id")
    area_id: int = Field(foreign_key="placementarea.id")
    furniture_type_id: int = Field(foreign_key="furnituretype.id")
    x_mm: float
    y_mm: float
    rotation_deg: float = 0.0
    # 이 자리만의 특기사항 자유 메모. 예: "전기 많이 씀", "테이블 대신 행거", "아이스크림 기계 있음".
    # 판매자 개별 DB를 따로 두지 않고, 필요한 자리에만 가볍게 표시하기 위한 용도.
    notes: Optional[str] = None
    # "auto": 자동배치가 생성/관리. "manual": 사람이 직접 추가했거나 손댄 자리 - 자동배치 재실행 시
    # 지우지 않고 그대로 유지하며, 오히려 새 자동배치가 이 자리를 피해가도록 장애물로 취급한다.
    source: str = "auto"
