# Informe del trabajo práctico — Parte 4: Virtualización

## Introducción

La cuarta parte del trabajo se centró en la virtualización de la solución mediante Docker Compose. El objetivo principal fue transformar el conjunto de programas en una infraestructura más organizada, aislada y reproducible, de modo que cada componente pudiera ejecutarse en su propio contenedor y mantenerse controlado desde una única estructura de orquestación.

Esta parte del trabajo no buscó solamente “hacer correr” los programas, sino también aplicar criterios de seguridad, mínima superficie de ataque y separación de responsabilidades. En esa línea, la solución fue diseñada como una stack de cuatro contenedores: un manager y tres runners, cada uno con una función específica.

## Objetivo de la infraestructura

La infraestructura propuesta fue pensada para cumplir con tres metas principales:

1. aislar cada aplicación en un entorno independiente;
2. permitir que el manager interactúe con los runners de manera controlada;
3. exponer un panel de monitoreo simple, funcional y basado en métricas reales.

## Arquitectura general

La solución se organiza en cuatro servicios definidos en Docker Compose:

- manager: es el punto de entrada del sistema. Actúa como cliente SSH para los runners y además ofrece un panel web de monitoreo.
- bash-runner: contiene la aplicación desarrollada en Bash.
- c-runner: contiene la aplicación desarrollada en C.
- ada-runner: contiene la aplicación desarrollada en Ada.

Los runners se encuentran conectados a una red interna, mientras que el manager se conecta tanto a esa red interna como a una red externa de puente, lo que le permite publicar el panel web en el host.

## Características de la infraestructura

### 1. Uso de cuatro contenedores en un único stack

Una de las condiciones del trabajo fue asegurar que la solución se ejecutara como una única infraestructura compuesta por cuatro contenedores. Esto se cumplió mediante el archivo Docker Compose, donde se definieron exactamente cuatro servicios: manager, bash-runner, c-runner y ada-runner.

### 2. Ejecución con un usuario no privilegiado

Otra de las decisiones del diseño fue evitar que los procesos principales corrieran como root. Para ello, en los Dockerfiles de los runners y del manager se crea un usuario dedicado, denominado appuser, y luego se establece ese usuario como el usuario que ejecuta el proceso principal.
Esto reduce la superficie de ataque y evita que el contenedor funcione con privilegios innecesarios durante la ejecución normal.

### 3. Sistema de archivos de solo lectura

La infraestructura fue diseñada para limitar la capacidad de escritura de los contenedores. Para ello, se configuró el parámetro read_only: true en los servicios, lo que hace que el sistema de archivos raíz del contenedor se monte en modo de solo lectura.
Además, los servicios en el docker compose cuentan con un tmpfs en /tmp para permitir un espacio temporal escribible cuando el proceso necesita trabajar con archivos temporales. Esta combinación permite mantener el contenedor más seguro sin romper el funcionamiento básico de las aplicaciones.

### 4. Capacidades mínimas del contenedor

Se buscó reducir al mínimo las capacidades del kernel disponibles dentro de los contenedores. Para ello, se configuró cap_drop: [ALL], lo que elimina prácticamente todas las capacidades del contenedor y deja un entorno mucho más restringido.

Esto es especialmente relevante en un entorno de virtualización, porque limita lo que un proceso comprometido podría hacer si se logra ejecutar código malicioso dentro del contenedor.

### 5. Prevención de escalada de privilegios

Además de restringir capacidades, la infraestructura incorpora la opción security_opt: no-new-privileges:true. Esta medida impide que un proceso pueda obtener privilegios adicionales mediante mecanismos de ejecución posteriores.

Con este ajuste, aunque un proceso interno fuera comprometido, tendría menor posibilidad de escalar permisos y afectar al sistema de manera más profunda.

### 6. Red interna y aislamiento de servicios

Uno de los puntos más importantes del diseño fue garantizar que los runners no fueran accesibles directamente desde fuera de la infraestructura. Para eso, los tres runners se conectaron a una red interna llamada backend, que se define como una red de tipo internal.

Esto se observa en la definición de la red en Docker Compose, la red backend tiene la opción internal: true, lo que impide que los contenedores de esa red salgan al exterior y también evita que sean alcanzados desde el host de manera directa. De esta forma, el manager es el único punto de comunicación con ellos.

### 7. Publicación mínima de puertos

El sistema fue diseñado para exponer el menor número posible de puertos. En este caso, los runners no publican puertos al host, mientras que el manager expone únicamente el puerto 8080.

Esto permite acceder al panel web desde el navegador sin abrir más puertos que los estrictamente necesarios. La decisión es coherente con el principio de mínima superficie expuesta.

### 8. SSH endurecido

En los runners, el servidor SSH se configura para aceptar únicamente autenticación por clave pública, deshabilitando la autenticación por contraseña. Además, se prohíbe el acceso de root por SSH y se incorpora la clave pública del manager en authorized_keys.

Esta configuración fue implementada en los Dockerfiles de los runners, donde se crean las host keys, se escriben las configuraciones de sshd y se copian las claves necesarias. También se ajustan permisos de directorios y archivos para que sshd acepte la autenticación de manera segura. Este mecanismo permite que el manager se conecte a los runners sin depender de contraseñas y con una configuración mucho más restringida.

### 9. Imágenes y software mínimos

Otro punto relevante del diseño fue evitar instalar componentes innecesarios dentro de las imágenes. Para ello, se utilizaron imágenes base mínimas y, en los casos de C y Ada, se aplicó una estrategia de compilación en múltiples etapas.

Para lograr esto, la imagen de compilación solo se usa para generar el ejecutable, mientras que la imagen final contiene únicamente lo necesario para ejecutar la aplicación. Ademas, en las imágenes basadas en Alpine o Debian slim se emplean opciones como --no-cache, --no-install-recommends y la limpieza de listas de paquetes, lo que reduce el tamaño final y evita dejar software sobrante en la imagen.

### 10. Monitoreo con métricas reales

La infraestructura incorpora un panel de monitoreo que muestra métricas obtenidas directamente del daemon de Docker. Para ello, el servicio manager monta el socket docker.sock dentro del contenedor y utiliza el SDK de Docker para consultar información de los contenedores.


## Conclusión

La cuarta parte del trabajo fue clave porque permitió cerrar el ciclo completo del obligatorio: desde la implementación de las aplicaciones hasta su ejecución en un entorno controlado y preparado para ser administrado. 

Gracias a Docker Compose, el proyecto pasó a ser una infraestructura completa, con contenedores bien separados, una red interna definida, un sistema de acceso más seguro y un panel de monitoreo funcional.

La infraestructura construida cumple con los principios de aislamiento, seguridad y simplicidad que se buscaban.
