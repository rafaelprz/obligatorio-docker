import subprocess

import docker
from docker.errors import DockerException
from flask import Flask, jsonify, request

app = Flask(__name__)

# Cliente del daemon de Docker (lee el socket montado en el contenedor).
docker_client = docker.from_env()

RUNNERS = [
    {
        "name": "bash-runner",
        "host": "bash-runner",
        "user": "appuser",
        "password": "app123",
        "command": "/home/appuser/programa.sh",
    },
    {
        "name": "c-runner",
        "host": "c-runner",
        "user": "appuser",
        "password": "app123",
        "command": "/home/appuser/programa",
    },
    {
        "name": "ada-runner",
        "host": "ada-runner",
        "user": "appuser",
        "password": "app123",
        "command": "/home/appuser/programa",
    },
]


# ---------------------------------------------------------------------------
# Ejecucion remota via SSH
# ---------------------------------------------------------------------------

def run_remote_command(host, user, password, command):
    ssh_args = [
        "sshpass",
        "-p",
        password,
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=5",
        f"{user}@{host}",
        command,
    ]
    completed = subprocess.run(ssh_args, capture_output=True, text=True, timeout=15)
    return {
        "host": host,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


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
        "executable": target.get("executable", False),
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


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

@app.route("/metrics")
def metrics():
    # El manager tambien se monitorea (metricas), pero no es ejecutable.
    monitored = [{"name": "manager", "host": "manager"}]
    monitored += [{**runner, "executable": True} for runner in RUNNERS]
    return jsonify([get_metrics(target) for target in monitored])


@app.route("/run", methods=["POST"])
def run_selected():
    runner_name = request.form.get("runner", "")
    selected_runner = next((r for r in RUNNERS if r["host"] == runner_name), None)

    if not selected_runner:
        return jsonify({"error": "Runner no encontrado"}), 400

    result = run_remote_command(
        host=selected_runner["host"],
        user=selected_runner["user"],
        password=selected_runner["password"],
        command=selected_runner["command"],
    )
    return jsonify({"result": result})


@app.route("/")
def home():
    return PAGE


PAGE = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Manager - Panel de runners</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; }
    h1 { margin-bottom: 0.25rem; }
    .sub { color: #666; margin-top: 0; }
    table { border-collapse: collapse; width: 100%; max-width: 900px; margin-top: 1rem; }
    th, td { border: 1px solid #ccc; padding: 8px 10px; text-align: left; }
    th { background: #f2f2f2; }
    .estado { font-weight: 600; }
    .running { color: #157347; }
    .down { color: #b02a37; }
    button { cursor: pointer; padding: 4px 10px; }
    pre { background: #111; color: #eee; padding: 12px; border-radius: 6px;
          max-width: 900px; overflow-x: auto; white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>Manager</h1>
  <p class="sub">Estado y metricas en vivo (se actualiza cada 3 s).</p>

  <table>
    <thead>
      <tr>
        <th>Runner</th><th>Estado</th><th>CPU %</th>
        <th>Memoria</th><th>Accion</th>
      </tr>
    </thead>
    <tbody id="filas">
      <tr><td colspan="5">Cargando...</td></tr>
    </tbody>
  </table>

  <h2>Salida</h2>
  <pre id="salida">(sin ejecuciones todavia)</pre>

  <script>
    async function cargarMetricas() {
      try {
        const resp = await fetch('/metrics');
        const runners = await resp.json();
        document.getElementById('filas').innerHTML = runners.map(r => {
          const activo = r.status === 'running';
          const cpu = r.cpu_percent === null ? '-' : r.cpu_percent + ' %';
          const mem = r.mem_used_mb === null
            ? '-'
            : `${r.mem_used_mb} MB (${r.mem_percent} %)`;
          const accion = r.executable
            ? `<button onclick="ejecutar('${r.host}')">Ejecutar</button>`
            : '-';
          return `<tr>
            <td>${r.name}</td>
            <td class="estado ${activo ? 'running' : 'down'}">${r.status}</td>
            <td>${cpu}</td>
            <td>${mem}</td>
            <td>${accion}</td>
          </tr>`;
        }).join('');
      } catch (e) {
        document.getElementById('filas').innerHTML =
          '<tr><td colspan="5">Error al leer metricas</td></tr>';
      }
    }

    async function ejecutar(host) {
      const salida = document.getElementById('salida');
      salida.textContent = 'Ejecutando en ' + host + '...';
      try {
        const body = new URLSearchParams({ runner: host });
        const resp = await fetch('/run', { method: 'POST', body });
        const data = await resp.json();
        salida.textContent = JSON.stringify(data.result ?? data, null, 2);
      } catch (e) {
        salida.textContent = 'Error al ejecutar en ' + host;
      }
    }

    cargarMetricas();
    setInterval(cargarMetricas, 3000);
  </script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
