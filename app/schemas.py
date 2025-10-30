from pydantic import BaseModel, EmailStr, field_validator


class UserRegister(BaseModel):
    user_login_id: str
    email: EmailStr
    user_password: str
    folder_name: str | None = "unknown" 

    #  아이디 제약: 영문 + 숫자 포함, 8~20자
    @field_validator("user_login_id")
    def validate_user_login_id(cls, v):
        if len(v) < 8 or len(v) > 20:
            raise ValueError("아이디는 8~20자여야 합니다.")
        if not any(c.isalpha() for c in v):
            raise ValueError("아이디에는 영문자가 포함되어야 합니다.")
        if not any(c.isdigit() for c in v):
            raise ValueError("아이디에는 숫자가 포함되어야 합니다.")
        return v

    #  비밀번호 제약: 영문 + 숫자 포함, 8~20자
    @field_validator("user_password")
    def validate_password(cls, v):
        if len(v) < 8 or len(v) > 20:
            raise ValueError("비밀번호는 8~20자여야 합니다.")
        if not any(c.isalpha() for c in v):
            raise ValueError("비밀번호에는 영문자가 포함되어야 합니다.")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호에는 숫자가 포함되어야 합니다.")
        return v

# 로그인
class UserLogin(BaseModel):
    user_login_id: str
    user_password: str

# 폴더 생성
class FolderCreate(BaseModel):
    user_id: int
    folder_name: str