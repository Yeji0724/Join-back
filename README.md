py -m venv venv

venv\scripts\activate

pip install -r requirements.txt

pip install uvicorn 

- 실행
uvicorn app.main:app --reload


.env 폴더에 테스트로 제 계정 넣어놔서 수정해야함.

<img width="422" height="215" alt="image" src="https://github.com/user-attachments/assets/f8a1e56d-8896-4490-879e-617bb6744f91" />
