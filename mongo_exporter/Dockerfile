# ProyectoDistribuidos/mongo_exporter/Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY export_mongo_to_tsv.py .

CMD ["python", "export_mongo_to_tsv.py"]