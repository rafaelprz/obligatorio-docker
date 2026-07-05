FROM python:3.12-alpine

# Solo cliente SSH (login por clave). appuser se agrega al grupo root para poder leer
# el socket de Docker (root:root en Docker Desktop) sin ser root ni escribir en runtime.
# En un host con grupo 'docker' propio, cambiar 'root' por ese grupo.
RUN apk add --no-cache openssh-client && \
    adduser -D -h /home/appuser appuser && \
    addgroup appuser root && \
    mkdir -p /home/appuser/.ssh

# Dependencias Python: solo el SDK de Docker (el server web usa la stdlib, sin framework)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clave privada para conectarse a los runners por clave (legible por appuser)
COPY manager_key /home/appuser/.ssh/id_ed25519

COPY app.py /app.py

RUN chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/id_ed25519 && \
    chown -R appuser:appuser /home/appuser

ENV HOME=/home/appuser
ENV PYTHONDONTWRITEBYTECODE=1

# El proceso principal (python) corre como appuser, no root.
USER appuser

CMD ["python","/app.py"]
