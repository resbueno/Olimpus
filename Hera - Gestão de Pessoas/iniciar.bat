@echo off
setlocal EnableDelayedExpansion
chcp 1252 >nul 2>&1

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "LOG=%ROOT%\hera_erro.log"

:: ── Python ────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH. >> "%LOG%"
    exit /b 1
)

:: ── pip ───────────────────────────────────────────────────
python -m pip --version >nul 2>&1
if errorlevel 1 (
    python -m ensurepip --upgrade >nul 2>&1
)

:: ── Dependencias ──────────────────────────────────────────
python -c "import flask, flask_cors" >nul 2>&1
if errorlevel 1 (
    python -m pip install -r "%ROOT%\requirements.txt" --quiet --disable-pip-version-check >nul 2>&1
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar dependencias. >> "%LOG%"
        exit /b 1
    )
)

if not exist "%ROOT%\app.py" (
    echo [ERRO] app.py nao encontrado. >> "%LOG%"
    exit /b 1
)

:: ── Mata porta 5041 ───────────────────────────────────────
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":5041 "') do (
    taskkill /PID %%p /F >nul 2>&1
)

:: ── Sobe servidor oculto ──────────────────────────────────
start "" /B pythonw "%ROOT%\app.py"

:: ── Aguarda servidor responder ────────────────────────────
set /a TRIES=0
:PING_LOOP
ping -n 2 127.0.0.1 >nul 2>&1
python -c "import urllib.request; urllib.request.urlopen('http://localhost:5041/api/ping', timeout=2)" >nul 2>&1
if not errorlevel 1 goto SERVER_UP
set /a TRIES+=1
if !TRIES! lss 20 goto PING_LOOP

echo [ERRO] Servidor nao respondeu apos 20 tentativas. >> "%LOG%"
exit /b 1

:SERVER_UP
exit /b 0
