"""격자 기반 최대 채우기 자동배치 알고리즘.

지정한 영역(폴리곤, 제외구역 holes 포함) 안에 기구를 큰 것부터 그리드 스캔 순서로 채워 넣는다.
완전 최적해를 구하는 빈패킹이 아니라, 빠르고 예측 가능한 greedy 방식이다.
"""
from dataclasses import dataclass
from shapely.geometry import Polygon, box as shapely_box


@dataclass
class FurnitureSpec:
    furniture_type_id: int
    width_mm: float
    height_mm: float
    quantity: int
    min_spacing_mm: float = 300.0
    allow_rotation: bool = True


@dataclass
class PlacedItem:
    furniture_type_id: int
    x_mm: float
    y_mm: float
    rotation_deg: float


def _fits(polygon: Polygon, footprint: Polygon) -> bool:
    # within()은 경계가 딱 맞닿는 경우도 포함해야 하므로 covers 사용
    # holes가 있으면 구멍 내부는 polygon에 포함되지 않으므로 자동으로 제외된다.
    return polygon.covers(footprint)


def _overlaps(footprint_padded, placed_padded: list) -> bool:
    return any(footprint_padded.intersects(p) for p in placed_padded)


def grid_placement(
    area_points: list[list[float]],
    specs: list[FurnitureSpec],
    holes: list[list[list[float]]] | None = None,
) -> list[PlacedItem]:
    polygon = Polygon(shell=area_points, holes=holes or None)
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    minx, miny, maxx, maxy = polygon.bounds

    # 큰 기구부터 배치해야 남는 공간을 작은 기구가 메우기 쉬움
    ordered = sorted(specs, key=lambda s: s.width_mm * s.height_mm, reverse=True)

    placed: list[PlacedItem] = []
    placed_padded = []  # 간격 확보용으로 부풀린 footprint, 겹침 검사에 사용

    for spec in ordered:
        placed_count = 0
        orientations = [0, 90] if spec.allow_rotation else [0]
        step = max(50.0, min(spec.width_mm, spec.height_mm) / 2)

        y = miny
        while y <= maxy and placed_count < spec.quantity:
            x = minx
            while x <= maxx and placed_count < spec.quantity:
                for angle in orientations:
                    w, h = (spec.height_mm, spec.width_mm) if angle == 90 else (spec.width_mm, spec.height_mm)
                    cx, cy = x + w / 2, y + h / 2
                    footprint = shapely_box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

                    if not _fits(polygon, footprint):
                        continue

                    pad = spec.min_spacing_mm / 2
                    footprint_padded = shapely_box(
                        cx - w / 2 - pad, cy - h / 2 - pad, cx + w / 2 + pad, cy + h / 2 + pad
                    )
                    if _overlaps(footprint_padded, placed_padded):
                        continue

                    placed.append(PlacedItem(spec.furniture_type_id, cx, cy, float(angle)))
                    placed_padded.append(footprint_padded)
                    placed_count += 1
                    break
                x += step
            y += step

    return placed
