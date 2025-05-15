# rmi_client.py
import asyncpg
import asyncio
import os
import Pyro5.api
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

PORT_BD = int(os.environ.get("PORT_BD"))
DATABASE_TYPE = os.environ.get("DATABASE_TYPE")
DB_CONFIG = {
    "db_url": f"postgresql://postgres:postgres@{os.getenv('DATABASE_HOST')}:{os.getenv('PORT_BD')}/{os.getenv('DATABASE_TYPE')}",
}



RMI_SERVER_NAME = "recolector_logs"
PYRO_NS_HOST = "pyro_nameserver"
PYRO_NS_PORT = 9090


async def esperar_rmi(nombre_objeto, retries=20, delay=3):
    for intento in range(retries):
        try:
            ns = Pyro5.api.locate_ns(host=PYRO_NS_HOST, port=PYRO_NS_PORT)
            uri = ns.lookup(nombre_objeto)
            uri = str(uri).replace("0.0.0.0", "recolector_logs").replace("localhost", "recolector_logs")

            return uri
        except Exception:
            await asyncio.sleep(delay)
    raise Exception(f"No se encontró el objeto RMI '{nombre_objeto}' después de {retries} intentos")


async def esperar_db(db_url, retries=10, delay=2):
    for attempt in range(retries):
        try:
            conn = await asyncpg.connect(db_url)
            await conn.close()
            return True
        except Exception:
            await asyncio.sleep(delay)
    return False


@Pyro5.api.expose
class LogClient:
    def __init__(self):
        self.last_log_id = 0

    async def fetch_new_logs(self, conn):
        rows = await conn.fetch(
            """
            SELECT id_log, timestamp_ini, timestamp_fin, documento_id,
                   query_busqueda, score_obtenido, rango_etario, resultados, parametros, ip_cliente,
                   tiempo_procesamiento, cantidad_resultados
            FROM consulta_logs
            WHERE id_log > $1 AND centralizado = FALSE
            ORDER BY id_log
            """, self.last_log_id
        )
        return rows

    async def mark_as_centralized(self, conn, log_id):
        await conn.execute("UPDATE consulta_logs SET centralizado = TRUE WHERE id_log = $1", log_id)

    async def send_logs_to_server(self):
        ns = Pyro5.api.locate_ns(host=PYRO_NS_HOST, port=PYRO_NS_PORT)
        uri = ns.lookup(RMI_SERVER_NAME)
        log_server = Pyro5.api.Proxy(uri)

        while True:
            try:
                conn = await asyncpg.connect(DB_CONFIG["db_url"])
                logs = await self.fetch_new_logs(conn)
                if logs:
                    for log in logs:
                        data = dict(log)
                        self.last_log_id = data["id_log"]

                        for k in ["timestamp_ini", "timestamp_fin"]:
                            if isinstance(data[k], datetime):
                                data[k] = data[k].isoformat()

                        try:
                            log_server.receive_log(data)
                            await self.mark_as_centralized(conn, data["id_log"])
                        except Exception as e:
                            print("[Error]")
                await conn.close()
            except Exception as e:
                print(f"[Error general] {e}")
            await asyncio.sleep(5)


async def main():
    if await esperar_db(DB_CONFIG["db_url"]):
        try:
            await esperar_rmi(RMI_SERVER_NAME)
        except Exception as e:
            exit(1)
        client = LogClient()
        await client.send_logs_to_server()
    else:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
