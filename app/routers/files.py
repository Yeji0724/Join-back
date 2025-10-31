# app/routers/files.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List
import os, asyncio, zipfile

from app.database import get_db
from app.models import File as FileModel, Folder, User

router = APIRouter(prefix="/files", tags=["Files"])

EXTRACTOR_SERVER_URL = "http://localhost:8001/new_file/"
SUPPORTED_EXTENSIONS = {"pdf", "hwp", "docx", "pptx", "xlsx",
                        "jpg", "jpeg", "png", "zip", "txt"}


def get_new_idx(db):
    max_id = db.query(func.max(FileModel.file_id)).scalar()
    if max_id is None:
        new_file_id = 1
    else:
        new_file_id = max_id + 1
    return new_file_id


# ------------------------------
# extractor 서버에 비동기 요청
# ------------------------------
async def notify_extractor(file_id: int, file_type: str):
    import httpx
    payload = {"files": [{"FILE_ID": file_id, "FILE_TYPE": file_type}]}
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(EXTRACTOR_SERVER_URL, json=payload)
            print(f"[Extractor 요청 전송 완료] file_id={file_id}")
        except Exception as e:
            print(f"[Extractor 요청 실패] file_id={file_id}, error={e}")


# ------------------------------
# 공통: 파일 저장 + DB 등록 + extractor 호출
# ------------------------------
async def save_file_to_db(
    user_id: int,
    folder_id: int,
    file_id: int,
    file_name: str,
    file_bytes: bytes,
    folder_dir: str,
    file_type: str,
    db: Session
) -> FileModel:
    """
    파일 저장, DB 등록, extractor 서버 호출
    - 지원되지 않는 확장자도 DB에는 기록, 파일 저장 X
    - ZIP 파일은 저장 + DB 기록, extractor 요청 제외
    """
    name, ext = os.path.splitext(file_name)
    ext = ext.lstrip(".").lower()

    # -----------------
    # DB용 중복 이름 처리 (같은 폴더 내)
    # -----------------
    existing_files = (
        db.query(FileModel)
        .filter(FileModel.folder_id == folder_id)
        .filter(FileModel.file_name.like(f"{name}%"))
        .all()
    )

    count = 0
    for f in existing_files:
        if f.file_name == f"{name}.{ext}":
            count = max(count, 1)
        elif f.file_name.startswith(f"{name}(") and f.file_name.endswith(f").{ext}"):
            try:
                n = int(f.file_name[len(name)+1:-len(ext)-2])
                count = max(count, n+1)
            except:
                continue

    if count == 0:
        display_name = f"{name}.{ext}"
    else:
        display_name = f"{name}({count}).{ext}"

    save_path = None

    # -----------------
    # 실제 저장은 지원되는 확장자만
    # -----------------
    save_filename = f"{file_id}.{ext}"
    save_path = os.path.join(folder_dir, save_filename)
    with open(save_path, "wb") as f_out:
        f_out.write(file_bytes)

    # -----------------
    # DB 저장
    # -----------------
    new_file = FileModel(
        user_id=user_id,
        folder_id=folder_id,
        file_id=file_id,
        file_name=display_name,  # DB에 표시될 제목
        file_type=ext,           # 확장자 그대로
        file_path=save_path,     # 실제 저장 경로
        is_transform=0,
        is_classification=0,
        uploaded_at=datetime.now()
    )
    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    # extractor 서버 호출 (ZIP 제외)
    if ext != "zip" and ext in SUPPORTED_EXTENSIONS:
        asyncio.create_task(notify_extractor(new_file.file_id, ext))

    return new_file



# ------------------------------
# 폴더별 파일 목록 조회 (최신순)
# ------------------------------
@router.get("/{folder_id}")
def get_folder_files(folder_id: int, db: Session = Depends(get_db)):
    update_folder_file_count(folder_id, db)     # 조회 전에 동기화
    files = (
        db.query(FileModel)
        .filter(FileModel.folder_id == folder_id)
        .order_by(FileModel.uploaded_at.desc().nullslast())
        .all()
    )

    result = [
        {
            "file_id": f.file_id,
            "user_id": f.user_id,
            "folder_id": f.folder_id,
            "file_name": f.file_name,
            "file_type": f.file_type,
            "file_path": f.file_path,
            "is_transform": f.is_transform,
            "transform_txt_path": f.transform_txt_path,
            "is_classification": f.is_classification,
            "category": f.category,
            "uploaded_at": f.uploaded_at
        }
        for f in files
    ]

    return {"files": result}


