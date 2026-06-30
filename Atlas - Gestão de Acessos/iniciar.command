#!/bin/bash

# Define o diretório de trabalho para a pasta do script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

ROOT="$DIR"
LOG="$ROOT/atlas_erro.log"

# ── Python ────────────────────────────────────────────────
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo "[ERRO] Python nao encontrado no PATH." >> "$LOG"
        echo "Erro: Python não encontrado."
        exit 1
    fi
fi

# ── pip ───────────────────────────────────────────────────
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    $PYTHON_CMD -m ensurepip --upgrade &> /dev/null
fi

# ── Dependencias ──────────────────────────────────────────
if ! $PYTHON_CMD -c "import flask, flask_cors" &> /dev/null; then
    if [ -f "$ROOT/requirements.txt" ]; then
        $PYTHON_CMD -m pip install -r "$ROOT/requirements.txt" --quiet --disable-pip-version-check &> /dev/null
        if [ $? -ne 0 ]; then
            echo "[ERRO] Falha ao instalar dependencias." >> "$LOG"
            echo "Erro: Falha ao instalar dependências do requirements.txt."
            exit 1
        fi
    else
        $PYTHON_CMD -m pip install flask flask-cors --quiet --disable-pip-version-check &> /dev/null
        if [ $? -ne 0 ]; then
            echo "[ERRO] Falha ao instalar dependencias." >> "$LOG"
            echo "Erro: Falha ao instalar Flask/Flask-Cors."
            exit 1
        fi
    fi
fi

if [ ! -f "$ROOT/app.py" ]; then
    echo "[ERRO] app.py nao encontrado." >> "$LOG"
    echo "Erro: app.py do Atlas não encontrado."
    exit 1
fi

# ── Mata porta 5010 ───────────────────────────────────────
PORT_PID=$(lsof -t -i :5010)
if [ ! -z "$PORT_PID" ]; then
    echo "Liberando a porta 5010 (PID: $PORT_PID)..."
    kill -9 $PORT_PID &> /dev/null
fi

# ── Sobe servidor oculto ──────────────────────────────────
nohup $PYTHON_CMD "$ROOT/app.py" > /dev/null 2>&1 &

# ── Aguarda servidor responder ────────────────────────────
TRIES=0
while true; do
    sleep 1
    $PYTHON_CMD -c "import socket; s=socket.create_connection(('127.0.0.1', 5010), timeout=2); s.close()" &> /dev/null
    if [ $? -eq 0 ]; then
        break
    fi
    TRIES=$((TRIES + 1))
    if [ $TRIES -ge 20 ]; then
        echo "[ERRO] Servidor nao respondeu apos 20 tentativas." >> "$LOG"
        echo "Erro: Atlas não respondeu."
        exit 1
    fi
done

exit 0
