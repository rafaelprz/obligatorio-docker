FROM alpine

# Alpine: sshd (sin PAM) rechaza la cuenta bloqueada; se desbloquea (! -> *) para login por clave
RUN apk add --no-cache bash openssh && \
    mkdir -p /run/sshd /home/appuser/.ssh && \
    ssh-keygen -A && \
    adduser -D -h /home/appuser appuser && \
    sed -i 's/^appuser:!:/appuser:*:/' /etc/shadow && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'KbdInteractiveAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config

# Clave publica del manager: unico login permitido (por clave, sin contraseña)
COPY manager_key.pub /home/appuser/.ssh/authorized_keys

COPY programa.sh /home/appuser/programa.sh

# StrictModes de sshd exige .ssh 700 y authorized_keys 600 del propio usuario
RUN chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/authorized_keys && \
    chmod +x /home/appuser/programa.sh && \
    chown -R appuser:appuser /home/appuser

CMD ["/usr/sbin/sshd","-D"]
