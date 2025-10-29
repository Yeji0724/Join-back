python -m venv venv

venv\scripts\activate

pip install uvicorn 

# 로그인/회원가입
uvicorn app.main:app --reload --port=8004

# 폴더 불러오기 생성,삭제,수정
uvicorn app.main:app --reload --port=8000


.env 폴더에 테스트로 제 계정 넣어놔서 수정해야함.

<img width="422" height="215" alt="image" src="https://github.com/user-attachments/assets/f8a1e56d-8896-4490-879e-617bb6744f91" />
