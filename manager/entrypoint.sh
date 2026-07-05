#!/bin/sh
set -e

SOCK=/var/run/docker.sock

# El socket de Docker es de root. Para que appuser (no root) pueda leer metricas,
# se agrega appuser al grupo del socket (creandolo si no existe con ese GID).
if [ -S "$SOCK" ]; then
    SOCK_GID=$(stat -c '%g' "$SOCK")
    GROUP_NAME=$(awk -F: -v gid="$SOCK_GID" '$3==gid {print $1; exit}' /etc/group)
    if [ -z "$GROUP_NAME" ]; then
        addgroup -g "$SOCK_GID" dockerhost
        GROUP_NAME=dockerhost
    fi
    addgroup appuser "$GROUP_NAME"
fi

export HOME=/home/appuser

# Se bajan privilegios: el proceso principal (python) corre como appuser, no root.
exec su-exec appuser python /app.py
