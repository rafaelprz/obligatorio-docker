FROM python:3.12-alpine

# Cliente SSH (login por clave) y su-exec para bajar privilegios en el entrypoint
RUN apk add --no-cache openssh-client su-exec && \
    adduser -D -h /home/appuser appuser && \
    mkdir -p /home/appuser/.ssh

# Dependencias Python (Flask + SDK de Docker para las metricas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clave privada para conectarse a los runners por clave (legible por appuser)
COPY manager_key /home/appuser/.ssh/id_ed25519

COPY app.py /app.py
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && \
    chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/id_ed25519 && \
    chown -R appuser:appuser /home/appuser

# El entrypoint arranca como root solo para dar acceso al socket, luego baja a appuser.
# El proceso principal (python) no corre como root.
ENTRYPOINT ["/entrypoint.sh"]
