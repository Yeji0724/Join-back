from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import File, Folder
import zipfile
import urllib.parse
import io
import os

router = APIRouter(prefix="/folders", tags=["download"])

# ------------------------------
# 전체 다운로드
# ------------------------------
@router.get("/download/{folder_id}")
def download_folder(folder_id: int, db: Session = Depends(get_db)):

    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    files = db.query(File).filter(File.folder_id == folder_id).all()
    if not files:
        raise HTTPException(status_code=404, detail="폴더 안에 파일이 존재하지 않습니다.")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            if file.file_path and os.path.exists(file.file_path):
                # 카테고리 이름을 포함해 ZIP 안에서 폴더 구조를 만듦
                if file.category:
                    arcname = os.path.join(file.category, file.file_name)
                else:
                    arcname = os.path.join("분류되지 않은 문서", file.file_name)
                zip_file.write(file.file_path, arcname=arcname)
            else:
                print(f"⚠ 전체 다운로드 실패 : {file.file_path}")

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(folder.folder_name + '.zip')}"
        }
    )
# ------------------------------
# 카테고리 다운로드
# ------------------------------

@router.get("/download/category/{folder_id}/{category_name}")
def download_category(folder_id: int, category_name: str, db: Session = Depends(get_db)):
    # 1. 폴더 존재 여부 확인
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="폴더가 존재하지 않습니다.")

    # 2. 해당 카테고리 파일 조회
    files = db.query(File).filter(
        File.folder_id == folder_id,
        File.category == category_name
    ).all()
    if not files:
        raise HTTPException(status_code=404, detail="카테고리에 파일이 존재 하지 않습니다.")

    # 3. ZIP 생성
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file in files:
            if file.file_path and os.path.exists(file.file_path):
                zip_file.write(file.file_path, arcname=file.file_name)
            else:
                print(f"⚠ 카테고리 다운로드 실패 : {file.file_path}")

    zip_buffer.seek(0)
    return StreamingResponse(
    zip_buffer,
    media_type="application/x-zip-compressed",
    headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(category_name + '.zip')}"
    }
)

# ------------------------------
# 개별 파일 다운로드
# ------------------------------

@router.get("/download/file/{file_id}")
def download_file(file_id: int, db: Session = Depends(get_db)):
    file = db.query(File).filter(File.file_id == file_id).first()
    if not file or not file.file_path or not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    # 파일명 한글 깨짐 방지
    encoded_name = urllib.parse.quote(file.file_name.encode("utf-8"))

    return FileResponse(
        path=file.file_path,
        filename=file.file_name,  # 실제 다운로드 시 표시될 이름
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"
        }
)
