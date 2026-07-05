# Informe técnico — Parte 4: Virtualización

Explicación **línea por línea y flag por flag** de la infraestructura: los cuatro
`Dockerfile`, el `docker-compose.yaml` y la aplicación del manager (`app.py`). No se
documentan las aplicaciones de las Partes 1–3 (bash, C, ADA) en sí, solo el andamiaje
de virtualización.

## Índice
1. [Arquitectura y mapeo de requisitos](#1-arquitectura-y-mapeo-de-requisitos)
2. [docker-compose.yaml](#2-docker-composeyaml)
3. [Patrón común de los runners (sshd endurecido)](#3-patrón-común-de-los-runners)
4. [bash-runner/Dockerfile](#4-bash-runnerdockerfile)
5. [c-runner/Dockerfile](#5-c-runnerdockerfile)
6. [ada-runner/Dockerfile](#6-ada-runnerdockerfile)
7. [manager/Dockerfile](#7-managerdockerfile)
8. [manager/app.py](#8-managerapppy)
9. [Caché y renderizado de métricas (en profundidad)](#9-caché-y-renderizado-de-métricas)

---

## 1. Arquitectura y mapeo de requisitos

Cuatro contenedores en una única stack de Docker Compose:

- **`manager`**: único con puerto publicado al host (`8080`). Cumple dos roles: (a) **cliente
  SSH** hacia los runners y (b) **panel web** de monitoreo con métricas reales.
- **`bash-runner` / `c-runner` / `ada-runner`**: cada uno encapsula una aplicación, corre un
  **servidor SSH** y **no publica puertos**. Solo son alcanzables por el manager por la red
  interna.

| Requisito de la consigna | Dónde se cumple |
|---|---|
| Exactamente 4 contenedores, un `docker compose up` | `docker-compose.yaml` |
| Imagen base mínima (fundamentada) | `FROM` de cada Dockerfile |
| Usuario no root (proceso principal) | `USER appuser` (runners y manager) |
| Sistema de archivos de solo lectura | `read_only: true` + `tmpfs` |
| Capabilities mínimas | `cap_drop: [ALL]` (sin `cap_add`) |
| Sin escalada de privilegios | `security_opt: [no-new-privileges:true]` |
| Puertos mínimos | runners sin `ports`; manager solo `8080` |
| SSH endurecido | claves + `PasswordAuthentication no` + `PermitRootLogin no` |
| Sin software innecesario | multi-stage (c, ada), `--no-install-recommends`, limpieza de cachés |
| Red interna | `networks.backend` con `internal: true` |
| Panel con métricas reales | `manager/app.py` + socket de Docker |

---

## 2. docker-compose.yaml

```yaml
services:
```
Bloque de servicios (contenedores). Cada clave es un servicio; su nombre es además el
**hostname** por el que lo resuelven los demás vía DNS interno de Compose.

### Servicio `bash-runner` (idéntico patrón en c-runner y ada-runner)

```yaml
  bash-runner:
    build: ./bash-runner
```
- **`build: ./bash-runner`**: construye la imagen a partir del `Dockerfile` en esa carpeta.
  El *contexto de build* es esa carpeta (solo sus archivos son visibles para `COPY`).

```yaml
    networks:
      - backend
```
- **`networks: [backend]`**: conecta el contenedor **solo** a la red `backend` (interna).
  → *Puertos mínimos / red interna*: sin salida a internet y solo alcanzable por el manager.

```yaml
    read_only: true
```
- **`read_only: true`**: monta el sistema de archivos raíz del contenedor como **solo
  lectura**. Un proceso comprometido no puede escribir binarios/malware ni persistir.
  → *Sistema de archivos de solo lectura*.

```yaml
    tmpfs:
      - /tmp
```
- **`tmpfs: [/tmp]`**: monta `/tmp` como un sistema de archivos en RAM (escribible y
  efímero). Es la única ruta escribible; permite `read_only` sin romper procesos que
  necesiten un scratch temporal.

```yaml
    cap_drop:
      - ALL
```
- **`cap_drop: [ALL]`**: elimina **todas** las Linux capabilities del contenedor. El sshd
  corre no-root en un puerto alto y no hace `setuid`, así que no necesita ninguna.
  → *Capabilities mínimas*.

```yaml
    security_opt:
      - no-new-privileges:true
```
- **`no-new-privileges:true`**: activa el flag del kernel `no_new_privs`. Ningún binario
  `setuid` puede otorgar privilegios adicionales tras un `execve`. → *Sin escalada de
  privilegios*.

### Servicio `manager` (diferencias)

```yaml
    networks:
      - backend
      - frontend
```
- El manager está en **dos** redes: `backend` (para hablar con los runners por SSH) y
  `frontend` (un puente normal, necesario para **publicar** el puerto al host, cosa que una
  red `internal` no permite).

```yaml
    ports:
      - "8080:8080"
```
- **`ports: ["8080:8080"]`**: publica el puerto `8080` del contenedor en el `8080` del host
  (`host:contenedor`). Es el único puerto expuesto de toda la stack. → *Puertos mínimos*.

```yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```
- Monta el **socket del daemon de Docker** dentro del manager. Es la fuente de las métricas
  reales (lo mismo que consulta `docker stats`).
- **`:ro`**: monta el archivo del socket como solo lectura. *Nota:* `:ro` protege el
  archivo, no la API detrás; es una buena práctica cosmética. Se acepta el tradeoff porque
  el manager es el único punto de entrada y solo publica `8080`.

### Sección `networks`

```yaml
networks:
  backend:
    internal: true
  frontend:
```
- **`backend.internal: true`**: red sin gateway al exterior. Los contenedores en ella **no
  pueden salir a internet** ni son accesibles desde el host. Verificado: un runner devuelve
  `Network unreachable` al intentar salir.
- **`frontend`** (sin opciones): puente bridge estándar; solo lo usa el manager para publicar
  `8080`.

---

## 3. Patrón común de los runners

Los tres runners comparten el mismo bloque de configuración de sshd. Se explica **una vez
en detalle** acá y en cada Dockerfile se remarca solo lo específico de esa imagen.

| Comando / flag | Qué hace | Por qué / requisito |
|---|---|---|
| `mkdir -p /run/sshd ...` | `-p`: crea directorios padres y no falla si existen | `sshd` exige que exista el dir de *privilege separation* |
| `ssh-keygen -t ed25519 -f <ruta> -N ""` | genera la **host key** del servidor. `-t ed25519`: tipo de clave (moderna, chica, segura); `-f`: archivo de salida; `-N ""`: passphrase vacía (arranque desatendido) | SSH endurecido; se usa una sola clave ed25519 (menos claves = menos superficie) |
| `sed -i 's/^appuser:!:/appuser:*:/' /etc/shadow` | `-i`: edita el archivo in-place; cambia el campo de contraseña de `!` (cuenta **bloqueada**) a `*` (sin contraseña válida pero **no** bloqueada) | Un `sshd` sin PAM rechaza cuentas bloqueadas; esto habilita el login por clave sin permitir login por contraseña |
| `echo 'Port 2222' >> sshd_config` | sshd escucha en el **2222** (puerto no privilegiado, ≥1024) | Un proceso **no-root** solo puede enlazar puertos ≥1024 → habilita `USER appuser` |
| `echo 'HostKey /etc/ssh/ssh_host_ed25519_key'` | usa la host key propia de appuser | Declarar una `HostKey` explícita evita que sshd use las claves root por defecto |
| `echo 'PidFile none'` | sshd no escribe archivo de PID | La ruta por defecto no es escribible bajo `read_only`; además así no escribe nada en runtime |
| `echo 'PasswordAuthentication no'` | deshabilita login por **contraseña** | SSH endurecido (solo claves) |
| `echo 'PubkeyAuthentication yes'` | habilita login por **clave pública** | SSH endurecido |
| `echo 'KbdInteractiveAuthentication no'` | cierra el otro camino de contraseña (interactivo) | SSH endurecido |
| `echo 'PermitRootLogin no'` | prohíbe login de root por SSH | SSH endurecido |
| `COPY manager_key.pub .../authorized_keys` | instala la clave pública del manager como **único** login permitido | SSH endurecido |
| `chmod 700 .ssh` / `chmod 600 authorized_keys` | permisos estrictos | `StrictModes` de sshd ignora las claves si los permisos son laxos |
| `chown appuser:appuser <host key>` | la host key pertenece al usuario que corre sshd | El sshd no-root debe poder leerla |
| `chown -R appuser:appuser /home/appuser` | ownership del home | `StrictModes` + acceso del usuario |
| `USER appuser` | fija el usuario del **proceso principal** | *Usuario no root* |
| `CMD ["/usr/sbin/sshd","-D"]` | arranca sshd. Forma *exec* (sin shell intermedio). `-D`: **no** se demoniza → queda como PID 1 en foreground y el contenedor no se apaga | El manager necesita el servidor SSH |

---

## 4. bash-runner/Dockerfile

```dockerfile
FROM alpine
```
- **Imagen base = Alpine** (~7 MB). El programa es un script bash interpretado: no requiere
  glibc, así que la imagen más liviana alcanza. → *Imagen base mínima*.

```dockerfile
RUN apk add --no-cache bash openssh && \
```
- **`apk add`**: instala paquetes (gestor de Alpine). **`bash`** (el script usa `#!/bin/bash`)
  y **`openssh`** (servidor SSH).
- **`--no-cache`**: no guarda el índice de paquetes en la imagen (sin `/var/cache/apk`) →
  imagen más chica, sin necesidad de `update`/`clean` por separado. → *Sin software innecesario*.
- *(No se instala `shadow`: al no setear contraseñas, el `adduser` de busybox alcanza.)*

Sigue el **bloque sshd común** (ver §3): `mkdir`, `ssh-keygen`, `adduser -D -h`, `sed` de
desbloqueo, y los `echo` de `sshd_config`. Nota específica de Alpine: **no** se agrega
`UsePAM no` porque el `sshd` de Alpine no tiene PAM (sería una opción no soportada).

```dockerfile
    adduser -D -h /home/appuser appuser && \
```
- **`adduser`** (busybox). **`-D`**: no asigna contraseña (crea la cuenta sin login por
  password). **`-h /home/appuser`**: directorio home. → *Usuario no root*.

```dockerfile
COPY manager_key.pub /home/appuser/.ssh/authorized_keys
COPY paddock_manager.sh /home/appuser/programa.sh
COPY inventario_f1.csv /home/appuser/inventario_f1.csv
COPY mercaderia /home/appuser/mercaderia
```
- Copia la clave pública (login), el script, y los **datos de prueba** que el script espera
  en su directorio de trabajo (`inventario_f1.csv` y la carpeta `mercaderia/`).

El resto (`chmod`, `chown`, `USER appuser`, `CMD`) es el patrón común de §3.

---

## 5. c-runner/Dockerfile

Imagen **multi-stage**: compila en una etapa y corre en otra. → *Sin software innecesario*
(el compilador no viaja a la imagen final).

```dockerfile
FROM gcc AS build
```
- **Etapa `build`** desde la imagen `gcc` (trae gcc, make, libc de desarrollo, etc.).
  **`AS build`** la nombra para referenciarla luego.

```dockerfile
COPY cocineros_mozos.c .
RUN gcc -pthread cocineros_mozos.c -o programa
```
- Compila el fuente C. **`-pthread`**: activa hilos POSIX en compilación *y* enlazado
  (define `_REENTRANT` y linkea el runtime de threads). Es la forma correcta y portable de
  compilar código con `pthread`/semáforos, independiente de que glibc ≥ 2.34 tenga pthread
  integrado en libc. **`-o programa`**: nombre del ejecutable de salida.

```dockerfile
FROM debian:bookworm-slim
```
- **Runtime = `debian:bookworm-slim`**. El binario está enlazado contra **glibc**; correrlo
  sobre Alpine (musl) lo rompería. Debian slim es la base glibc mínima. → *Imagen base mínima*
  fundamentada.

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server && \
    rm -rf /var/lib/apt/lists/* && \
```
- **`apt-get update`**: refresca el índice de paquetes. **`install -y`**: `-y` asume "sí".
  **`--no-install-recommends`**: no instala paquetes "recomendados" (no imprescindibles) →
  menos software. **`rm -rf /var/lib/apt/lists/*`**: borra el índice descargado → imagen más
  chica. → *Sin software innecesario / imagen mínima*.

```dockerfile
    rm -f /etc/ssh/ssh_host_* && \
```
- **Específico de Debian/Ubuntu**: el paquete `openssh-server` **genera host keys** en su
  post-instalación. Se borran para que el `ssh-keygen -f` siguiente no encuentre el archivo
  ya existente y pida confirmación (fallaría sin terminal). *(Alpine no las genera, por eso
  bash-runner no lo necesita.)*

```dockerfile
    useradd -m -d /home/appuser -s /bin/bash appuser && \
```
- **`useradd`** (Debian). **`-m`**: crea el home. **`-d`**: ruta del home. **`-s /bin/bash`**:
  shell de login. → *Usuario no root*.

```dockerfile
    sed -i '/^UsePAM/d' /etc/ssh/sshd_config && \
```
- **Específico de Debian/Ubuntu**: el `sshd_config` de fábrica trae `UsePAM yes` **sin
  comentar**. Como en `sshd_config` **gana la primera aparición** de cada opción, nuestro
  `UsePAM no` agregado al final sería ignorado. Este `sed` **borra** la línea de fábrica para
  que gane la nuestra. (Sin esto, PAM queda activo y rechaza la sesión bajo el endurecimiento.)

```dockerfile
COPY --from=build programa /home/appuser/programa
```
- **`COPY --from=build`**: trae el **binario compilado** desde la etapa `build`. El
  compilador nunca llega a la imagen final. → *Sin software innecesario*.

Resto: `chmod`/`chown`/`USER`/`CMD` del patrón común (§3).

---

## 6. ada-runner/Dockerfile

También **multi-stage**, análogo a c-runner (misma razón: sacar el toolchain del runtime;
imagen 525 MB → 149 MB).

```dockerfile
FROM debian:bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends gnat && \
    rm -rf /var/lib/apt/lists/*
COPY main.adb .
RUN gnatmake main.adb -o programa
```
- **Etapa build** sobre `debian:bookworm` (no slim, porque necesita el compilador).
  **`gnat`**: compilador de Ada. **`gnatmake main.adb -o programa`**: `gnatmake` compila,
  hace el *bind* y el *link* del programa Ada en un paso; **`-o programa`** nombra el
  ejecutable.

```dockerfile
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server libgnat-12 && \
```
- **Runtime = `debian:bookworm-slim`** (misma distro que build → mismas versiones de glibc y
  de las libs de Ada; mezclar Ubuntu→Debian arriesga `GLIBC_x not found`).
- **`libgnat-12`**: paquete del **runtime de Ada** (aporta `libgnat-12.so` y `libgnarl-12.so`,
  este último es el runtime de *tasking* que usa el juego). Es la librería, **no** el
  compilador. → *Imagen mínima + sin software innecesario*, sin dejar de ser funcional.
- *(Se descartó el enlazado estático total: el gnat de estos repos no trae las libs `.a`.)*

El resto del bloque sshd y el `COPY --from=build programa` son idénticos a c-runner.

---

## 7. manager/Dockerfile

```dockerfile
FROM python:3.12-alpine
```
- **Base = `python:3.12-alpine`**: Python mínimo. El panel se sirve con la biblioteca
  estándar (sin framework), así que no hace falta más. → *Imagen base mínima*.

```dockerfile
RUN apk add --no-cache openssh-client && \
    adduser -D -h /home/appuser appuser && \
    addgroup appuser root && \
    mkdir -p /home/appuser/.ssh
```
- **`openssh-client`**: cliente SSH para que un operador ejecute las apps por SSH desde el
  manager. (Ya **no** se instala `sshpass`: la autenticación es por clave.)
- **`adduser -D -h`**: crea el usuario no root. → *Usuario no root*.
- **`addgroup appuser root`**: agrega `appuser` al **grupo root**. El socket de Docker es
  `root:root` (modo 660); estar en el grupo root permite leerlo **sin ser root**. Se hace en
  *build* (no en runtime) para no escribir `/etc/group` en ejecución → compatible con
  `read_only`. (En un host con grupo `docker` propio, se cambiaría `root` por ese grupo.)

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- Instala dependencias Python desde `requirements.txt` (una sola: el SDK `docker`).
- **`--no-cache-dir`**: pip no guarda la caché de descargas → imagen más chica.
- **`-r requirements.txt`**: instala desde el archivo de requisitos.

```dockerfile
COPY manager_key /home/appuser/.ssh/id_ed25519
COPY app.py /app.py
RUN chmod 700 /home/appuser/.ssh && \
    chmod 600 /home/appuser/.ssh/id_ed25519 && \
    chown -R appuser:appuser /home/appuser
```
- Copia la **clave privada** (para conectarse a los runners) y la app. **`chmod 600`** en la
  clave: ssh rechaza claves privadas legibles por otros.

```dockerfile
ENV HOME=/home/appuser
ENV PYTHONDONTWRITEBYTECODE=1
```
- **`HOME`**: para que ssh y demás encuentren el home de appuser.
- **`PYTHONDONTWRITEBYTECODE=1`**: Python no escribe archivos `.pyc` → evita intentos de
  escritura bajo `read_only`.

```dockerfile
USER appuser
CMD ["python","/app.py"]
```
- **`USER appuser`**: el proceso principal (Python) corre no-root. → *Usuario no root*.
- **`CMD`**: arranca el servidor. (No hay entrypoint ni `su-exec`: al estar appuser en el
  grupo del socket, no hay que bajar privilegios desde root.)

---

## 8. manager/app.py

**Tecnologías usadas:**
- **`http.server`** (biblioteca estándar de Python): servidor HTTP **sin framework**
  (`ThreadingHTTPServer` + `BaseHTTPRequestHandler`).
- **`docker` (SDK de Docker para Python)**: habla con la API del daemon de Docker a través
  del socket montado. Es lo que provee las estadísticas reales.
- **`threading` + `concurrent.futures`**: un thread de fondo y un pool para paralelizar.
- **Frontend**: HTML + CSS + JavaScript *vanilla* (`fetch` + `setInterval`), sin framework JS.

### Imports y estado a nivel de módulo

```python
import concurrent.futures, json, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import docker
from docker.errors import DockerException
```
Módulos estándar + el SDK de Docker.

```python
docker_client = docker.from_env()
```
- **`docker.from_env()`**: crea el cliente leyendo el entorno; por defecto usa
  `/var/run/docker.sock` (el socket montado). Es la conexión a la API del daemon.

```python
SSH_KEY = "/home/appuser/.ssh/id_ed25519"
SSH_PORT = "2222"
RUNNERS = [ {name, host, user, command}, ... ]
MONITORED = [{"name": "manager", "host": "manager"}] + RUNNERS
```
- `RUNNERS`: datos de acceso SSH, usados para **documentar** el comando en el panel (la
  ejecución es interactiva, no por web). `MONITORED`: la lista que se monitorea = manager +
  los tres runners.

```python
_cache_lock = threading.Lock()
_cache = [ {name, host, "status": "cargando", cpu/mem: None} for t in MONITORED ]
```
- **`_cache`**: lista en memoria con la última foto de métricas. Se inicializa en estado
  `"cargando"` para que la tabla muestre los nombres de inmediato.
- **`_cache_lock`**: candado que serializa lecturas/escrituras de `_cache` entre threads.

### `find_container(service)`
Resuelve el objeto contenedor de un servicio.
```python
docker_client.containers.list(all=True, filters={"label": f"com.docker.compose.service={service}"})
```
- **`.containers.list(...)`**: lista contenedores vía la API. **`all=True`**: incluye los
  detenidos (para poder reportar "inactivo"). **`filters={label...}`**: filtra por el label
  que Compose pone en cada contenedor. Se busca por **label** y no por nombre porque Compose
  antepone el prefijo del proyecto al nombre real. Devuelve el primero o `None`.

### `compute_cpu_percent(stats)` — cálculo de CPU
La API de Docker no da un porcentaje: da **contadores acumulados**. El porcentaje se calcula
con la variación entre dos lecturas (idéntico a `docker stats`):
```python
cpu_delta    = cpu["cpu_usage"]["total_usage"] - precpu["cpu_usage"]["total_usage"]
system_delta = cpu["system_cpu_usage"]         - precpu["system_cpu_usage"]
online       = cpu["online_cpus"] (o len(percpu_usage))
cpu% = (cpu_delta / system_delta) * online * 100
```
- **`cpu_delta`**: nanosegundos de CPU que consumió el contenedor entre las dos muestras.
- **`system_delta`**: tiempo total de CPU del sistema (todos los núcleos) en ese intervalo.
- El cociente es la fracción del sistema que usó el contenedor; se escala por **`online`**
  (núcleos) para llevarlo a la escala "100% = un núcleo". El objeto `stats` trae la lectura
  actual (`cpu_stats`) y la anterior (`precpu_stats`), por eso se puede sacar el delta.
- **Guardas**: si algún delta es ≤ 0 (primera lectura) devuelve `0.0`, evitando división por
  cero. `try/except (KeyError, TypeError)` tolera un stats incompleto.

### `compute_memory(stats)` — cálculo de memoria
```python
usage = mem["usage"]
cache = mem["stats"].get("inactive_file", "total_inactive_file")
used  = usage - cache
percent = used / mem["limit"] * 100
```
- **`usage`**: memoria usada, incluyendo el *page cache*. Se le **resta el cache de página**
  reclamable (`inactive_file` en cgroup v2 / `total_inactive_file` en v1) para reflejar el
  uso "real", igual que `docker stats`. Devuelve MB usados, MB límite y porcentaje.

### `get_metrics(target)`
Arma el diccionario de métricas de **un** contenedor: resuelve el contenedor, si no existe
→ `"no encontrado"`; si no está `running` → devuelve el estado sin métricas; si está
corriendo, pide `container.stats(stream=False)` y calcula CPU/memoria.
- **`stats(stream=False)`**: pide **una** foto de estadísticas (no un stream continuo).

### `collect_loop()` — el recolector de fondo (clave, ver §9)
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=len(MONITORED)) as pool:
    while True:
        results = list(pool.map(get_metrics, MONITORED))
        with _cache_lock:
            _cache[:] = results
        time.sleep(1)
```
- Corre en un thread aparte y **refresca `_cache` continuamente**.
- **`ThreadPoolExecutor` + `pool.map`**: ejecuta `get_metrics` de los 4 contenedores **en
  paralelo** (son llamadas I/O-bound que esperan al daemon), así un ciclo dura ~lo de una
  sola consulta y no la suma.
- **`_cache[:] = results`**: reemplaza el **contenido** de la lista in-place, bajo el candado,
  para que un lector nunca vea una lista a medio actualizar.

### `render_page()`
Arma el HTML: por cada runner genera el comando `docker compose exec ... ssh -t ...` de
acceso y lo inyecta en el placeholder `__SSH_HINTS__` de `PAGE` con `str.replace`.

### `class Handler(BaseHTTPRequestHandler)` — servidor HTTP
- **`do_GET`**: enruta por `self.path`:
  - `/` → devuelve el HTML (`render_page()`).
  - `/metrics` → serializa `_cache` a JSON **bajo el candado** y lo devuelve. Es instantáneo
    (no consulta el daemon en el request).
  - cualquier otra → `404`.
- **`_send(status, content_type, body)`**: helper que escribe status, headers
  (`Content-Type`, `Content-Length`) y el cuerpo.
- **`log_message`**: se sobrescribe con `pass` para **silenciar** el log por request (el panel
  hace polling y sería ruido).

### `PAGE` (HTML + CSS + JS)
Constante con la página. Incluye la tabla, el placeholder de comandos SSH, y el script que
consulta `/metrics` (ver §9). El CSS aplica un tema oscuro y colorea el estado (verde/rojo).

### Arranque
```python
if __name__ == "__main__":
    threading.Thread(target=collect_loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()
```
- Lanza el **recolector** como thread **daemon** (muere con el proceso).
- **`ThreadingHTTPServer`**: atiende cada request en su propio thread (por eso hace falta el
  candado de `_cache`). Escucha en `0.0.0.0:8080` y `serve_forever()` bloquea sirviendo.

---

## 9. Caché y renderizado de métricas

Esta es la parte medular del panel. El problema y la solución, en detalle:

### El problema
Leer estadísticas de un contenedor (`container.stats(stream=False)`) **es lento**: el daemon
muestrea durante ~1 s para poder calcular el delta de CPU, así que cada llamada bloquea
~1–4 s. Hacer las 4 llamadas **en cada request HTTP** daría respuestas de ~4–17 s; con el
navegador consultando cada 1 s, los pedidos se apilarían y la tabla nunca cargaría.

### La solución: recolector de fondo + caché en memoria
1. **Un thread de fondo (`collect_loop`)** consulta a los 4 contenedores **en paralelo**
   (`ThreadPoolExecutor`) y guarda el resultado en la lista compartida `_cache`. Un ciclo
   dura ~4–5 s; entre ciclos duerme 1 s.
2. **El endpoint `/metrics`** simplemente devuelve `_cache` serializada a JSON — **al
   instante**, sin tocar el daemon en el camino del request.
3. **Sincronización**: `ThreadingHTTPServer` atiende cada request en un thread distinto, y el
   recolector escribe desde otro. Un `threading.Lock` (`_cache_lock`) protege tanto la lectura
   (`json.dumps(_cache)`) como la escritura (`_cache[:] = results`), garantizando que el
   cliente nunca reciba una foto a medio actualizar.
4. **Arranque suave**: `_cache` empieza con estado `"cargando"`, así la tabla muestra los
   nombres de inmediato y se llena con datos reales tras el primer ciclo.

### El renderizado (front-end)
```javascript
async function cargarMetricas() {
  const resp  = await fetch('/metrics');   // pide el JSON cacheado
  const items = await resp.json();
  document.getElementById('filas').innerHTML = items.map(r => {
     ... arma un <tr> con nombre, estado (clase css running/down), CPU %, memoria ...
  }).join('');
}
cargarMetricas();
setInterval(cargarMetricas, 1000);         // repite cada 1 s
```
- **`fetch('/metrics')`**: pide el JSON al servidor (asíncrono).
- **`.map(...).join('')`**: transforma cada objeto de métrica en una fila `<tr>` (con *template
  literals*) y las concatena en el `<tbody>`.
- **`setInterval(..., 1000)`**: repite cada 1 s. Como `/metrics` responde desde la caché, el
  polling es barato; la sensación es de tiempo real aunque los datos reales se refresquen cada
  ~4–5 s por el ciclo del recolector.
- Si el `fetch` falla, el `catch` muestra "Error al leer metricas".

### Flujo completo de una métrica
```
daemon de Docker  ──stats──▶  collect_loop (thread, en paralelo)  ──escribe──▶  _cache
                                                                                   │
navegador ──GET /metrics──▶ Handler.do_GET ──lee bajo lock──▶ json.dumps(_cache) ─▶ JSON
   ▲                                                                                │
   └────────────── setInterval 1s / fetch / render tabla ◀──────────────────────────┘
```

Esto satisface el requisito de **"panel web con información real de los contenedores"**: los
números provienen del daemon (los mismos que `docker stats`), no son simulados.
