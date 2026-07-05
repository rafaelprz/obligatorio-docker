# Obligatorio Parte 4 — Virtualización

Cuatro contenedores Docker orquestados con Docker Compose: un **manager** (cliente SSH +
panel web de monitoreo) y tres **runners** aislados (Bash, C y ADA), cada uno con su
aplicación y un servidor SSH, endurecidos bajo criterios de mínima superficie y mínima
vulnerabilidad.

```
navegador → manager:8080 (panel de métricas)
                 │
     SSH (clave, puerto 2222, red interna)
      ┌──────────┼──────────┐
 bash-runner  c-runner  ada-runner
```

## Requisitos previos

- **Docker Desktop** (Windows/macOS) o **Docker Engine + Docker Compose v2** (Linux),
  con el daemon corriendo.
- No hace falta nada más: las claves SSH internas ya vienen en el repo y las imágenes se
  construyen solas.

## Levantar la solución (un solo comando)

Desde la raíz del proyecto:

```bash
docker compose up --build
```

Esto construye las cuatro imágenes, crea las redes y arranca los contenedores.

> **Nota:** `up` (sin `-d`) queda **en primer plano** mostrando los logs. Como el `sshd` de
> los runners no imprime nada al arrancar bien y el manager silencia el log por request, la
> terminal **parece congelada pero está funcionando**. Para recuperar la terminal, usá:
>
> ```bash
> docker compose up --build -d      # modo desacoplado (background)
> docker compose logs -f            # seguir los logs si hace falta
> ```

## Usar el sistema

### 1. Panel web de monitoreo

Abrir en el navegador:

```
http://localhost:8080
```

Muestra, en vivo (actualiza cada 1 s), el **estado**, **CPU %** y **memoria** de los cuatro
contenedores, más el comando SSH listo para copiar de cada runner.

### 2. Ejecutar las aplicaciones (SSH interactivo desde el manager)

Las apps se ejecutan por SSH desde el manager (no desde la web). El panel lista estos
comandos; también están acá:

```bash
# Bash (Parte 1) — recibe acción + parámetro, p. ej. "buscar Ferrari"
docker compose exec -it manager ssh -t -i /home/appuser/.ssh/id_ed25519 -p 2222 \
  -o StrictHostKeyChecking=no appuser@bash-runner /home/appuser/programa.sh buscar Ferrari

# C (Parte 2) — hilos POSIX; termina solo (~20-30 s)
docker compose exec -it manager ssh -t -i /home/appuser/.ssh/id_ed25519 -p 2222 \
  -o StrictHostKeyChecking=no appuser@c-runner /home/appuser/programa

# ADA (Parte 3) — juego interactivo en terminal; se controla con A / D / W (Ctrl-C para salir)
docker compose exec -it manager ssh -t -i /home/appuser/.ssh/id_ed25519 -p 2222 \
  -o StrictHostKeyChecking=no appuser@ada-runner /home/appuser/programa
```

## Detener

- **Ctrl+C** en la terminal en primer plano detiene la stack.
- Para eliminar contenedores y redes:

```bash
docker compose down
```

## Estructura del repositorio

```
docker-compose.yaml     Orquestación, redes y endurecimiento de los 4 servicios
bash-runner/            App Bash + Dockerfile (Alpine)
c-runner/               App C + Dockerfile (multi-stage gcc → debian-slim)
ada-runner/             App ADA + Dockerfile (multi-stage debian+gnat → debian-slim)
manager/                Panel + cliente SSH (Python stdlib + SDK de Docker)
informe.md              Informe técnico (explicación línea por línea)
DECISIONES.md           Bitácora de decisiones de diseño
```

## Notas

- Los runners **no publican puertos** al host y están en una red **interna sin salida a
  internet**; solo el manager los alcanza (por la red `backend`) y solo el manager expone el
  puerto `8080` (por la red `frontend`).
- El login SSH es **solo por clave** (sin contraseña, sin root); todos los procesos
  principales corren **sin privilegios de root**.
- Detalle completo de cada comando y flag en `informe.md`; justificación de cada decisión en
  `DECISIONES.md`.
