from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app.models import User, Folder
from app.utils.security import hash_password, verify_password, create_access_token
from app.schemas import UserRegister, UserLogin 

router = APIRouter(prefix="/auth", tags=["Auth"])


# 회원가입
@router.post("/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.user_login_id == user.user_login_id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 존재하는 아이디입니다.")

    hashed_pw = hash_password(user.password)
    new_user = User(
        user_login_id=user.user_login_id,
        email=user.email,
        user_password=hashed_pw,
        created_at=date.today()
    )
    db.add(new_user)
    db.flush()          # USER_ID 확보

    # 폴더 생성
    folder_name = (user.folder_name or "unknown").strip()
    new_folder = Folder(
        user_id = new_user.user_id,
        folder_name = folder_name,
        file_cnt = 0,
        classification_after_change = 0
    )

    db.add(new_folder)
    db.commit()
    db.refresh(new_user)
    return {"message": "회원가입 성공", 
            "user_id": new_user.user_id,
            "folder_name": folder_name}

# 로그인
@router.post("/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    print(" 로그인 요청 body:", user.dict())  
    db_user = db.query(User).filter(User.user_login_id == user.user_login_id).first()

    if not db_user or not verify_password(user.password, db_user.user_password):
        print("로그인 실패: 유저 없음 or 비밀번호 불일치")
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")

    token = create_access_token({"sub": str(db_user.user_id)})
    db_user.access_key = token
    db.commit()
    print("로그인 성공:", db_user.user_login_id)
    return {"message": "로그인 성공", "token": token, "user_id": db_user.user_id}

