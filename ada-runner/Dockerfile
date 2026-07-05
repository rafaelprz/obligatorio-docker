# alpine ya trae las cosas necesarias para ejecutar el ejecutable de c o el script de bash
# pero no trae gnat, y es mas facil instalarlo en un ubuntu
# lo comentado al final es una version de este dockerfile para que la imagen sea minima
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends gnat openssh-server && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /run/sshd /home/appuser/.ssh && \
    rm -f /etc/ssh/ssh_host_* && \
    ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N "" && \
    useradd -m -d /home/appuser -s /bin/bash appuser && \
    sed -i 's/^appuser:!:/appuser:*:/' /etc/shadow && \
    sed -i '/^UsePAM/d' /etc/ssh/sshd_config && \
    echo 'Port 2222' >> /etc/ssh/sshd_config && \
    echo 'HostKey /etc/ssh/ssh_host_ed25519_key' >> /etc/ssh/sshd_config && \
    echo 'PidFile none' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'KbdInteractiveAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'UsePAM no' >> /etc/ssh/sshd_config

# Clave publica del manager: unico login permitido (por clave, sin contraseña)
COPY manager_key.pub /home/appuser/.ssh/authorized_keys

COPY main.adb .

# StrictModes de sshd exige .ssh 700 y authorized_keys 600 del propio usuario
RUN gnatmake main.adb && \
    mv main /home/appuser/programa && \
    chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/authorized_keys && \
    chmod +x /home/appuser/programa && \
    chown appuser:appuser /etc/ssh/ssh_host_ed25519_key && \
    chown -R appuser:appuser /home/appuser

# El proceso principal ya no corre como root
USER appuser

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
