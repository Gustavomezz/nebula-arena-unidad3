FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
USER 1000:1000
CMD exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 60 main:app
