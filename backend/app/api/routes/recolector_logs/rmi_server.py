import Pyro5.api
from Pyro5.server import Daemon
import os
import csv
from datetime import datetime
import socket
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = os.getenv("LOG_FILE")

@Pyro5.api.expose
class LogCollector:

    def __init__(self):
        self._initialize_csv()

    def _initialize_csv(self):
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, mode='w', newline='') as file:

                writer = csv.writer(file)

                writer.writerow([

                    "timestamp_ini", "timestamp_fin",
                    "query_busqueda", "score_obtenido", "rango_etario", "resultados","parametros","ip_cliente",
                    "tiempo_procesamiento", "cantidad_resultados"
                ])

    def receive_log(self, log_data: dict):

        with open(LOG_FILE, mode='a', newline='') as file:


            writer = csv.writer(file)

            writer.writerow([

                log_data.get("timestamp_ini"),
                log_data.get("timestamp_fin"),
                log_data.get("maquina"),
                log_data.get("tipo_maquina"),
                log_data.get("query_busqueda"),
                log_data.get("score_obtenido"),
                log_data.get("rango_etario"),
                log_data.get("resultados"),
                log_data.get("parametros"),
                log_data.get("ip_cliente"),
                log_data.get("tiempo_procesamiento"),
                log_data.get("cantidad_resultados")
            ])

def main():

    daemon = Pyro5.api.Daemon(host="0.0.0.0")

    uri = daemon.register(LogCollector)  # registra la clase
    uri = str(uri).replace("0.0.0.0", "recolector_logs")

    ns = Pyro5.api.locate_ns(host="pyro_nameserver", port=9090)

    ns.register("recolector_logs", uri)    # registra el nombre en el NameServer


    daemon.requestLoop()

if __name__ == "__main__":
    main()
