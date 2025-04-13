
# ProyectoDistribuidos – Análisis de Tráfico en la RM (Entrega 1)

Este proyecto forma parte de la entrega 1 del curso de Sistemas Distribuidos. Consiste en un sistema modular distribuido para recolectar, almacenar y analizar eventos de tráfico desde Waze Live Map.

## 🧱 Estructura del Proyecto

El proyecto está compuesto por los siguientes módulos (cada uno en su propia carpeta):

- `scraper/` — se encarga de extraer eventos del mapa de Waze.
- `storage/` — responsable de almacenar los eventos obtenidos.
- `traffic_generator/` — simula tráfico de consultas al sistema.
- `cache/` — sistema de cache que mejora el rendimiento del acceso a eventos.

Todos los módulos están orquestados usando Docker Compose.

## 📦 Requisitos

Antes de comenzar, asegúrate de tener instalado:

- Git
- Docker
- Docker Compose (viene con Docker Desktop)
- Visual Studio Code (opcional, recomendado)

## ⚙️ Instrucciones para correr el proyecto

1. Abre una terminal y navega a la carpeta donde quieres guardar el proyecto. Por ejemplo:

```bash
cd Desktop
mkdir ProyectoUDP
cd ProyectoUDP
```

2. Clona el repositorio:

```bash
git clone https://github.com/victoriguez/ProyectoDistribuidos.git
cd ProyectoDistribuidos
```

3. Levanta los contenedores del sistema:

```bash
docker compose up --build
```

4. Verifica que los servicios están activos:

```bash
docker ps
```

Deberías ver los servicios: scraper, storage, traffic_generator y cache.

## 🧪 Estado actual de la entrega

- [x] Estructura inicial del proyecto
- [x] Docker Compose funcional
- [ ] Módulo scraper implementado
- [ ] Almacenamiento persistente
- [ ] Simulación de tráfico
- [ ] Sistema de cache con políticas de reemplazo
- [ ] Métricas y análisis

## 👥 Integrantes del grupo

- Víctor Iguez
- Sebastián (tu apellido aquí)
