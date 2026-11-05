FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml requirements.txt ./
COPY src ./src
COPY app ./app
COPY data ./data
RUN python -m pip install --no-cache-dir .

EXPOSE 8501
CMD ["streamlit", "run", "app/dashboard.py", "--server.address=0.0.0.0"]
