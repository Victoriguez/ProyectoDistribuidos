# Proyecto Sistemas Distribuidos — UDP 2025

Este proyecto implementa una arquitectura distribuida para la recolección, almacenamiento, análisis y cache de datos de tráfico utilizando información pública de Waze. Cumple con los requisitos solicitados en la entrega 1 del curso.

## 📦 Estructura de Módulos

- `scraper/` — Extrae datos de tráfico desde la API de Waze y los guarda en MongoDB.
- `storage/` — Servicio basado en MongoDB para almacenar los eventos.
- `cache/` — Cache HTTP que entrega eventos bajo dos políticas (LRU o FIFO) y guarda métricas.
- `traffic_generator/` — Genera tráfico de consultas simuladas con distribuciones configurables.

## 🚀 Cómo ejecutar

Desde la raíz del proyecto:

1. Construir los contenedores:

```bash
docker compose build
```

2. Levantar todos los servicios:

```bash
docker compose up
```

Los siguientes servicios estarán disponibles:

- Cache: http://localhost:5001
- MongoDB: puerto 27017

## 🔁 Generador de Tráfico

Configura el generador en `traffic_generator.py`:

```python
ESTRATEGIA = "poisson"  # o "uniforme"
LAM = 0.5  # tasa promedio (λ)
```

El generador consulta eventos simulados al cache cada cierto tiempo, modelando distintas distribuciones de llegada.

## 🔐 Cache de Eventos

El servicio cache implementa:

- Políticas: LRU y FIFO (editables en `cache_server.py`)
- Capacidad máxima: 100 eventos (editable)
- Conexión a MongoDB para cache misses

📊 Endpoint de métricas:

Consulta en cualquier momento:

```
GET http://localhost:5001/stats
```

Respuesta ejemplo:

```json
{
  "cache_hits": 12,
  "cache_misses": 8,
  "cache_size": 8
}
```

## 🧪 Pendientes para pruebas

- Ejecutar múltiples generadores de tráfico con diferentes tasas
- Comparar eficiencia de políticas FIFO vs LRU
- Evaluar escalabilidad del cache y storage

## 👨‍💻 Autores

- Sebastián — Módulos: Traffic Generator, Cache, Integración, Scraper
- Víctor — Módulo: Storage, Optimizaciones, Integración con base de datos