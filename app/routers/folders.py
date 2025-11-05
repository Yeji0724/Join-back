from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Folder, File, FoldersCategory
from app.schemas import FolderCreate
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/folders", tags=["Folders"])

CLASSIFICATOR_URL = "http://localhost:8002/new_file/"


# 폴더 목록 조회 (최신순)
@router.get("/{user_id}")
def get_user_folders(user_id: int, db: Session = Depends(get_db)):
    folders = (
        db.query(Folder)
        .filter(Folder.user_id == user_id)
        .order_by(Folder.last_work.desc().nullslast())
        .all()
    )

    result = []
    for f in folders:
        # 파일 개수 실시간 계산 (Files 테이블에서 COUNT)
        file_count = db.query(File).filter(File.folder_id == f.folder_id).count()

        result.append({
            "folder_id": f.folder_id,
            "user_id": f.user_id,
            "folder_name": f.folder_name,
            "file_cnt": file_count,   # DB 실시간 카운트 반영
            "last_work": f.last_work.isoformat() if f.last_work else None
        })

    return {"folders": result}

# 폴더 생성
@router.post("/create")
def create_folder(folder: FolderCreate, db: Session = Depends(get_db)):
    name = folder.folder_name.strip()

    if not name:
        raise HTTPException(status_code=400, detail="폴더 이름을 입력해주세요.")

    if len(name) > 20:
        raise HTTPException(status_code=400, detail="폴더 이름은 20자 이하로 입력해주세요.")

    new_folder = Folder(
        user_id=folder.user_id,
        folder_name=name,
        file_cnt=0,
        classification_after_change=0,
        last_work=datetime.utcnow()
    )

    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)

    return {
        "message": "폴더 생성 완료",
        "folder_id": new_folder.folder_id,
        "folder_name": new_folder.folder_name
    }

# 폴더 이름 수정
class FolderRename(BaseModel):
    new_name: str


@router.patch("/{folder_id}/rename")
def rename_folder(folder_id: int, renameData: FolderRename, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()

    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    new_name = renameData.new_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="폴더 이름은 공백일 수 없습니다.")

    if len(new_name) > 20:
        raise HTTPException(status_code=400, detail="폴더 이름은 20자 이하로 입력해주세요.")

    folder.folder_name = new_name
    folder.last_work = datetime.utcnow()

    db.commit()
    db.refresh(folder)

    return {"message": "폴더 이름 수정 완료", "folder_name": folder.folder_name}

# 폴더 삭제
@router.delete("/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()

    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")
    
    # 카테고리 삭제
    categories = db.query(FoldersCategory).filter(FoldersCategory.folder_id == folder_id).all()

    for cat in categories:
        # 각 카테고리 안의 파일 삭제
        db.query(File).filter(File.folder_id == cat.folder_id).delete()

    # 카테고리 자체 삭제
    db.query(FoldersCategory).filter(FoldersCategory.folder_id == folder_id).delete()

    # 폴더 안의 카테고리 없는 파일 삭제
    db.query(File).filter(File.folder_id == folder_id).delete()

    # 폴더 삭제
    db.delete(folder)
    db.commit()

    return {"message": "폴더 삭제 완료", "folder_id": folder_id}

# 폴더 새로고침
@router.get("/info/{folder_id}")
def get_folder_info(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()

    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    return {
        "folder_id": folder.folder_id,
        "folder_name": folder.folder_name,
        "last_work": folder.last_work
    }

# 폴더 활동 시간 갱신 (새로고침 시)
@router.patch("/{folder_id}/refresh")
def refresh_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()

    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    folder.last_work = datetime.utcnow()
    db.commit()
    db.refresh(folder)

    return {"message": "폴더 활동 시간 갱신 완료", "last_work": folder.last_work.isoformat()}

#  특정 폴더 내 파일 전체 조회
@router.get("/{folder_id}/files")
def get_files_in_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    files = db.query(File).filter(File.folder_id == folder_id).all()
    file_list = [
        {
            "file_id": f.file_id,
            "file_name": f.file_name,
            "file_type": f.file_type,
            "is_transform": f.is_transform,  # 0: 대기, 1: 진행중, 2: 완료
            "is_classification": f.is_classification  # 0: 미분류, 1: 분류중, 2: 완료
        }
        for f in files
    ]

    return {"folder_id": folder_id, "files": file_list}

# 진행현황 계산 API
@router.get("/{folder_id}/progress")
def get_folder_progress(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    files = db.query(File).filter(File.folder_id == folder_id).all()
    total = len(files)

    if total == 0:
        return {
            "folder_id": folder_id,
            "total": 0,
            "transform_done": 0,
            "transform_pending": 0,
            "transform_waiting": 0,
            "classification_done": 0,
            "classification_pending": 0,
            "classification_waiting": 0,
            "transform_rate": 0,
            "classification_rate": 0
        }

    # 상태별 계산 (대기 포함)
    transform_done = sum(f.is_transform == 2 for f in files)
    transform_pending = sum(f.is_transform == 1 for f in files)
    transform_waiting = sum(f.is_transform == 0 for f in files)

    classification_done = sum(f.is_classification == 2 for f in files)
    classification_pending = sum(f.is_classification == 1 for f in files)
    classification_waiting = sum(f.is_classification == 0 for f in files)

    transform_rate = round((transform_done / total) * 100, 1)
    classification_rate = round((classification_done / total) * 100, 1)

    return {
        "folder_id": folder_id,
        "total": total,
        "transform_done": transform_done,
        "transform_pending": transform_pending,
        "transform_waiting": transform_waiting,
        "classification_done": classification_done,
        "classification_pending": classification_pending,
        "classification_waiting": classification_waiting,
        "transform_rate": transform_rate,
        "classification_rate": classification_rate
    }

# 분류 요청 
@router.post("/{folder_id}/classify")
async def classify_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    folder.classification_after_change = 1

    files = db.query(File).filter(File.folder_id == folder_id).all()
    if not files:
        raise HTTPException(status_code=404, detail="해당 폴더에 파일이 없습니다.")
    
    for f in files:
        f.is_classification = 0
        f.files = None
    
    db.commit()

    payload = {"files": [{"FILE_ID": f.file_id, "FILE_TYPE": f.file_type} for f in files]}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.post(CLASSIFICATOR_URL, json=payload)
            res.raise_for_status()
            return {
                "message": "분류 요청 완료",
                "file_count": len(files),
                "response": res.json()
            }
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="분류 서버에 연결할 수 없습니다.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"분류 요청 중 오류: {e}")

