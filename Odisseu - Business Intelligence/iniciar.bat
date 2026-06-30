@echo off
rem Odisseu - Business Intelligence - Startup (Windows)
setlocal EnableDelayedExpansion
chcp 1252 >nul 2>&1

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "LOG=%ROOT%\odisseu_erro.log"

set "PORT=%ODISSEU_PORT%"
if "%PORT%"=="" set "PORT=5100"
set "HOST=%ODISSEU_HOST%"
if "%HOST%"=="" set "HOST=127.0.0.1"

:: ── Python ─────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH. >> "%LOG%"
    exit /b 1
)

:: ── Dependencias ───────────────────────────────────────────────────────────
python -c "import flask, flask_cors" >nul 2>&1
if errorlevel 1 (
    echo [Odisseu] Instalando dependencias...
    call :log Instalando dependencias...
    python -m pip install -r "%ROOT%\requirements.txt" --quiet --disable-pip-version-check >>"%LOG%" 2>>&1
    if errorlevel 1 (
        call :log ERRO Falha ao instalar dependencias.
        exit /b 1
    )
    call :log Dependencias instaladas.
)

:: ── Libera porta ───────────────────────────────────────────────────────────
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":%PORT% " ^| findstr LISTENING') do (
    taskkill /PID %%p /F >nul 2>&1
)

:: ── Sobe servidor em background ────────────────────────────────────────────
set "ODISSEU_PORT=%PORT%"
set "ODISSEU_HOST=%HOST%"
start "" /B pythonw "%ROOT%\app.py"

:: ── Aguarda resposta (Flask sobe em ~2s) ───────────────────────────────────
set /a TRIES=0
:PING_LOOP
    ping -n 2 127.0.0.1 >nul 2>&1
    python -c "import urllib.request; urllib.request.urlopen('http://%HOST%:%PORT%/api/ping', timeout=2)" >nul 2>&1
    if not errorlevel 1 goto SERVER_UP
    set /a TRIES+=1
    if !TRIES! lss 30 goto PING_LOOP

call :log ERRO Timeout aguardando servidor.
exit /b 1

:SERVER_UP
    call :log Servidor iniciado em http://%HOST%:%PORT%
    exit /b 0

:log
    set "now=%date% %time%"
    echo [%now%] %*>>"%LOG%"
    goto :eof
