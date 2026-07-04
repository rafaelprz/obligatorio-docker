FROM python:3.12-alpine

RUN apk add --no-cache openssh-client sshpass

# Instalamos desde requirements.txt (Flask + SDK de Docker para las metricas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python","app.py"]