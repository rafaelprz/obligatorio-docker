# se crea una etapa llamada "build" que empieza desde una imagen con gcc instalado
# la cual trae linux, gcc, g++, make, bibliotecas de compilacion
FROM gcc AS build

COPY programa.c .

RUN gcc programa.c -o programa

# la imagen quedo muy grande por tener compiladores y todo eso
# entonces se crea otra etapa desde otra imagen
# en este caso usamos una imagen basada en Debian para que el binario
# compilado con gcc pueda correr correctamente con la misma libc
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends openssh-server passwd && \
    mkdir -p /run/sshd /home/appuser/.ssh && \
    ssh-keygen -A && \
    useradd -m -s /bin/bash appuser && \
    echo 'appuser:app123' | chpasswd && \
    echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'UsePAM no' >> /etc/ssh/sshd_config

# el ejecutable que habia quedado en build, lo traemos a esta imagen
COPY --from=build programa /home/appuser/programa

RUN chmod +x /home/appuser/programa && \
    chown appuser:appuser /home/appuser/programa

# comando a ejecutar cuando se inicia el contenedor
# el comando sshd hace que se empiecen a escuchar conexiones ssh
# pero lo hace en modo deamon, entonces docker piensa que el proceso principal termino y apaga el contenedor
# al ejecutar sshd -D no se demoniza, queda como proceso principal y docker no apaga el contenedor
CMD ["/usr/sbin/sshd","-D"]