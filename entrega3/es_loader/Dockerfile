# ProyectoDistribuidos/es_loader/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY load_results_to_elasticsearch.py .

CMD ["python", "load_results_to_elasticsearch.py"]