FROM python:3.11

RUN pip install --upgrade pip

RUN pip install Pyro5

EXPOSE 9090
EXPOSE 9091

CMD ["python", "-m", "Pyro5.nameserver", "-n", "0.0.0.0", "-p", "9090"]
