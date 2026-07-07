import json
from http.server import BaseHTTPRequestHandler, HTTPServer

import docker
from docker.errors import DockerException

# Cliente del daemon de Docker (lee el socket montado en el contenedor).
docker_client = docker.from_env()

# Datos de acceso SSH a los runners (para documentar el comando en el panel).
# La ejecucion de las apps es interactiva por SSH desde el manager, no por web.
SSH_KEY = "/home/appuser/.ssh/id_ed25519"
SSH_PORT = "2222"

RUNNERS = [
    {
        "name": "bash-runner",
        "host": "bash-runner",
        "user": "appuser",
        "command": "/home/appuser/programa.sh buscar Ferrari",
    },
    {
        "name": "c-runner",
        "host": "c-runner",
        "user": "appuser",
        "command": "/home/appuser/programa",
    },
    {
        "name": "ada-runner",
        "host": "ada-runner",
        "user": "appuser",
        "command": "/home/appuser/programa",
    },
]

# Contenedores monitoreados: el manager y los tres runners.
MONITORED = [{"name": "manager", "host": "manager"}] + RUNNERS


# ---------------------------------------------------------------------------
# Metricas reales via daemon de Docker
# ---------------------------------------------------------------------------

def find_container(service):
    # Compose nombra los contenedores con prefijo de proyecto, asi que no se
    # pueden buscar por nombre de servicio; se resuelven por su label de Compose.
    containers = docker_client.containers.list(
        all=True,
        filters={"label": f"com.docker.compose.service={service}"},
    )
    return containers[0] if containers else None


def compute_cpu_percent(stats):
    # Misma formula que usa `docker stats`: variacion de uso del contenedor
    # sobre variacion de uso total del sistema, escalada por nucleos.
    try:
        cpu = stats["cpu_stats"]
        precpu = stats["precpu_stats"]
        cpu_delta = cpu["cpu_usage"]["total_usage"] - precpu["cpu_usage"]["total_usage"]
        system_delta = cpu["system_cpu_usage"] - precpu.get("system_cpu_usage", 0)
        online = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage") or [])
        if cpu_delta > 0 and system_delta > 0 and online > 0:
            return round((cpu_delta / system_delta) * online * 100, 2)
    except (KeyError, TypeError):
        pass
    return 0.0


def compute_memory(stats):
    # Se descuenta el cache de pagina para reflejar el uso "real", igual que docker stats.
    try:
        mem = stats["memory_stats"]
        usage = mem.get("usage", 0)
        detail = mem.get("stats", {})
        cache = detail.get("inactive_file", detail.get("total_inactive_file", 0))
        used = usage - cache if usage > cache else usage
        limit = mem.get("limit", 0) or 0
        used_mb = round(used / (1024 * 1024), 1)
        limit_mb = round(limit / (1024 * 1024), 1) if limit else 0.0
        percent = round(used / limit * 100, 2) if limit else 0.0
        return used_mb, limit_mb, percent
    except (KeyError, TypeError):
        return 0.0, 0.0, 0.0


def get_metrics(target):
    result = {
        "name": target["name"],
        "host": target["host"],
        "status": "inactivo",
        "cpu_percent": None,
        "mem_used_mb": None,
        "mem_limit_mb": None,
        "mem_percent": None,
    }

    container = find_container(target["host"])
    if container is None:
        result["status"] = "no encontrado"
        return result

    result["status"] = container.status
    if container.status != "running":
        return result

    try:
        stats = container.stats(stream=False)
    except DockerException:
        result["status"] = "error metricas"
        return result

    used_mb, limit_mb, mem_percent = compute_memory(stats)
    result["cpu_percent"] = compute_cpu_percent(stats)
    result["mem_used_mb"] = used_mb
    result["mem_limit_mb"] = limit_mb
    result["mem_percent"] = mem_percent
    return result


def render_page():
    hints = []
    for runner in RUNNERS:
        cmd = (
            f"docker compose exec -it manager ssh -t -i {SSH_KEY} "
            f"-p {SSH_PORT} -o StrictHostKeyChecking=no "
            f"{runner['user']}@{runner['host']} {runner['command']}"
        )
        hints.append(f"<li><strong>{runner['name']}</strong><pre>{cmd}</pre></li>")
    return PAGE.replace("__SSH_HINTS__", "".join(hints))


# ---------------------------------------------------------------------------
# Servidor HTTP (biblioteca estandar, sin framework)
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self._send(200, "text/html; charset=utf-8", render_page().encode("utf-8"))
        elif self.path == "/metrics":
            # Se consultan los contenedores en el momento (sin cache): es lento
            # (~varios segundos) pero simple.
            data = [get_metrics(target) for target in MONITORED]
            self._send(200, "application/json", json.dumps(data).encode("utf-8"))
        else:
            self._send(404, "text/plain; charset=utf-8", b"Not Found")

    def _send(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # silencia el log por request


PAGE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Manager - Panel de monitoreo</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem;
           background: #14171c; color: #e6e6e6; }
    h1 { margin-bottom: 0.25rem; }
    h2 { margin-top: 1.5rem; }
    .sub { color: #9aa0a6; margin-top: 0; }
    table { border-collapse: collapse; width: 100%; max-width: 800px; margin-top: 1rem; }
    th, td { border: 1px solid #333a44; padding: 8px 10px; text-align: left; }
    th { background: #1e232b; }
    .estado { font-weight: 600; }
    .running { color: #4ade80; }
    .down { color: #f87171; }
    ul.ssh { list-style: none; padding: 0; max-width: 800px; }
    ul.ssh li { margin: 10px 0; }
    pre { background: #0d1117; color: #e6edf3; padding: 12px; border-radius: 6px;
          border: 1px solid #333a44; overflow-x: auto; white-space: pre; }
  </style>
</head>
<body>
  <h1>Manager</h1>
  <p class="sub">Monitoreo de los contenedores (la consulta tarda unos segundos).</p>

  <table>
    <thead>
      <tr><th>Contenedor</th><th>Estado</th><th>CPU %</th><th>Memoria</th></tr>
    </thead>
    <tbody id="filas">
      <tr><td colspan="4">Cargando...</td></tr>
    </tbody>
  </table>

  <h2>Acceso SSH (ejecutar las apps)</h2>
  <p class="sub">La ejecucion es interactiva por SSH desde el manager. Comandos:</p>
  <ul class="ssh">__SSH_HINTS__</ul>

  <script>
    async function cargarMetricas() {
      try {
        const resp = await fetch('/metrics');
        const items = await resp.json();
        document.getElementById('filas').innerHTML = items.map(r => {
          const activo = r.status === 'running';
          const cpu = r.cpu_percent === null ? '-' : r.cpu_percent + ' %';
          const mem = r.mem_used_mb === null
            ? '-'
            : `${r.mem_used_mb} MB (${r.mem_percent} %)`;
          return `<tr>
            <td>${r.name}</td>
            <td class="estado ${activo ? 'running' : 'down'}">${r.status}</td>
            <td>${cpu}</td>
            <td>${mem}</td>
          </tr>`;
        }).join('');
      } catch (e) {
        document.getElementById('filas').innerHTML =
          '<tr><td colspan="4">Error al leer metricas</td></tr>';
      } finally {
        // Se agenda la proxima recarga 2s despues de terminar (sin apilar pedidos).
        setTimeout(cargarMetricas, 2000);
      }
    }

    cargarMetricas();
  </script>
</body>
</html>"""


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
