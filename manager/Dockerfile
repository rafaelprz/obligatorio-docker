FROM python:3.12-alpine

# Solo cliente SSH: la autenticacion es por clave, ya no se usa sshpass
RUN apk add --no-cache openssh-client

# Instalamos desde requirements.txt (Flask + SDK de Docker para las metricas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clave privada del manager para conectarse a los runners por clave
COPY manager_key /root/.ssh/id_ed25519
RUN chmod 700 /root/.ssh && chmod 600 /root/.ssh/id_ed25519

COPY app.py .

CMD ["python","app.py"]
