"""PDF/이미지에서 벽선과 배치 영역 후보를 best-effort로 추정한다.

벡터 정보가 없는 래스터 입력이므로 결과는 참고용이며, 프론트엔드에서
사용자가 반드시 폴리곤을 눈으로 확인하고 보정해야 한다. 또한 이미지에는
실제 축척이 없으므로 Drawing.scale_mm_per_unit 보정 없이는 좌표 단위가
'픽셀'일 뿐 mm가 아니다.
"""
import cv2
import numpy as np
from pdf2image import convert_from_path


def pdf_to_image(pdf_path: str, out_png_path: str, dpi: int = 150) -> str:
    """PDF 첫 페이지를 PNG로 변환한다 (poppler 설치 필요, 컨테이너에는 이미 포함됨)."""
    pages = convert_from_path(pdf_path, dpi=dpi)
    pages[0].save(out_png_path, "PNG")
    return out_png_path


def parse_raster(image_path: str, min_area_px: float = 5000) -> dict:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"이미지를 읽을 수 없습니다: {image_path}")
    h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    # 배경 렌더링 참고용 직선 검출
    segments = []
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=40, maxLineGap=10)
    if lines is not None:
        # OpenCV 3/4는 (N,1,4), OpenCV 5는 (N,4)를 반환해 버전에 따라 모양이 다르므로 통일한다.
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            segments.append([[float(x1), float(y1)], [float(x2), float(y2)]])

    # 닫힌 영역(방/구역) 후보 = 윤곽선 중 면적이 큰 것들
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    candidate_areas = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area_px:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.01 * peri, True)
        if len(approx) < 3:
            continue
        points = [[float(p[0][0]), float(p[0][1])] for p in approx]
        candidate_areas.append({"points": points, "area": float(area), "fallback": False})

    candidate_areas.sort(key=lambda c: c["area"], reverse=True)
    candidate_areas = candidate_areas[:10]

    if not candidate_areas:
        # 아무 것도 못 찾으면 이미지 전체를 단일 후보로 제공 (사용자가 직접 보정)
        candidate_areas.append({
            "points": [[0.0, 0.0], [float(w), 0.0], [float(w), float(h)], [0.0, float(h)]],
            "area": float(w * h),
            "fallback": True,
        })

    return {
        "segments": segments,
        "candidate_areas": candidate_areas,
        "bounds": [0.0, 0.0, float(w), float(h)],
        "image_size": [w, h],
    }
