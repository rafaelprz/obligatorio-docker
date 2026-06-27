FROM alpine

RUN apk add --no-cache bash openssh

RUN adduser -D appuser

COPY programa.sh /home/appuser/programa.sh

# otorgar permisos de ejecucion del script
RUN chmod +x /home/appuser/programa.sh

CMD ["/usr/sbin/sshd","-D"]