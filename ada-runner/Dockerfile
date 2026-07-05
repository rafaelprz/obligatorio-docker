# --- build: compila el .adb con gnat; el compilador queda SOLO en esta etapa ---
FROM debian:bookworm AS build

RUN apt-get update && apt-get install -y --no-install-recommends gnat && \
    rm -rf /var/lib/apt/lists/*

COPY main.adb .

RUN gnatmake main.adb -o programa

# --- runtime: debian-slim sin compilador; solo el runtime de Ada ---
# El binario GNAT enlaza libgnat/libgnarl (tasking) dinamicamente. Se instala el paquete
# de runtime `libgnat-12` (que trae ambos .so), NO el compilador. Mismo distro/glibc que
# la etapa build para que las versiones de las librerias coincidan (como en c-runner).
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends openssh-server libgnat-12 && \
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

# Binario compilado (no el fuente ni el compilador)
COPY --from=build programa /home/appuser/programa

# StrictModes exige .ssh 700 y authorized_keys 600; la host key debe pertenecer a appuser
RUN chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/authorized_keys && \
    chmod +x /home/appuser/programa && \
    chown appuser:appuser /etc/ssh/ssh_host_ed25519_key && \
    chown -R appuser:appuser /home/appuser

USER appuser

CMD ["/usr/sbin/sshd","-D"]
