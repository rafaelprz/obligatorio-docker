# alpine ya trae las cosas necesarias para ejecutar el ejecutable de c o el script de bash
# pero no trae gnat, y es mas facil instalarlo en un ubuntu
# lo comentado al final es una version de este dockerfile para que la imagen sea minima
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends gnat openssh-server && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /run/sshd /home/appuser/.ssh && \
    ssh-keygen -A && \
    useradd -m -d /home/appuser -s /bin/bash appuser && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'KbdInteractiveAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'UsePAM no' >> /etc/ssh/sshd_config

# Clave publica del manager: unico login permitido (por clave, sin contraseña)
COPY manager_key.pub /home/appuser/.ssh/authorized_keys

COPY programa.adb .

# StrictModes de sshd exige .ssh 700 y authorized_keys 600 del propio usuario
RUN gnatmake programa.adb && \
    mv programa /home/appuser/programa && \
    chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/authorized_keys && \
    chmod +x /home/appuser/programa && \
    chown -R appuser:appuser /home/appuser

CMD ["/usr/sbin/sshd","-D"]


#FROM ubuntu AS build
#
#RUN apt update && apt install -y gnat
#
#COPY programa.adb .
#
#RUN gnatmake programa.adb
#
#FROM alpine
#
#RUN apk add --no-cache openssh
#
#COPY --from=build programa /home/appuser/programa
