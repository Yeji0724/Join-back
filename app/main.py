from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.routers import auth, folders, categories, files, download

#  1. FastAPI 앱 생성
app = FastAPI()

#  2. CORS 설정 (꼭 app 바로 밑에 위치해야 작동함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 허용할 프론트 주소
    allow_credentials=True,
    allow_methods=["*"],    # 모든 메서드 허용 (POST, GET 등)
    allow_headers=["*"],    # 모든 헤더 허용
)

#  3. DB 테이블 생성
Base.metadata.create_all(bind=engine)

#  4. 라우터 등록
app.include_router(auth.router)
app.include_router(folders.router)
app.include_router(categories.router)
app.include_router(files.router)
app.include_router(download.router)

#  5. 테스트용 루트 엔드포인트
@app.get("/")
def root():
    return {"message": "Backend Running"}