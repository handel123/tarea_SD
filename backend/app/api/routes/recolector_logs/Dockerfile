FROM python:3.11-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install Pyro5

CMD ["python", "rmi_server.py"]
