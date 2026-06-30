#!/bin/bash

# Define o diretório de trabalho para a pasta do script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

ROOT="$DIR"
LOG="$ROOT/olimpus_erro.log"

# -------------------------------------------------------
# PASSO 1 - Verificar Python
# -------------------------------------------------------
PYTHON_CMD="python3"
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD="python"
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo "[ERRO] Python nao encontrado." >> "$LOG"
        echo "Erro: Python não está instalado ou não foi encontrado no PATH."
        exit 1
    fi
fi

# -------------------------------------------------------
# PASSO 2 - Verificar pip
# -------------------------------------------------------
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    $PYTHON_CMD -m ensurepip --upgrade &> /dev/null
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        echo "[ERRO] pip nao instalavel." >> "$LOG"
        echo "Erro: pip não está instalado e não pôde ser configurado."
        exit 1
    fi
fi

# -------------------------------------------------------
# PASSO 3 - Instalar Flask e dependencias
# -------------------------------------------------------
if ! $PYTHON_CMD -c "import flask, flask_cors" &> /dev/null; then
    $PYTHON_CMD -m pip install flask flask-cors --quiet --disable-pip-version-check &> /dev/null
    if [ $? -ne 0 ]; then
        echo "[ERRO] Falha ao instalar Flask." >> "$LOG"
        echo "Erro: Falha ao instalar as dependências do Flask."
        exit 1
    fi
fi

if [ ! -f "$ROOT/app.py" ]; then
    echo "[ERRO] app.py nao encontrado em $ROOT." >> "$LOG"
    echo "Erro: app.py não encontrado."
    exit 1
fi

# -------------------------------------------------------
# PASSO 4 - Garantir que o Atlas esta no ar
# -------------------------------------------------------
$PYTHON_CMD -c "import socket; s=socket.create_connection(('127.0.0.1', 5010), timeout=2); s.close()" &> /dev/null
if [ $? -eq 0 ]; then
    echo "Atlas já está rodando."
else
    # Atlas não está respondendo — localiza a pasta pelo prefixo (evita problemas com acentos)
    ATLAS_DIR=""
    for d in "$ROOT"/Atlas*; do
        if [ -d "$d" ]; then
            if [ -f "$d/iniciar.command" ]; then
                ATLAS_SCRIPT="$d/iniciar.command"
                ATLAS_DIR="$d"
                break
            elif [ -f "$d/iniciar.sh" ]; then
                ATLAS_SCRIPT="$d/iniciar.sh"
                ATLAS_DIR="$d"
                break
            fi
        fi
    done

    if [ -z "$ATLAS_DIR" ]; then
        echo "[ERRO] Pasta ou script do Atlas nao encontrado em: $ROOT" >> "$LOG"
        echo "Erro: Pasta ou script do Atlas não encontrado."
        exit 1
    fi

    echo "Iniciando Atlas em segundo plano..."
    chmod +x "$ATLAS_SCRIPT"
    "$ATLAS_SCRIPT" &

    # Aguarda Atlas responder na porta 5010 (até 20 segundos)
    PTRIES=0
    while true; do
        sleep 1
        $PYTHON_CMD -c "import socket; s=socket.create_connection(('127.0.0.1', 5010), timeout=2); s.close()" &> /dev/null
        if [ $? -eq 0 ]; then
            break
        fi
        PTRIES=$((PTRIES + 1))
        if [ $PTRIES -ge 20 ]; then
            echo "[ERRO] Atlas nao respondeu apos 20 segundos." >> "$LOG"
            echo "Erro: Atlas não respondeu."
            exit 1
        fi
    done
fi

# -------------------------------------------------------
# PASSO 5 - Mata porta 5100 se em uso
# -------------------------------------------------------
PORT_PID=$(lsof -t -i :5100)
if [ ! -z "$PORT_PID" ]; then
    echo "Liberando a porta 5100 (PID: $PORT_PID)..."
    kill -9 $PORT_PID &> /dev/null
fi

# -------------------------------------------------------
# PASSO 6 - Sobe servidor Flask oculto
# -------------------------------------------------------
nohup $PYTHON_CMD "$ROOT/app.py" > /dev/null 2>&1 &

# Aguarda o servidor responder HTTP
TRIES=0
while true; do
    sleep 1
    $PYTHON_CMD -c "import urllib.request; urllib.request.urlopen('http://localhost:5100/api/ping', timeout=2)" &> /dev/null
    if [ $? -eq 0 ]; then
        break
    fi
    TRIES=$((TRIES + 1))
    if [ $TRIES -ge 20 ]; then
        echo "[ERRO] Servidor nao respondeu apos 20 segundos." >> "$LOG"
        echo "Erro: Servidor Flask não respondeu."
        exit 1
    fi
done

echo "Servidor rodando com sucesso! Abrindo no navegador..."
open "http://localhost:5100"
exit 0
