from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>Manager</h1>

    <ul>
        <li>Bash Runner</li>
        <li>C Runner</li>
        <li>Ada Runner</li>
    </ul>
    """

app.run(host="0.0.0.0", port=8080)