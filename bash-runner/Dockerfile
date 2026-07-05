FROM alpine

# Alpine: sshd (sin PAM) rechaza la cuenta bloqueada; se desbloquea (! -> *) para login por clave.
# Host key propia de appuser + puerto alto: sshd puede correr sin root (ver USER al final).
RUN apk add --no-cache bash openssh && \
    mkdir -p /run/sshd /home/appuser/.ssh && \
    ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N "" && \
    adduser -D -h /home/appuser appuser && \
    sed -i 's/^appuser:!:/appuser:*:/' /etc/shadow && \
    echo 'Port 2222' >> /etc/ssh/sshd_config && \
    echo 'HostKey /etc/ssh/ssh_host_ed25519_key' >> /etc/ssh/sshd_config && \
    echo 'PidFile none' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'KbdInteractiveAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config

# Clave publica del manager: unico login permitido (por clave, sin contraseña)
COPY manager_key.pub /home/appuser/.ssh/authorized_keys

COPY paddock_manager.sh /home/appuser/programa.sh

# Datos que el script espera en su directorio de trabajo (/home/appuser)
COPY inventario_f1.csv /home/appuser/inventario_f1.csv
COPY mercaderia /home/appuser/mercaderia

# StrictModes exige .ssh 700 y authorized_keys 600; la host key debe pertenecer a appuser
RUN chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/authorized_keys && \
    chmod +x /home/appuser/programa.sh && \
    chown appuser:appuser /etc/ssh/ssh_host_ed25519_key && \
    chown -R appuser:appuser /home/appuser

# El proceso principal ya no corre como root
USER appuser

CMD ["/usr/sbin/sshd","-D"]
