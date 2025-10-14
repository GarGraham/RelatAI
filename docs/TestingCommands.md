Backend:
cd backend
python -m uvicorn relat_ai.api.main:app --reload

Frontend:
cd frontend\streamlit_app
python -m streamlit run app.py