# se crea una etapa llamada "build" que empieza desde una imagen con gcc instalado
# la cual trae linux, gcc, g++, make, bibliotecas de compilacion
FROM gcc AS build

COPY programa.c .

RUN gcc programa.c -o programa

# la imagen quedo muy grande por tener compiladores y todo eso
# entonces se crea otra etapa desde otra imagen
# la imagen de alpine es de las mas livianas
# al terminar el build, la imagen final es la ultima etapa
FROM alpine

# instalar openssh
RUN apk add --no-cache openssh

# Crear keys
RUN ssh-keygen -A

# se crea un usuario en el sistema operativo alpine del contenedor
# se hace para que sea este usuario el que ejecuta los procesos y no root
RUN adduser -D appuser

# el ejecutable que habia quedado en build, lo traemos a esta imagen
COPY --from=build programa /home/appuser/programa

# comando a ejecutar cuando se inicia el contenedor
# el comando sshd hace que se empiecen a escuchar conexiones ssh
# pero lo hace en modo deamon, entonces docker piensa que el proceso principal termino y apaga el contenedor
# al ejecutar sshd -D no se demoniza, queda como proceso principal y docker no apaga el contenedor
CMD ["/usr/sbin/sshd","-D"]