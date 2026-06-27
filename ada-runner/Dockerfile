# alpine ya trae las cosas necesarias para ejecutar el ejecutable de c o el script de bash
# pero no trae gnat, y es mas facil instalarlo en un ubuntu
# lo comentado al final es una version de este dockerfile para que la imagen sea minima
FROM ubuntu:24.04

RUN apt update
RUN apt install -y gnat openssh-server

RUN useradd -m appuser

COPY programa.adb .

RUN gnatmake programa.adb

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