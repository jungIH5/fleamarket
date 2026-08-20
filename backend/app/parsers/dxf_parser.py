"""DXF 도면에서 벽 선분과 배치 가능 영역 후보(닫힌 폴리곤)를 추출한다.

DWG 파일은 이 파서로 직접 읽을 수 없다 (오토데스크 독점 바이너리 포맷).
DWG는 ODA File Converter 등 외부 변환기로 먼저 DXF로 변환한 뒤 이 파서를 재사용해야 한다.
"""
import math
import ezdxf
from shapely.geometry import Polygon, MultiPoint


def _arc_to_segments(center, radius, start_angle, end_angle, n=16):
    points = []
    a0, a1 = math.radians(start_angle), math.radians(end_angle)
    if a1 <= a0:
        a1 += 2 * math.pi
    for i in range(n + 1):
        a = a0 + (a1 - a0) * i / n
        points.append((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)))
    return points


def parse_dxf(path: str) -> dict:
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    segments: list[list[tuple[float, float]]] = []
    candidate_areas: list[dict] = []
    all_points: list[tuple[float, float]] = []

    for e in msp:
        try:
            if e.dxftype() == "LINE":
                p1 = (e.dxf.start.x, e.dxf.start.y)
                p2 = (e.dxf.end.x, e.dxf.end.y)
                segments.append([p1, p2])
                all_points += [p1, p2]

            elif e.dxftype() == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points("xy")]
                for i in range(len(pts) - 1):
                    segments.append([pts[i], pts[i + 1]])
                all_points += pts
                if e.closed and len(pts) >= 3:
                    poly = Polygon(pts)
                    if poly.is_valid and poly.area > 0:
                        candidate_areas.append({"points": [list(p) for p in pts], "area": poly.area})

            elif e.dxftype() == "POLYLINE":
                pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
                for i in range(len(pts) - 1):
                    segments.append([pts[i], pts[i + 1]])
                all_points += pts
                if e.is_closed and len(pts) >= 3:
                    poly = Polygon(pts)
                    if poly.is_valid and poly.area > 0:
                        candidate_areas.append({"points": [list(p) for p in pts], "area": poly.area})

            elif e.dxftype() == "ARC":
                pts = _arc_to_segments(
                    (e.dxf.center.x, e.dxf.center.y), e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle
                )
                for i in range(len(pts) - 1):
                    segments.append([pts[i], pts[i + 1]])
                all_points += pts

            elif e.dxftype() == "CIRCLE":
                pts = _arc_to_segments((e.dxf.center.x, e.dxf.center.y), e.dxf.radius, 0, 360)
                for i in range(len(pts) - 1):
                    segments.append([pts[i], pts[i + 1]])
                all_points += pts
        except Exception:
            # 개별 엔티티 파싱 실패는 건너뛰고 나머지는 계속 처리
            continue

    candidate_areas.sort(key=lambda c: c["area"], reverse=True)

    # 닫힌 폴리곤이 하나도 없으면 전체 도형의 컨벡스 헐을 유일한 후보 영역으로 제안
    if not candidate_areas and len(all_points) >= 3:
        hull = MultiPoint(all_points).convex_hull
        if hull.geom_type == "Polygon":
            coords = list(hull.exterior.coords)
            candidate_areas.append({"points": [list(p) for p in coords], "area": hull.area, "fallback": True})

    if all_points:
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        bounds = [min(xs), min(ys), max(xs), max(ys)]
    else:
        bounds = [0, 0, 0, 0]

    return {
        "segments": [[list(p1), list(p2)] for p1, p2 in segments],
        "candidate_areas": candidate_areas,
        "bounds": bounds,
    }
