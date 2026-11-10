FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
USER 1000:1000
EXPOSE 7654 9100
CMD ["python", "-u", "server.py"]
