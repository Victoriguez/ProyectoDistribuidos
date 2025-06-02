# ProyectoDistribuidos/cache_loader/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY load_results_to_redis.py .

CMD ["python", "load_results_to_redis.py"]