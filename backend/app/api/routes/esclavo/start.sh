#!/bin/sh


python rmi_client.py &

uvicorn main:app --host 0.0.0.0 --port $PORT
