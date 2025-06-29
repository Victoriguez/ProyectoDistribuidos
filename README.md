# Proyecto Sistemas Distribuidos - Entrega 2 y 3: Procesamiento y Visualización de Tráfico

**Integrantes:**
*   Sebastián Espinoza
*   Víctor Rodriguez

---

## Descripción General

Este proyecto implementa un pipeline completo para la recolección, procesamiento, análisis y visualización de datos de tráfico de la plataforma Waze en la Región Metropolitana de Santiago. El sistema está diseñado para transformar datos crudos en agregados analíticos significativos y presentarlos en un dashboard interactivo.

El pipeline se compone de los siguientes módulos principales, orquestados por Docker Compose:

1.  **Scraper**: Recolecta datos de la API GeoRSS de Waze.
2.  **Almacenamiento (MongoDB)**: Persiste los datos crudos de Waze.
3.  **Mongo Exporter (Python)**: Extrae datos de MongoDB, los enriquece (añadiendo comuna, hora del día, día de la semana) y los guarda como un archivo TSV.
4.  **Pig Processor (Apache Pig)**: Lee el archivo TSV, realiza filtrado, estandarización de tipos y análisis agregados.
5.  **Cache Loader (Python)**: Carga los resultados agregados de Pig en un caché Redis.
6.  **Elasticsearch Loader (Python)**: Carga los resultados agregados y los datos de eventos completos en Elasticsearch.
7.  **Servicios de Persistencia y Visualización**: Redis, Elasticsearch y Kibana.

---

## Arquitectura del Sistema

El flujo de datos y procesamiento es el siguiente:

**Waze API -> Scraper -> MongoDB (storage) -> Mongo Exporter -> `waze_events.tsv` -> Pig Processor -> Archivos TSV de Resultados -> (a) Cache Loader -> Redis & (b) ES Loader -> Elasticsearch -> Kibana (Visualización)**

Todos los servicios son gestionados como contenedores Docker y orquestados por Docker Compose.

---

## Tecnologías Utilizadas

*   **Lenguajes de Programación:** Python 3.10, Pig Latin (Apache Pig 0.17.0)
*   **Contenerización:** Docker, Docker Compose
*   **Procesamiento de Datos:** Apache Pig 0.17.0 (sobre OpenJDK 11)
*   **Bases de Datos y Caché:**
    *   MongoDB 6.0
    *   Redis (imagen `redis:alpine`)
    *   Elasticsearch 7.17.10
*   **Visualización:** Kibana 7.17.10
*   **Librerías Python Clave:** `requests`, `pymongo`, `shapely`, `redis`, `elasticsearch`

---

## Estructura del Proyecto

ProyectoDistribuidos/
├── docker-compose.yml
├── scraper/
│ ├── Dockerfile
│ ├── requirements.txt
│ └── scraper.py
├── mongo_exporter/
│ ├── Dockerfile
│ ├── requirements.txt
│ ├── export_mongo_to_tsv.py
│ └── comunas_rm.geojson
├── entrega2/
│ └── pig_processing/
│ ├── Dockerfile.pig
│ ├── data_input/ # (Generado por mongo_exporter)
│ ├── data_output/ # (Generado por pig_processor)
│ └── scripts/
│ └── process_waze_data.pig
├── cache_loader/
│ ├── Dockerfile
│ ├── requirements.txt
│ └── load_results_to_redis.py
└── entrega3/
└── es_loader/
├── Dockerfile
├── requirements.txt
└── load_results_to_elasticsearch.py


---

## Instrucciones de Ejecución del Pipeline Completo

Siga estos pasos desde la raíz del repositorio clonado:

### 1. Prerrequisitos
*   Asegúrese de tener **Docker Desktop** instalado y en ejecución.

### 2. Limpiar Entornos Anteriores (Recomendado)
Para asegurar una ejecución limpia, ejecute el siguiente comando en su terminal:
```bash
docker-compose down --remove-orphans
```

Si desea eliminar también los datos persistentes de MongoDB y Redis:

docker volume rm proyectodistribuidos_mongo_data proyectodistribuidos_redis_pig_data proyectodistribuidos_elastic_data

