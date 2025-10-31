from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from datetime import datetime
from app.models import FoldersCategory, Folder
from pydantic import BaseModel
from app.models import File as FileModel

router = APIRouter(prefix="/folders", tags=["Categories"])


# 폴더 내 카테고리 목록 조회
@router.get("/{folder_id}/categories")
def get_categories(folder_id: int, db: Session = Depends(get_db)):
    categories = (
        db.query(FoldersCategory)
        .filter(FoldersCategory.folder_id == folder_id)
        .all()
    )
    return {"categories": [c.category_name for c in categories]}


class CategoryCreate(BaseModel):
    category_name: str


# 카테고리 생성
@router.post("/{folder_id}/categories")
def create_category(folder_id: int, cat: CategoryCreate, db: Session = Depends(get_db)):
    exists = db.query(FoldersCategory).filter(
        FoldersCategory.folder_id == folder_id,
        FoldersCategory.category_name == cat.category_name
    ).first()

    if exists:
        raise HTTPException(status_code=400, detail="이미 존재하는 카테고리입니다.")

    new_cat = FoldersCategory(folder_id=folder_id, category_name=cat.category_name)
    db.add(new_cat)

    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if folder:
        folder.last_work = datetime.utcnow()

    db.commit()
    return {"message": "카테고리 생성 완료"}


class CategoryRename(BaseModel):
    new_name: str


# 카테고리 이름 수정
@router.put("/{folder_id}/categories/{old_name}")
def rename_category(folder_id: int, old_name: str, body: CategoryRename, db: Session = Depends(get_db)):
    cat = db.query(FoldersCategory).filter(
        FoldersCategory.folder_id == folder_id,
        FoldersCategory.category_name == old_name
    ).first()

    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")

    cat.category_name = body.new_name

    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if folder:
        folder.last_work = datetime.utcnow()

    db.commit()
    return {"message": "카테고리 이름 수정 완료"}


# 카테고리 삭제
@router.delete("/{folder_id}/categories/{cat_name}")
def delete_category(folder_id: int, cat_name: str, db: Session = Depends(get_db)):
    cat = db.query(FoldersCategory).filter(
        FoldersCategory.folder_id == folder_id,
        FoldersCategory.category_name == cat_name
    ).first()

    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")

    db.delete(cat)

    folder = db.query(Folder).filter(Folder.folder_id == folder_id).first()
    if folder:
        folder.last_work = datetime.utcnow()

    db.commit()
    return {"message": "카테고리 삭제 완료"}


# 카테고리별 파일 목록 조회
@router.get("/{folder_id}/categories/{category_name}/files")
def get_files_by_category(folder_id: int, category_name: str, db: Session = Depends(get_db)):
    """
    특정 폴더 내의 특정 카테고리에 속한 파일 목록을 반환
    """
    # 카테고리 유효성 확인
    category = db.query(FoldersCategory).filter(
        FoldersCategory.folder_id == folder_id,
        FoldersCategory.category_name == category_name
    ).first()

    if not category:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")

    # 해당 카테고리의 파일 목록 조회
    files = (
        db.query(FileModel)
        .filter(FileModel.folder_id == folder_id)
        .filter(FileModel.category == category_name)
        .order_by(FileModel.uploaded_at.desc().nullslast())
        .all()
    )

    result = [
        {
            "file_id": f.file_id,
            "file_name": f.file_name,
            "file_type": f.file_type,
            "is_transform": f.is_transform,
            "is_classification": f.is_classification,
            "uploaded_at": f.uploaded_at
        }
        for f in files
    ]

    return {
        "category_name": category_name,
        "file_count": len(result),
        "files": result
    }

# 카테고리 없는 파일 목록 조회
@router.get("/{folder_id}/files")
def get_files_without_category(folder_id: int, db: Session = Depends(get_db)):
    """
    특정 폴더 안에서 카테고리(category)가 없는 파일들만 조회
    """
    files = (
        db.query(FileModel)
        .filter(FileModel.folder_id == folder_id)
        .filter((FileModel.category == None) | (FileModel.category == ""))  # NULL 또는 빈값
        .order_by(FileModel.uploaded_at.desc().nullslast())
        .all()
    )

    result = [
        {
            "file_id": f.file_id,
            "file_name": f.file_name,
            "file_type": f.file_type,
            "uploaded_at": f.uploaded_at,
        }
        for f in files
    ]

    return {"files": result}
