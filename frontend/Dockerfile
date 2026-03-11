FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY admins.json .
COPY static/ static/

EXPOSE 5000

CMD ["python", "server.py"]
