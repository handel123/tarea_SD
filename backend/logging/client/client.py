# rmi_client.py
import asyncpg
import asyncio
import os
import Pyro5.api
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configuración de la base de datos del esclavo (se puede parametrizar por entorno)
DB_CONFIG = {
    "host": os.getenv("DATABASE_HOST", "localhost"),
    "port": int(os.getenv("PORT_BD", 5433)),
    "user": "postgres",
    "password": "postgres",
    "database": os.getenv("DATABASE_TYPE", "libros"),
}

RMI_SERVER_URI = os.getenv("RMI_SERVER_URI", "PYRONAME:log.colector")

@Pyro5.api.expose
class LogClient:
    def __init__(self):
        self.last_log_id = 0  # para saber desde dónde leer

    async def fetch_new_logs(self):
        conn = await asyncpg.connect(**DB_CONFIG)
        try:
            rows = await conn.fetch(
                """
                SELECT id_log, timestamp_ini, timestamp_fin, documento_id,
                        query_busqueda, score_obtenido, rango_etario, resultados,parametros,ip_cliente,
                        tiempo_procesamiento, cantidad_resultados
                FROM consulta_logs
                WHERE id_log > $1 AND centralizado = FALSE
                ORDER BY id_log
                """, self.last_log_id
            )
            return rows
        finally:
            await conn.close()

    async def mark_as_centralized(self, conn, log_id):
        await conn.execute("UPDATE consulta_logs SET centralizado = TRUE WHERE id_log = $1", log_id)

    async def send_logs_to_server(self):
        log_server = Pyro5.api.Proxy(RMI_SERVER_URI)
        while True:
            conn = await asyncpg.connect(**DB_CONFIG)
            logs = await self.fetch_new_logs()
            if logs:
                for log in logs:
                    data = dict(log)
                    self.last_log_id = data["id_log"]
                    # transformar datetime a string para JSON o CSV
                    for k in ["timestamp_ini", "timestamp_fin"]:
                        if isinstance(data[k], datetime):
                            data[k] = data[k].isoformat()
                    try:
                        log_server.receive_log(data)
                        await self.mark_as_centralized(conn, data["id_log"])
                        print(f"[Enviado] Log ID {data['id_log']} enviado al servidor RMI")
                    except Exception as e:
                        print(f"[Error] Falló el envío del log ID {data['id_log']}: {e}")
            await asyncio.sleep(5)  # Esperar un poco antes de consultar de nuevo

if __name__ == "__main__":
    client = LogClient()
    asyncio.run(client.send_logs_to_server())
