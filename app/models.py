from sqlalchemy import Column, Integer, String, Date, Sequence, ForeignKey
from app.database import Base
from sqlalchemy.orm import relationship

# Oracle용 시퀀스 (USER_ID 자동 증가)
user_id_seq = Sequence('USER_ID_SEQ', start=1, increment=1)

class User(Base):
    __tablename__ = "USERS"

    # 사용자 고유 ID (PK)
    user_id = Column("USER_ID", Integer, user_id_seq,
                     primary_key=True,
                     server_default=user_id_seq.next_value())

    # 로그인 아이디
    user_login_id = Column("USER_LOGIN_ID", String(50),
                           unique=True, nullable=False)

    # 이메일
    email = Column("EMAIL", String(100),
                   unique=True, nullable=False)

    # 비밀번호
    user_password = Column("USER_PASSWORD", String(200), nullable=False)

    # API 토큰
    access_key = Column("ACCESS_KEY", String(100))

    # 파일 저장 기본 경로
    user_directory = Column("USER_DIRECTORY", String(200))

    # 계정 생성 시간
    created_at = Column("CREATED_AT", Date)

    # 스키마 관계
    folders = relationship("Folder", back_populates="user", cascade="all, delete-orphan")


# Folder 테이블용 시퀀스
folder_id_seq = Sequence('FOLDER_ID_SEQ', start = 1, increment = 1)

class Folder(Base):
    __tablename__ = "FOLDERS"
    folder_id = Column("FOLDER_ID", Integer, folder_id_seq,
                       primary_key=True,
                       server_default=folder_id_seq.next_value())
    user_id = Column("USER_ID", Integer, ForeignKey("USERS.USER_ID"), nullable=False)
    folder_name = Column("FOLDER_NAME", String(200), nullable=False)
    file_cnt = Column("FILE_CNT", Integer, default=0)
    connected_directory = Column("CONNECTED_DIRECTORY", String(300))
    classification_after_change = Column("CLASSIFICATION_AFTER_CHANGE", Integer, default=0)
    last_work = Column("LAST_WORK", Date)

    user = relationship("User", back_populates="folders")