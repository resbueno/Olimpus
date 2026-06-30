#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
ROOT="$DIR"
LOG="$ROOT/iris_erro.log"

PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo "[ERRO] Python nao encontrado no PATH." >> "$LOG"
        exit 1
    fi
fi

if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    $PYTHON_CMD -m ensurepip --upgrade &> /dev/null
fi

if ! $PYTHON_CMD -c "import flask, flask_cors" &> /dev/null; then
    $PYTHON_CMD -m pip install -r "$ROOT/requirements.txt" --quiet --disable-pip-version-check &> /dev/null
fi

if [ ! -f "$ROOT/app.py" ]; then
    echo "[ERRO] app.py nao encontrado." >> "$LOG"
    exit 1
fi

PORT_PID=$(lsof -t -i :5070)
if [ ! -z "$PORT_PID" ]; then
    kill -9 $PORT_PID &> /dev/null
fi

nohup $PYTHON_CMD "$ROOT/app.py" > /dev/null 2>&1 &

TRIES=0
while true; do
    sleep 1
    $PYTHON_CMD -c "import urllib.request; urllib.request.urlopen('http://localhost:5070/api/ping', timeout=2)" &> /dev/null
    if [ $? -eq 0 ]; then break; fi
    TRIES=$((TRIES + 1))
    if [ $TRIES -ge 20 ]; then
        echo "[ERRO] Servidor nao respondeu apos 20 tentativas." >> "$LOG"
        exit 1
    fi
done
exit 0
