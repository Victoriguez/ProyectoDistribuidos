# Proyecto de Sistemas Distribuidos - Entrega 1

## Descripción General

Este proyecto tiene como objetivo la construcción de un sistema distribuido que recolecta, almacena y analiza eventos de tráfico en tiempo real extraídos desde Waze. Se compone de 4 módulos principales que se comunican de forma secuencial: 

1. Scraper
2. Almacenamiento (MongoDB)
3. Generador de Tráfico
4. Sistema de Caché

---

## 1. Scraper

El scraper se conecta a la API de Waze Live Map para extraer información geoespacial de usuarios y eventos en la Región Metropolitana de Santiago, Chile.

- Extrae datos cada 5 segundos.
- Guarda los eventos en MongoDB.
- Objetivo: alcanzar 10.000 eventos.

### Endpoint consultado

```
https://www.waze.com/live-map/api/georss?top=-33.3&bottom=-33.7&left=-70.9&right=-70.5&env=row&types=alerts,traffic,users
```

---

## 2. Almacenamiento (MongoDB)

Se utiliza MongoDB por su alta velocidad de escritura y flexibilidad con documentos JSON.

- Se aloja en un contenedor llamado `mongo-storage`.
- Base de datos: `waze_db`
- Colección: `eventos`
- Se incluye un módulo `cleaner.py` que elimina eventos inválidos o corrige el campo `timestamp`.

---

## 3. Generador de Tráfico

Este módulo simula tráfico de consultas de eventos, representando cómo distintos usuarios acceden a los datos.

### Modos de distribución soportados:

- `poisson`: usa numpy para generar tasas de arribo según una distribución de Poisson.
- `uniform`: genera una consulta cada segundo a un user_id aleatorio.
- `empirical`: basada en la distribución real observada de user_ids desde MongoDB.

Las consultas se hacen al módulo de caché.

---

## 4. Sistema de Caché

Un servidor Flask que:

- Expone un endpoint: `GET /evento/<user_id>`
- Almacena respuestas en memoria.
- Implementa políticas de reemplazo:
  - LRU (Least Recently Used)
  - FIFO (First In First Out)
- Configurable por variables de entorno:
  - `CACHE_POLICY`
  - `CACHE_SIZE`

---

## Uso con Docker

### 1. Construir y levantar los servicios

```bash
docker compose up --build
```

### 2. Consultar estado de Mongo

```bash
docker exec -it mongo-storage mongosh
```

### 3. Ver logs del generador de tráfico

```bash
docker logs traffic_generator
```

---

## Métricas del Caché

Disponible en:

```bash
curl http://localhost:5001/metrics
```

Ejemplo de salida:

```json
{
  "cache_hits": 12,
  "cache_misses": 8,
  "cache_tamaño": 8
}
```

---

## Consideraciones

- Se recomienda ejecutar el módulo `cleaner` después de acumular los eventos.
- El sistema está preparado para escalabilidad y portabilidad gracias a Docker.
- La distribución empírica ofrece un modelo más realista, basado en datos reales del scraping.

---

## Repositorio

📎 https://github.com/Victoriguez/ProyectoDistribuidos