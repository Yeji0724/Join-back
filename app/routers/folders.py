from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Folder
from app.schemas import FolderCreate
from pydantic import BaseModel

router = APIRouter(prefix="/folders", tags=["Folders"])


# 폴더 목록 조회 (최신순)
@router.get("/{user_id}")
def get_user_folders(user_id: int, db: Session = Depends(get_db)):
    folders = (
        db.query(Folder)
        .filter(Folder.user_id == user_id)
        .order_by(Folder.last_work.desc().nullslast())
        .all()
    )

    result = [
        {
            "folder_id": f.folder_id,
            "user_id": f.user_id,
            "folder_name": f.folder_name,
            "file_cnt": f.file_cnt,
            "last_work": f.last_work.isoformat() if f.last_work else None
        }
        for f in folders
    ]

    return {"folders": result}


# 폴더 생성
@router.post("/create")
def create_folder(folder: FolderCreate, db: Session = Depends(get_db)):
    if not folder.folder_name.strip():
        raise HTTPException(status_code=400, detail="폴더 이름을 입력해주세요.")

    new_folder = Folder(
        user_id=folder.user_id,
        folder_name=folder.folder_name.strip(),
        file_cnt=0,
        classification_after_change=0,
        last_work=datetime.utcnow()
    )

    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)

    return {"message": "폴더 생성 완료", "folder_id": new_folder.folder_id, "folder_name": new_folder.folder_name}


# 폴더 이름 수정
class FolderRename(BaseModel):
    new_name: str


@router.patch("/{folder_id}/rename")
def rename_folder(folder_id: int, renameData: FolderRename, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()

    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

    if not renameData.new_name.strip():
        raise HTTPException(status_code=400, detail="폴더 이름은 공백일 수 없습니다.")

    folder.folder_name = renameData.new_name.strip()
    folder.last_work = datetime.utcnow()

    db.commit()
    db.refresh(folder)  # 인자 추가

    return {"message": "폴더 이름 수정 완료", "folder_name": folder.folder_name}


# 폴더 삭제
@router.delete("/{folder_id}")
def delete_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()

    if not folder:
        raise HTTPException(status_code=404, detail="폴더를 찾을 수 없습니다.")

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
