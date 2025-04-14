# Proyecto Distribuidos - Análisis de Tráfico Waze

## Descripción general

Este sistema distribuido simula un flujo completo de procesamiento de datos de tráfico obtenidos desde Waze. Se compone de cuatro módulos principales:
1. Scraper: extrae datos automáticamente desde el Live Map de Waze (API indirecta).
2. Almacenamiento: almacena los datos en MongoDB.
3. Traffic Generator: genera tráfico de consultas sobre los datos siguiendo distribuciones probabilísticas.
4. Cache: optimiza el acceso a datos repetidos utilizando políticas de reemplazo como LRU o FIFO.

Además, se incluye un módulo auxiliar de limpieza (cleaner) que verifica y normaliza los datos en la base.

## Estructura del proyecto

```
ProyectoDistribuidos/
├── docker-compose.yml
├── scraper/
│   └── scraper.py
├── storage/
│   ├── cleaner.py
│   ├── Dockerfile
│   └── requirements.txt
├── traffic_generator/
│   └── generator.py
├── cache/
│   └── cache_server.py
```

## Requisitos

- Docker & Docker Compose
- Python 3.10+ (solo para desarrollo local)

## Instrucciones de uso

1. Clona el repositorio y entra a la carpeta del proyecto.
2. Ejecuta:

```bash
docker compose build
docker compose up
```

3. Esto levantará:
- MongoDB en storage
- El microservicio cache en :5001
- El traffic generator consultando a cache
- El scraper obteniendo datos periódicamente

Para limpiar la base de datos manualmente:

```bash
docker compose up cleaner
```

## Verificación del funcionamiento

- La base de datos se puede consultar usando:

```bash
docker exec -it mongo-storage mongosh
use waze_db
db.eventos.countDocuments()
```

- Para ver estadísticas del cache:

```bash
curl http://localhost:5001/stats
```

## Justificación de diseño

- MongoDB fue elegido por su flexibilidad en esquemas y soporte para grandes volúmenes de datos.
- El sistema fue modularizado para facilitar pruebas, escalabilidad y mantenimiento.
- Se utilizaron contenedores Docker para garantizar portabilidad.
- Cache fue implementado como microservicio independiente para probar diferentes políticas de reemplazo.

## Consideraciones

- El cleaner es parte del módulo de almacenamiento.
- El tráfico simulado se basa en distribución Poisson, con opción a cambiarla fácilmente.
- Todos los módulos son intercambiables o ampliables.
- Se alcanzó el objetivo de 10.000 eventos.