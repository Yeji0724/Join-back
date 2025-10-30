from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FoldersCategory
from pydantic import BaseModel

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
    db.commit()

    return {"message": "카테고리 생성 완료"}


class CategoryRename(BaseModel):
    new_name: str


# 카테고리 이름 수정
@router.put("/{folder_id}/category/{old_name}")
def rename_category(folder_id: int, old_name: str, body: CategoryRename, db: Session = Depends(get_db)):
    cat = db.query(FoldersCategory).filter(
        FoldersCategory.folder_id == folder_id,
        FoldersCategory.category_name == old_name
    ).first()

    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")

    cat.category_name = body.new_name
    db.commit()

    return {"message": "카테고리 이름 수정 완료"}


# 카테고리 삭제
@router.delete("/{folder_id}/category/{cat_name}")
def delete_category(folder_id: int, cat_name: str, db: Session = Depends(get_db)):
    cat = db.query(FoldersCategory).filter(
        FoldersCategory.folder_id == folder_id,
        FoldersCategory.category_name == cat_name
    ).first()

    if not cat:
        raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")

    db.delete(cat)
    db.commit()

    return {"message": "카테고리 삭제 완료"}