# DB 기준으로 실제 파일 수 자동으로 세고 갱신
def update_folder_file_count(folder_id: int, db: Session):
    """폴더의 실제 파일 개수를 DB에서 다시 계산해 Folder.file_cnt 갱신"""
    count = db.query(FileModel).filter(FileModel.folder_id == folder_id).count()
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if folder:
        folder.file_cnt = count
        folder.last_work = datetime.now()
        db.commit()


# ------------------------------
# 파일 업로드
# ------------------------------
@router.post("/upload/{user_id}/{folder_id}")
async def upload_files(
    user_id: int,
    folder_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    new_idx = get_new_idx(db)
    user = db.query(User).filter(User.user_id == user_id).first()
    folder = db.query(Folder).filter(Folder.folder_id == folder_id, Folder.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    if not files:
        raise HTTPException(status_code=400, detail="업로드할 파일이 없습니다.")

    # 저장 경로
    base_dir = "../uploaded_files"
    folder_dir = os.path.join(base_dir)
    os.makedirs(folder_dir, exist_ok=True)

    uploaded_files = []

    for upload_file in files:
        file_bytes = await upload_file.read()
        new_file = await save_file_to_db(
            user_id=user_id,
            folder_id=folder_id,
            file_id=new_idx,
            file_name=upload_file.filename,
            file_bytes=file_bytes,
            folder_dir=folder_dir,
            file_type=os.path.splitext(upload_file.filename)[1].lstrip("."),
            db=db
        )
        new_idx += 1
        uploaded_files.append(new_file)

    # 폴더 상태 업데이트
    folder.file_cnt = (folder.file_cnt or 0) + len(uploaded_files)
    folder.last_work = datetime.now()
    db.commit()

    # 지원/미지원 파일 분리
    result_supported = []
    result_unsupported = []

    for f in uploaded_files:
        entry = {
            "file_id": f.file_id,
            "file_name": f.file_name,
            "file_path": f.file_path,
            "file_type": f.file_type,
            "uploaded_at": f.uploaded_at
        }
        if f.file_type not in SUPPORTED_EXTENSIONS:
            result_unsupported.append(entry)
        else:
            result_supported.append(entry)

    return {
        "message": f"{len(uploaded_files)}개 파일 처리 완료.",
        "folder_id": folder.folder_id,
        "supported_files": result_supported,
        "unsupported_files": result_unsupported
    }


# ------------------------------
# ZIP 파일 압축 해제
# ------------------------------
@router.post("/unzip/{folder_id}/{zip_file_id}")
async def unzip_zip(
    folder_id: int,
    zip_file_id: int,
    db: Session = Depends(get_db)
):
    new_idx = get_new_idx(db)
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    file = db.query(FileModel).filter(FileModel.file_id == zip_file_id).first()

    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    if not file:
        raise HTTPException(status_code=400, detail="해당 zip 파일이 없습니다.")

    zip_path = file.file_path
    if not os.path.exists(zip_path):
        raise HTTPException(status_code=400, detail="zip 파일 경로가 존재하지 않습니다.")

    base_dir = "../uploaded_files"
    folder_dir = os.path.join(base_dir)
    extracted_files = []

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            if member.is_dir():
                continue
            file_bytes = zip_ref.read(member)
            new_file = await save_file_to_db(
                file_id=new_idx,
                user_id=file.user_id,
                folder_id=folder_id,
                file_name=os.path.basename(member.filename),
                file_bytes=file_bytes,
                folder_dir=folder_dir,
                file_type=os.path.splitext(member.filename)[1].lstrip("."),
                db=db
            )
            new_idx += 1
            extracted_files.append(new_file)

    folder.file_cnt = (folder.file_cnt or 0) + len(extracted_files)
    folder.last_work = datetime.now()
    db.commit()

    # 지원/미지원 파일 분리
    result_supported = []
    result_unsupported = []

    for f in extracted_files:
        entry = {
            "file_id": f.file_id,
            "file_name": f.file_name,
            "file_path": f.file_path,
            "file_type": f.file_type,
            "uploaded_at": f.uploaded_at
        }
        if f.file_type not in SUPPORTED_EXTENSIONS:
            result_unsupported.append(entry)
        else:
            result_supported.append(entry)

    return {
        "message": f"{len(extracted_files)}개의 파일 처리 완료.",
        "folder_id": folder_id,
        "supported_files": result_supported,
        "unsupported_files": result_unsupported
    }
