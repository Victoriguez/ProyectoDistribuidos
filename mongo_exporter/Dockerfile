# ProyectoDistribuidos/mongo_exporter/Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends libgeos-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove libgeos-dev && \
    rm -rf /var/lib/apt/lists/*
COPY export_mongo_to_tsv.py .
COPY comunas_rm.geojson ./
CMD ["python", "export_mongo_to_tsv.py"]