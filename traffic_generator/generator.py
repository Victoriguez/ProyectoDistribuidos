import time
import requests
import random
import argparse
import numpy as np
from pymongo import MongoClient

def get_all_user_ids():
    client = MongoClient("mongodb://mongo-storage:27017")
    db = client["waze_db"]
    eventos = db["eventos"]
    return eventos.distinct("id")

def get_user_id_distribution_empirical():
    client = MongoClient("mongodb://mongo-storage:27017")
    db = client["waze_db"]
    eventos = db["eventos"]
    pipeline = [{"$group": {"_id": "$id", "count": {"$sum": 1}}}]
    freq_data = list(eventos.aggregate(pipeline))
    user_ids = [item["_id"] for item in freq_data]
    weights = [item["count"] for item in freq_data]
    return user_ids, weights

def traffic_generator(mode="poisson", rate=1.0):
    if mode == "empirical":
        print("📊 Usando distribución empírica basada en frecuencia real...")
        user_ids, weights = get_user_id_distribution_empirical()
    else:
        user_ids = get_all_user_ids()
        weights = None
        print(f"🔢 Total de user_id únicos: {len(user_ids)}")

    while True:
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
        try:
            r = requests.get(f"http://cache:5001/evento/{uid}")
            print(f"📥 Respuesta: {r.status_code} | Evento: {uid}")
        except Exception as e:
            print(f"⚠️ Error en la solicitud: {e}")

        time.sleep(max(delay, 1))

import os

if __name__ == "__main__":
    mode = os.getenv("MODE", "poisson")
    rate = float(os.getenv("RATE", "2.0"))
    traffic_generator(mode=mode, rate=rate)