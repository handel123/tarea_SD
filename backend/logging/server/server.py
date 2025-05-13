import Pyro5.api
import os
import csv
from datetime import datetime

# Nombre del archivo donde se guardarán todos los logs
LOG_FILE = "central_logs.csv"

@Pyro5.api.expose
class LogCollector:
    def __init__(self):
        self._initialize_csv()

    def _initialize_csv(self):
        """Inicializa el archivo CSV si no existe."""
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "timestamp_ini", "timestamp_fin",
                    "query_busqueda", "score_obtenido", "rango_etario", "resultados","parametros","ip_cliente",
                    "tiempo_procesamiento", "cantidad_resultados"
                ])

    def receive_log(self, log_data: dict):
        """Recibe un log y lo guarda en el archivo central."""
        print(f"[{datetime.now()}] Recibiendo log de {log_data.get('maquina', 'desconocida')}")

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
        return "Log recibido exitosamente."

# Publicar el objeto en el Daemon de Pyro5
def main():
    daemon = Pyro5.api.Daemon()
    uri = daemon.register(LogCollector)
    print("Servidor RMI iniciado. URI:", uri)

    # También puede registrarse en un nameserver si se desea
    try:
        ns = Pyro5.api.locate_ns()
        ns.register("log.colector", uri)
        print("Registrado en el NameServer como 'log.colector'")
    except Exception as e:
        print("No se pudo registrar en el NameServer:", e)

    daemon.requestLoop()

if __name__ == "__main__":
    main()
