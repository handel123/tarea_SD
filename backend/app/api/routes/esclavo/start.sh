#!/bin/sh

echo "[START] Esperando a que el servidor RMI esté disponible..."

# Espera hasta que el NameServer esté activo y el objeto registrado
python rmi_client.py &

# Ejecuta el servidor FastAPI
uvicorn main:app --host 0.0.0.0 --port $PORT
