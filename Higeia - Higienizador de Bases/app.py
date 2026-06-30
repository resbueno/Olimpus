"""Higeia – servidor mínimo Flask que serve higeia.html."""
import os
from flask import Flask, send_from_directory, jsonify

BASE = os.path.dirname(os.path.abspath(__file__))
app  = Flask(__name__, static_folder=BASE)


@app.route("/")
def index():
    return send_from_directory(BASE, "higeia.html")


@app.route("/api/ping")
def ping():
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("HIGEIA_PORT", 8501))
    host = os.environ.get("HIGEIA_HOST", "127.0.0.1")
    print(f"\n HIGEIA rodando em http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, threaded=True)
