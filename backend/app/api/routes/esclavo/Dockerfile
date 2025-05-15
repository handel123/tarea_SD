

FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt
RUN chmod +x start.sh

EXPOSE ${PORT}



CMD ["sh", "start.sh"]

