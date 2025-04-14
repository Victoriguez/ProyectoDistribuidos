import requests
import time
import random
import numpy as np

# Configuración
ESTRATEGIA = "poisson"  # Cambia a 'uniforme' si quieres
LAM = 0.5               # λ para Poisson (eventos/segundo)
INTERVALO_MIN = 0.5     # Para Uniforme (segundos)
INTERVALO_MAX = 3.0
EVENTOS_A_CONSULTAR = 20  # Número de consultas a realizar

# URL del cache
CACHE_URL = "http://cache:5001"

# Simulamos algunos IDs conocidos
ids_simulados = [
    "user-0", "user-1", "user-2", "user-3", "user-4",
    "user-5", "user-6", "user-7", "user-8", "user-9"
]

def consultar_evento(evento_id):
    try:
        url = f"{CACHE_URL}/evento/{evento_id}"
        response = requests.get(url)
        if response.status_code == 200:
            evento = response.json()
            print(f"📥 Consulta simulada: {evento.get('_id')} | Velocidad: {evento.get('speed')} | Usuario: {evento.get('userName')}")
        else:
            print(f"❌ Evento {evento_id} no encontrado")
    except Exception as e:
        print(f"❌ Error al consultar cache: {e}")

def obtener_intervalo():
    if ESTRATEGIA == "poisson":
        return np.random.exponential(1 / LAM)
    elif ESTRATEGIA == "uniforme":
        return random.uniform(INTERVALO_MIN, INTERVALO_MAX)
    else:
        raise ValueError("Estrategia no válida. Usa 'poisson' o 'uniforme'.")

if __name__ == '__main__':
    print(f"🚦 Generador de tráfico iniciado usando estrategia: {ESTRATEGIA}")

    for i in range(EVENTOS_A_CONSULTAR):
        evento_id = random.choice(ids_simulados)
        consultar_evento(evento_id)
        intervalo = obtener_intervalo()
        print(f"⏳ Esperando {intervalo:.2f} segundos...\n")
        time.sleep(intervalo)

    print("✅ Generador de tráfico finalizado.")
