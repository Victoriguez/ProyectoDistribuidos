
# ProyectoDistribuidos — Sistemas Distribuidos 2025-1

Este proyecto corresponde a la Entrega 1 del curso de Sistemas Distribuidos. Implementa un sistema distribuido modular capaz de extraer, almacenar, simular y cachear eventos de tráfico desde Waze Live Map para la Región Metropolitana de Chile.

---

## 🧑‍💻 Integrantes

- Sebastián [@Sej0taGrove]
- Víctor [@victoriguez]

---

## 📦 Estructura del proyecto

El proyecto está organizado en 4 módulos principales, cada uno desplegado como un contenedor independiente usando Docker:

```
ProyectoDistribuidos/
├── scraper/             # Módulo de scraping (obtiene eventos desde Waze)
├── storage/             # Módulo de almacenamiento (MongoDB)
├── traffic_generator/   # (próximamente) Generador de consultas sintéticas
├── cache/               # (próximamente) Sistema de cache para respuestas repetidas
└── docker-compose.yml   # Orquestador de todos los servicios
```

---

## ✅ Estado actual

✔️ Módulo scraper implementado:  
- Consulta periódicamente la API pública de Waze Live Map.
- Descarga eventos tipo "users" desde la Región Metropolitana.
- Guarda directamente en MongoDB sin archivos intermedios.

✔️ Módulo storage implementado:  
- Usa MongoDB 6.0 como base de datos.
- Recibe los datos desde scraper a través de PyMongo.
- Persistencia con volumen Docker.
- Colección: eventos (en la base de datos waze_db)

⏳ Módulos traffic_generator y cache están planificados y en desarrollo.

---

## 🚀 Cómo ejecutar el proyecto

Asegurate de tener Docker y Docker Compose instalados.

1. Cloná el repositorio:

```bash
git clone https://github.com/victoriguez/ProyectoDistribuidos.git
cd ProyectoDistribuidos
```

2. Levantá los servicios (scraper + MongoDB):

```bash
docker compose up --build
```

Esto iniciará:
- MongoDB como servicio storage
- El scraper que consultará Waze cada 5 segundos e insertará datos en la base

3. Verificá que los datos se estén guardando:

En otra terminal:

```bash
docker exec -it mongo-storage mongosh
```

Dentro del cliente de Mongo:

```js
use waze_db
db.eventos.countDocuments()
```

Deberías ver un número creciente de documentos (eventos tipo “users”).

---

## 📌 Tecnologías utilizadas

- Python 3.10 (scraper)
- requests + pymongo
- MongoDB 6.0
- Docker y Docker Compose

---

## 🛠 Próximas tareas

- Implementar generador de tráfico (Poisson + Uniforme)
- Implementar sistema de cache (LRU, FIFO)
- Medición de métricas de eficiencia
- Documentar decisiones de diseño
