# ./config/pyro_nameserver/Dockerfile
FROM python:3.11

# Actualiza pip y asegura herramientas básicas
RUN pip install --upgrade pip

# Instala Pyro5 explícitamente
RUN pip install Pyro5

# Expone los puertos de Pyro (opcional pero recomendable)
EXPOSE 9090
EXPOSE 9091

# Comando para iniciar el nameserver
CMD ["python", "-m", "Pyro5.nameserver", "-n", "0.0.0.0", "-p", "9090"]
