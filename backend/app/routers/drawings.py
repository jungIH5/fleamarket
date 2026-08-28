import os
import shutil
import subprocess
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from ..database import get_session
from ..models import Drawing
from ..parsers.dxf_parser import parse_dxf
from ..parsers.raster_parser import parse_raster, pdf_to_image
from ..paths import get_app_dir

router = APIRouter(prefix="/projects/{project_id}/drawings", tags=["drawings"])

UPLOAD_DIR = os.path.join(get_app_dir(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXT_TO_TYPE = {
    ".dxf": "dxf",
    ".dwg": "dwg",
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}

# DWG -> DXF 변환에 사용할 ODA File Converter 실행 파일 경로.
# DWG는 오토데스크 독점 포맷이라 오픈소스로 직접 파싱할 수 없어, 설치되어 있으면 이 변환기를 거쳐 DXF로 바꾼 뒤 동일 파이프라인을 재사용한다.
ODA_CONVERTER_PATH = os.environ.get("ODA_CONVERTER_PATH")


def _convert_dwg_to_dxf(dwg_path: str) -> str:
    if not ODA_CONVERTER_PATH:
        raise HTTPException(
            422,
            "DWG 파일은 자동 변환기가 설정되어 있지 않아 처리할 수 없습니다. "
            "ODA File Converter를 설치하고 ODA_CONVERTER_PATH 환경변수를 설정하거나, "
            "파일을 DXF로 변환해서 다시 업로드해 주세요.",
        )
    out_dir = os.path.dirname(dwg_path)
    subprocess.run(
        [ODA_CONVERTER_PATH, out_dir, out_dir, "ACAD2018", "DXF", "0", "1", os.path.basename(dwg_path)],
        check=True,
        timeout=60,
    )
    dxf_path = os.path.splitext(dwg_path)[0] + ".dxf"
    if not os.path.exists(dxf_path):
        raise HTTPException(500, "DWG -> DXF 변환에 실패했습니다.")
    return dxf_path


@router.post("")
def upload_drawing(project_id: int, file: UploadFile = File(...), session: Session = Depends(get_session)):
    ext = os.path.splitext(file.filename)[1].lower()
    file_type = EXT_TO_TYPE.get(ext)
    if not file_type:
        raise HTTPException(400, f"지원하지 않는 파일 형식입니다: {ext}")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    parse_result = None
    preview_image_path = None

    try:
        if file_type == "dxf":
            parse_result = parse_dxf(stored_path)
        elif file_type == "dwg":
            dxf_path = _convert_dwg_to_dxf(stored_path)
            parse_result = parse_dxf(dxf_path)
        elif file_type == "pdf":
            preview_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}.png")
            pdf_to_image(stored_path, preview_path)
            preview_image_path = preview_path
            parse_result = parse_raster(preview_path)
        elif file_type == "image":
            preview_image_path = stored_path
            parse_result = parse_raster(stored_path)
    except HTTPException:
        raise
    except Exception as e:
        # 자동 인식이 실패해도 업로드 자체는 성공시키고, 사용자가 직접 폴리곤을 그릴 수 있게 빈 결과를 반환
        parse_result = {"segments": [], "candidate_areas": [], "bounds": [0, 0, 0, 0], "error": str(e)}

    drawing = Drawing(
        project_id=project_id,
        filename=file.filename,
        file_type=file_type,
        storage_path=stored_path,
        preview_image_path=preview_image_path,
    )
    session.add(drawing)
    session.commit()
    session.refresh(drawing)

    return {"drawing": drawing, "parse_result": parse_result}


@router.get("", response_model=list[Drawing])
def list_drawings(project_id: int, session: Session = Depends(get_session)):
    return session.exec(select(Drawing).where(Drawing.project_id == project_id)).all()


@router.get("/{drawing_id}/file")
def get_drawing_file(project_id: int, drawing_id: int, session: Session = Depends(get_session)):
    drawing = session.get(Drawing, drawing_id)
    if not drawing or drawing.project_id != project_id:
        raise HTTPException(404, "도면을 찾을 수 없습니다")
    path = drawing.preview_image_path or drawing.storage_path
    return FileResponse(path)


@router.put("/{drawing_id}/scale")
def set_drawing_scale(
    project_id: int, drawing_id: int, scale_mm_per_unit: float, session: Session = Depends(get_session)
):
    """PDF/이미지 업로드 후, 사용자가 기준선을 긋고 실제 길이를 입력하면
    scale_mm_per_unit = 실제_길이_mm / 화면에서_그은_선의_픽셀_길이 로 계산해 전달한다."""
    drawing = session.get(Drawing, drawing_id)
    if not drawing or drawing.project_id != project_id:
        raise HTTPException(404, "도면을 찾을 수 없습니다")
    drawing.scale_mm_per_unit = scale_mm_per_unit
    session.add(drawing)
    session.commit()
    session.refresh(drawing)
    return drawing
