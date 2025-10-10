FROM python:3.11-slim

WORKDIR /app

COPY frontend/streamlit_app ./streamlit_app
RUN pip install --no-cache-dir streamlit>=1.31

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
