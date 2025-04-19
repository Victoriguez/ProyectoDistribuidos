FROM python:3.10-slim

WORKDIR /app

# Instalar curl para el healthcheck
RUN apt-get update && apt-get install -y curl && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cache_server.py .
COPY cache_logic.py .

CMD ["python", "cache_server.py"]