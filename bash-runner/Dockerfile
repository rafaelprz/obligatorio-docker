FROM alpine

RUN apk add --no-cache bash openssh shadow && \
    mkdir -p /run/sshd /home/appuser/.ssh && \
    ssh-keygen -A && \
    adduser -D -h /home/appuser appuser && \
    echo 'appuser:app123' | chpasswd && \
    chown -R appuser:appuser /home/appuser && \
    echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'UsePAM no' >> /etc/ssh/sshd_config

COPY programa.sh /home/appuser/programa.sh

RUN chmod +x /home/appuser/programa.sh

CMD ["/usr/sbin/sshd","-D"]