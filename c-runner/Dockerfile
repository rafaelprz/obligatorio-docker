# se crea una etapa llamada "build" que empieza desde una imagen con gcc instalado
# la cual trae linux, gcc, g++, make, bibliotecas de compilacion
FROM gcc AS build

COPY cocineros_mozos.c .

# -pthread: el programa usa hilos POSIX y semaforos; expresa la intencion y
# asegura el link correcto (no depende de que glibc >= 2.34 tenga pthread en libc)
RUN gcc -pthread cocineros_mozos.c -o programa

# la imagen quedo muy grande por tener compiladores y todo eso
# entonces se crea otra etapa desde otra imagen
# en este caso usamos una imagen basada en Debian para que el binario
# compilado con gcc pueda correr correctamente con la misma libc
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends openssh-server && \
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

# el ejecutable que habia quedado en build, lo traemos a esta imagen
COPY --from=build programa /home/appuser/programa

# StrictModes de sshd exige .ssh 700 y authorized_keys 600 del propio usuario
RUN chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/authorized_keys && \
    chmod +x /home/appuser/programa && \
    chown appuser:appuser /etc/ssh/ssh_host_ed25519_key && \
    chown -R appuser:appuser /home/appuser

# El proceso principal ya no corre como root
USER appuser

# comando a ejecutar cuando se inicia el contenedor
# el comando sshd hace que se empiecen a escuchar conexiones ssh
# pero lo hace en modo deamon, entonces docker piensa que el proceso principal termino y apaga el contenedor
# al ejecutar sshd -D no se demoniza, queda como proceso principal y docker no apaga el contenedor
CMD ["/usr/sbin/sshd","-D"]
