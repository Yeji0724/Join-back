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
    access_key = Column("ACCESS_KEY", String(512))

    # 마지막 작업
    last_work = Column("LAST_WORK", Date)

    # 계정 생성 시간
    created_at = Column("CREATED_AT", Date)

    # 스키마 관계
    folders = relationship("Folder", back_populates="user", cascade="all, delete-orphan")
    files = relationship("File", back_populates="user", cascade="all, delete")
    logs = relationship("Log", back_populates="user", cascade="all, delete")

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
    files = relationship("File", back_populates="folder", cascade="all, delete")
    categories = relationship("FoldersCategory", back_populates="folder", cascade="all, delete")

# FILES
class File(Base):
    __tablename__ = "FILES"

    file_id = Column("FILE_ID", Integer, primary_key=True)
    user_id = Column("USER_ID", Integer, ForeignKey("USERS.USER_ID"), nullable=False)
    folder_id = Column("FOLDER_ID", Integer, ForeignKey("FOLDERS.FOLDER_ID"))
    file_name = Column("FILE_NAME", String(200))
    file_type = Column("FILE_TYPE", String(50))
    file_path = Column("FILE_PATH", String(300))
    is_transform = Column("IS_TRANSFORM", Integer, default=0)
    transform_txt_path = Column("TRANSFORM_TXT_PATH", String(300))
    is_classification = Column("IS_CLASSIFICATION", Integer, default=0)
    category = Column("CATEGORY", String(200))
    uploaded_at = Column("UPLOADED_AT", Date)

    # 관계
    user = relationship("User", back_populates="files")
    folder = relationship("Folder", back_populates="files")


#  LOGS -
class Log(Base):
    __tablename__ = "LOGS"

    log_id = Column("LOG_ID", Integer, primary_key=True, index=True)
    user_id = Column("USER_ID", Integer, ForeignKey("USERS.USER_ID"))
    log_time = Column("LOG_TIME", Date)
    log_content = Column("LOG_CONTENT", String(1000))

    # 관계
    user = relationship("User", back_populates="logs")



# 카테고리
class FoldersCategory(Base):
    __tablename__ = "FOLDERS_CATEGORY"

    folder_id = Column(Integer, ForeignKey("FOLDERS.FOLDER_ID"), primary_key=True)
    category_name = Column(String(200), primary_key=True)

    # 관계 (선택적)
    folder = relationship("Folder", back_populates="categories")