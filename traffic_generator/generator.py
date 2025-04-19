import time
import requests
import random
import numpy as np
from pymongo import MongoClient

def esperar_cache(url, intentos=10, intervalo=3):
    """
    Espera a que el servicio de caché esté disponible.
    """
    for i in range(intentos):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("✅ Caché está listo.")
                return
        except requests.exceptions.ConnectionError:
            print(f"⏳ Esperando al caché... intento {i+1}/{intentos}")
            time.sleep(intervalo)
    raise Exception("❌ No se pudo conectar al caché después de varios intentos.")

def get_all_user_ids():
    """
    Obtiene todos los IDs de usuario únicos desde MongoDB.
    """
    client = MongoClient("mongodb://mongo-storage:27017")
    db = client["waze_db"]
    eventos = db["eventos"]
    user_ids = eventos.distinct("id")
    print(f"🔢 Total de user_id únicos obtenidos: {len(user_ids)}")
    return user_ids

def get_user_id_distribution_empirical():
    """
    Obtiene una distribución empírica de IDs de usuario basada en la frecuencia real.
    """
    client = MongoClient("mongodb://mongo-storage:27017")
    db = client["waze_db"]
    eventos = db["eventos"]
    pipeline = [{"$group": {"_id": "$id", "count": {"$sum": 1}}}]
    freq_data = list(eventos.aggregate(pipeline))
    user_ids = [item["_id"] for item in freq_data]
    weights = [item["count"] for item in freq_data]
    print(f"📊 Distribución empírica obtenida: {len(user_ids)} IDs únicos.")
    return user_ids, weights

def traffic_generator(mode="poisson", rate=1.0):
    """
    Generador de tráfico que consulta eventos al caché usando diferentes distribuciones.
    """
    if mode == "empirical":
        print("📊 Usando distribución empírica basada en frecuencia real...")
        user_ids, weights = get_user_id_distribution_empirical()
    else:
        user_ids = get_all_user_ids()
        weights = None

    if not user_ids:
        print("❌ No se encontraron user_ids en la base de datos. Verifica el scraper.")
        return

    print(f"🚦 Iniciando generador de tráfico en modo: {mode}")

    while True:
        try:
            if mode == "poisson":
                delay = np.random.poisson(rate)
                uid = random.choice(user_ids)
            elif mode == "uniform":
                delay = 1
                uid = random.choice(user_ids)
            elif mode == "empirical":
                delay = 1
                uid = random.choices(user_ids, weights=weights, k=1)[0]
            else:
                print("❌ Modo inválido. Usa 'poisson', 'uniform' o 'empirical'.")
                break

            print(f"📤 Consultando evento con user_id: {uid} usando distribución: {mode}")
            r = requests.get(f"http://cache:5001/evento/{uid}")
            if r.status_code == 200:
                print(f"✅ Respuesta: {r.status_code} | Evento encontrado: {uid}")
            elif r.status_code == 404:
                print(f"❌ Evento no encontrado en la base de datos: {uid}")
            else:
                print(f"⚠️ Respuesta inesperada: {r.status_code}")

            time.sleep(max(delay, 1))
        except KeyboardInterrupt:
            print("🛑 Generador de tráfico detenido por el usuario.")
            break
        except Exception as e:
            print(f"⚠️ Error en el generador de tráfico: {e}")
            time.sleep(2)

if __name__ == "__main__":
    import os

    # Leer variables de entorno
    mode = os.getenv("MODE", "poisson")
    rate = float(os.getenv("RATE", "2.0"))

    # Esperar a que el caché esté listo
    esperar_cache("http://cache:5001/metrics")

    # Iniciar el generador de tráfico
    traffic_generator(mode=mode, rate=rate)