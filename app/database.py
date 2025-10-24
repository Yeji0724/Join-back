import os
import oracledb
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# .env 불러오기
load_dotenv()

# Oracle Instant Client 초기화
instant_client_path = r"C:\Users\4Class_14\instantclient_23_9"
if os.path.exists(instant_client_path):
    oracledb.init_oracle_client(lib_dir=instant_client_path)

# 환경 변수 불러오기
DB_USER = os.getenv("ORACLE_USER")
DB_PASS = os.getenv("ORACLE_PASSWORD")
DB_HOST = os.getenv("ORACLE_HOST")
DB_PORT = os.getenv("ORACLE_PORT")
DB_SERVICE = os.getenv("ORACLE_SERVICE")

# SERVICE_NAME 방식으로 수정
DATABASE_URL = (
    f"oracle+oracledb://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/?service_name={DB_SERVICE}"
)

# 엔진 및 세션 설정
engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB 세션 종속성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