### 3. Construir y Ejecutar el Pipeline
Este único comando construirá todas las imágenes necesarias y levantará todos los servicios en el orden correcto definido por depends_on.

docker-compose up --build

La opción --build es importante la primera vez o si se han modificado los Dockerfile.

El proceso completo puede tardar varios minutos la primera vez, especialmente mientras se descargan las imágenes de Elasticsearch y Kibana.

Los servicios scraper, mongo_exporter, pig_processor, cache_loader y es_loader son "jobs" que realizarán su tarea y saldrán con code 0 si todo es exitoso.

Los servicios storage, redis_actual_cache, elasticsearch y kibana son servidores y permanecerán corriendo. Es normal que la terminal se quede mostrando los logs de estos servicios.

### 4. Verificar Resultados
Para verificar, abra una nueva terminal mientras el pipeline sigue corriendo en la primera.

a.- Verificar Redis

docker exec -it redis_cache_for_pig_results redis-cli

Dentro de redis-cli, pruebe:

KEYS stats:*
GET stats:comuna:Santiago
exit

Debería ver una lista de claves y el conteo para la comuna solicitada.

b.- Verificar Elasticsearch

# Listar los índices creados
curl "http://localhost:9200/_cat/indices?v"

# Contar los documentos en el índice de eventos
curl "http://localhost:9200/waze_eventos_procesados/_count?pretty"

# Ver un ejemplo de un documento
curl "http://localhost:9200/waze_eventos_procesados/_search?pretty"

El primer comando debería mostrar sus índices (waze_eventos_procesados, stats_incidentes_por_comuna, etc.) con un conteo de documentos mayor a cero.

c.- Visualizar en Kibana

Abra su navegador web y vaya a http://localhost:5601.

En el menú (☰), vaya a Stack Management > Index Patterns.

Cree los siguientes patrones de índice:

waze_eventos_procesados: Para el campo de tiempo, seleccione timestamp_original_iso.

stats_*: Seleccione la opción "I don't want to use the Time Filter".

Vaya a Dashboard en el menú principal para crear o ver las visualizaciones.

### 5. Detener Todos los Servicios
En la terminal donde ejecutó docker-compose up, presione Ctrl + C. O, desde cualquier terminal en la raíz del proyecto:

docker-compose down

Justificación de Decisiones de Diseño Clave
Exportación a TSV antes de Pig: Dada la naturaleza End-of-Life del conector mongo-hadoop y las dificultades para integrar librerías Python con dependencias C (como shapely) directamente en UDFs de Pig/Jython, se tomó la decisión pragmática de realizar el enriquecimiento de datos (determinación de comuna y parseo de timestamps) en el script Python mongo_exporter.

Procesamiento Principal en Pig: Una vez que los datos son ingeridos por Pig desde el archivo TSV, todo el filtrado, estandarización y análisis agregados se realizan íntegramente utilizando Apache Pig, cumpliendo con el requisito central de la entrega.

Doble Destino para Resultados (Redis y Elasticsearch): Los resultados agregados se cargan tanto en Redis como en Elasticsearch para cumplir con los requisitos de ambas entregas: Redis para un caché rápido de clave-valor y Elasticsearch para las capacidades avanzadas de búsqueda y visualización de Kibana.

---

## Evaluación de Rendimiento (Ejemplo)

*(Esta sección debe ser completada por el alumno con las mediciones reales obtenidas durante las pruebas).*

Se realizaron pruebas de rendimiento para X eventos, midiendo los tiempos de ejecución de los componentes clave:

| Componente         | Tiempo de Ejecución (X eventos) |
| :----------------- | :------------------------------ |
| `mongo_exporter`   | *(ej. XX.X s)*                  |
| `pig_processor`    | *(ej. YY.Y s)*                  |
| `cache_loader`     | *(ej. ZZ.Z s)*                  |
| **Pipeline Total** | *(ej. TT.T s)*                  |

**Observaciones:**
*   *(Análisis breve de los tiempos).*
*   *(Identificación de la etapa más costosa).*
*   *(Limitaciones de la prueba en entorno local).*

---