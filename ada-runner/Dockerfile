# alpine ya trae las cosas necesarias para ejecutar el ejecutable de c o el script de bash
# pero no trae gnat, y es mas facil instalarlo en un ubuntu
# lo comentado al final es una version de este dockerfile para que la imagen sea minima
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends gnat openssh-server && \
    mkdir -p /run/sshd && \
    ssh-keygen -A && \
    useradd -m -s /bin/bash appuser && \
    echo 'appuser:app123' | chpasswd && \
    echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'UsePAM no' >> /etc/ssh/sshd_config

COPY programa.adb .

RUN gnatmake programa.adb && \
    mv programa /home/appuser/programa && \
    chmod +x /home/appuser/programa && \
    chown appuser:appuser /home/appuser/programa

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