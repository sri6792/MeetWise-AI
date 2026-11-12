# MeetWise AI backend

See the project-level `README.md` for setup, API table and deployment.

Quick start:
```powershell
venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
pytest -v
```
