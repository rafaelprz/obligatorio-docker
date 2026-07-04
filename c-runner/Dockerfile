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

RUN apt-get update && apt-get install -y --no-install-recommends openssh-server && \
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

# el ejecutable que habia quedado en build, lo traemos a esta imagen
COPY --from=build programa /home/appuser/programa

# StrictModes de sshd exige .ssh 700 y authorized_keys 600 del propio usuario
RUN chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/authorized_keys && \
    chmod +x /home/appuser/programa && \
    chown -R appuser:appuser /home/appuser

# comando a ejecutar cuando se inicia el contenedor
# el comando sshd hace que se empiecen a escuchar conexiones ssh
# pero lo hace en modo deamon, entonces docker piensa que el proceso principal termino y apaga el contenedor
# al ejecutar sshd -D no se demoniza, queda como proceso principal y docker no apaga el contenedor
CMD ["/usr/sbin/sshd","-D"]
