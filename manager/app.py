import subprocess

from flask import Flask, jsonify, request

app = Flask(__name__)

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


@app.route("/")
def home():
    buttons = "".join(
        f'<form action="/run" method="post" style="margin: 8px 0;">'
        f'<input type="hidden" name="runner" value="{runner["host"]}">'
        f'<button type="submit">Ejecutar {runner["name"]}</button>'
        f'</form>'
        for runner in RUNNERS
    )
    return f"""
    <h1>Manager</h1>
    <p>Seleccione un runner para ejecutarlo:</p>
    {buttons}
    """


@app.route("/run", methods=["POST"])
def run_selected():
    runner_name = request.form.get("runner", "")
    selected_runner = next((runner for runner in RUNNERS if runner["host"] == runner_name), None)

    if not selected_runner:
        return jsonify({"error": "Runner no encontrado"}), 400

    result = run_remote_command(
        host=selected_runner["host"],
        user=selected_runner["user"],
        password=selected_runner["password"],
        command=selected_runner["command"],
    )
    return jsonify({"result": result})


app.run(host="0.0.0.0", port=8080)