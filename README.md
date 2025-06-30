# Análisis de Tráfico con Pipeline Distribuido - Entrega 3

**Integrantes:**
- Sebastian Espinoza
- Victor Rodriguez

## Descripción General

Este proyecto implementa un **pipeline completo de Big Data** para la ingesta, procesamiento, análisis y visualización de datos de tráfico de la plataforma Waze en la Región Metropolitana de Santiago. El sistema transforma datos crudos en insights accionables para la gestión de tráfico utilizando herramientas del ecosistema de Big Data.

### Objetivo
Desarrollar una solución end-to-end que permita:
- Recolectar datos de tráfico en tiempo real desde Waze
- Procesar y enriquecer la información con datos geoespaciales
- Realizar análisis agregados utilizando Apache Pig
- Almacenar resultados en sistemas de caché y búsqueda
- Visualizar insights mediante dashboards interactivos

## Arquitectura del Sistema

El sistema sigue una **arquitectura de pipeline secuencial** orquestada con Docker Compose:

```
Waze API → Scraper → MongoDB → Mongo Exporter → Apache Pig → Resultados
                                     ↓              ↓
                              Enriquecimiento   Análisis
                                     ↓              ↓
                                   TSV        Redis + Elasticsearch
                                                     ↓
                                                  Kibana
```

### Flujo de Datos Detallado

1. **Ingesta**: Scraper Python recolecta alertas de Waze
2. **Almacenamiento**: Datos crudos se guardan en MongoDB
3. **Enriquecimiento**: Python + Shapely añade información geoespacial
4. **Procesamiento**: Apache Pig realiza análisis agregados
5. **Caché**: Redis almacena resultados para acceso rápido
6. **Indexación**: Elasticsearch indexa datos para búsquedas
7. **Visualización**: Kibana presenta dashboards interactivos

## Tecnologías Utilizadas

### Core Technologies
- **Lenguajes**: Python 3.10, Pig Latin
- **Big Data**: Apache Pig 0.17.0
- **Bases de Datos**: MongoDB 6.0, Redis, Elasticsearch 7.17.10
- **Visualización**: Kibana 7.17.10
- **Orquestación**: Docker, Docker Compose

### Librerías Python
- `requests` - API calls
- `pymongo` - MongoDB integration
- `shapely` - Geospatial processing
- `redis` - Cache management
- `elasticsearch` - Search engine integration

## 📁 Estructura del Proyecto

```
ProyectoDistribuidos/
├── docker-compose.yml                    # Orquestación completa
├── scraper/                             # Recolección de datos
│   ├── Dockerfile
│   ├── requirements.txt
│   └── scraper.py
├── mongo_exporter/                      # Enriquecimiento de datos
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── export_mongo_to_tsv.py
│   └── comunas_rm.geojson
├── entrega2/pig_processing/             # Procesamiento con Pig
│   ├── Dockerfile.pig
│   ├── data_input/                      # waze_events.tsv
│   ├── data_output/                     # Resultados de Pig
│   └── scripts/
│       └── process_waze_data.pig
├── cache_loader/                        # Carga a Redis
│   ├── Dockerfile
│   ├── requirements.txt
│   └── load_results_to_redis.py
├── es_loader/                           # Carga a Elasticsearch
│   ├── Dockerfile
│   ├── requirements.txt
│   └── load_to_elasticsearch.py
└── README.md
```

## Instrucciones de Ejecución

### Prerrequisitos
- Docker Desktop instalado y ejecutándose
- Docker Compose V2
- Conexión a internet
- 8GB RAM mínimo recomendado

### Ejecución Completa del Pipeline

1. **Clonar el repositorio**
   ```bash
   git clone <https://github.com/Victoriguez/ProyectoDistribuidos.git>
   cd ProyectoDistribuidos
   ```

2. **Limpiar ejecuciones anteriores** (recomendado)
   ```bash
   docker-compose down --remove-orphans
   docker volume prune -f
   ```

3. **Construir e iniciar el pipeline completo**
   ```bash
   docker-compose up --build
   ```

4. **Monitorear el progreso**
   - Los servicios de procesamiento (`scraper`, `mongo_exporter`, `pig_processor`, etc.) se ejecutarán secuencialmente
   - Los servicios de infraestructura (`mongodb`, `redis`, `elasticsearch`, `kibana`) permanecerán activos

### Verificación de Resultados

#### Verificar datos en MongoDB
```bash
docker exec -it mongodb_container mongosh waze_db --eval "db.eventos.countDocuments()"
```

#### Verificar cache en Redis
```bash
docker exec -it redis_cache_for_pig_results redis-cli
# Dentro de redis-cli:
KEYS stats:*
GET stats:type:CONGESTION
```

#### Verificar índices en Elasticsearch
```bash
curl "http://localhost:9200/_cat/indices?v"
```

#### Acceder a Kibana
- URL: http://localhost:5601

## Servicios y Componentes

### Servicios de Procesamiento

| Servicio | Función | Tecnología |
|----------|---------|------------|
| `scraper` | Recolección de datos Waze | Python + requests |
| `mongo_exporter` | Enriquecimiento geoespacial | Python + Shapely |
| `pig_processor` | Análisis agregados | Apache Pig 0.17.0 |
| `cache_loader` | Carga a Redis | Python + redis |
| `es_loader` | Carga a Elasticsearch | Python + elasticsearch |

### Servicios de Infraestructura

| Servicio | Función | Puerto | Volumen |
|----------|---------|--------|---------|
| `storage` (MongoDB) | Almacenamiento de datos crudos | 27017 | `mongo_data` |
| `redis_actual_cache` | Cache de resultados | 6379 | `redis_pig_data` |
| `elasticsearch` | Motor de búsqueda | 9200 | `es_data` |
| `kibana` | Visualización | 5601 | - |


## 🔧 Decisiones de Diseño

### Arquitectura Pragmática
- **Problema**: Conector mongo-hadoop End-of-Life con MongoDB 6.0
- **Solución**: Enriquecimiento en Python antes del procesamiento en Pig
- **Beneficio**: Mayor robustez y compatibilidad

### Enriquecimiento Geoespacial
- **Herramienta**: Shapely para cálculos geométricos
- **Datos**: GeoJSON de comunas de la Región Metropolitana
- **Proceso**: Point-in-polygon para determinar comuna por coordenadas

### Rol de Apache Pig
- **Función principal**: Motor de análisis agregado
- **Operaciones**: GROUP BY, SUM, filtrado
- **Salida**: 5 conjuntos de datos agregados

