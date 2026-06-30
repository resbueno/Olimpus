@echo off
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "LOG=%ROOT%\olimpus_erro.log"

cls
echo.
echo  ============================================================
echo    OLIMPUS - Inicializando Hub de Aplicacoes
echo  ============================================================
echo.

:: -------------------------------------------------------
:: PASSO 1 - Verificar Python
:: -------------------------------------------------------
echo  [1/7] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado no PATH.
    echo  [ERRO] Python nao encontrado. >> "%LOG%"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo         %%v encontrado.

:: -------------------------------------------------------
:: PASSO 2 - Verificar pip
:: -------------------------------------------------------
echo  [2/7] Verificando pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo         pip nao encontrado. Instalando...
    python -m ensurepip --upgrade >nul 2>&1
    if errorlevel 1 (
        echo  [ERRO] pip nao instalavel.
        echo  [ERRO] pip nao instalavel. >> "%LOG%"
        echo.
        pause
        exit /b 1
    )
)
echo         pip OK.

:: -------------------------------------------------------
:: PASSO 3 - Instalar Flask e dependencias
:: -------------------------------------------------------
echo  [3/7] Verificando dependencias do hub (Flask)...
python -c "import flask, flask_cors" >nul 2>&1
if errorlevel 1 (
    echo         Instalando Flask e flask-cors...
    python -m pip install flask flask-cors --quiet --disable-pip-version-check >nul 2>&1
    if errorlevel 1 (
        echo  [ERRO] Falha ao instalar Flask.
        echo  [ERRO] Falha ao instalar Flask. >> "%LOG%"
        echo.
        pause
        exit /b 1
    )
    echo         Instalacao concluida.
) else (
    echo         Flask OK.
)

if not exist "%ROOT%\app.py" (
    echo  [ERRO] app.py nao encontrado em: %ROOT%
    echo  [ERRO] app.py nao encontrado. >> "%LOG%"
    echo.
    pause
    exit /b 1
)

:: -------------------------------------------------------
:: PASSO 4 - Garantir que o Atlas esta no ar
:: -------------------------------------------------------
echo  [4/7] Verificando Atlas (porta 5010)...
python -c "import socket; s=socket.create_connection(('127.0.0.1',5010),timeout=2); s.close()" >nul 2>&1
if not errorlevel 1 (
    echo         Atlas ja esta rodando.
    goto ATLAS_OK
)

echo         Atlas offline. Localizando script de inicializacao...
set "ATLAS_BAT="
for /d %%d in ("%ROOT%\Atlas*") do (
    if exist "%%d\iniciar.bat" set "ATLAS_BAT=%%d\iniciar.bat"
)

if "!ATLAS_BAT!"=="" (
    echo  [ERRO] Pasta do Atlas nao encontrada em: %ROOT%
    echo  [ERRO] Pasta do Atlas nao encontrada em: %ROOT% >> "%LOG%"
    echo.
    pause
    exit /b 1
)

echo         Iniciando Atlas...
start "" /B cmd /c "!ATLAS_BAT!"

set /a PTRIES=0
:ATLAS_WAIT
ping -n 2 127.0.0.1 >nul 2>&1
python -c "import socket; s=socket.create_connection(('127.0.0.1',5010),timeout=2); s.close()" >nul 2>&1
if not errorlevel 1 goto ATLAS_PRONTO
set /a PTRIES+=1
set /a PSEC=PTRIES*2
echo         Aguardando Atlas... (!PSEC!s)
if !PTRIES! lss 20 goto ATLAS_WAIT

echo  [ERRO] Atlas nao respondeu apos 40 segundos.
echo  [ERRO] Atlas nao respondeu apos 40 segundos. >> "%LOG%"
echo.
pause
exit /b 1

:ATLAS_PRONTO
echo         Atlas respondendo na porta 5010.

:ATLAS_OK

:: -------------------------------------------------------
:: PASSO 5 - Mata porta 5100 se em uso
:: -------------------------------------------------------
echo  [5/7] Liberando porta 5100...
set "KILLED=0"
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":5100 "') do (
    taskkill /PID %%p /F >nul 2>&1
    set "KILLED=1"
)
if "!KILLED!"=="1" (
    echo         Processo anterior encerrado.
) else (
    echo         Porta livre.
)

:: -------------------------------------------------------
:: PASSO 6 - Sobe servidor Flask
:: -------------------------------------------------------
echo  [6/7] Iniciando hub Olimpus (porta 5100)...
start "" /B pythonw "%ROOT%\app.py"

set /a TRIES=0
:PING_LOOP
ping -n 2 127.0.0.1 >nul 2>&1
python -c "import urllib.request; urllib.request.urlopen('http://localhost:5100/api/ping', timeout=2)" >nul 2>&1
if not errorlevel 1 goto SERVER_UP
set /a TRIES+=1
set /a TSEC=TRIES*2
echo         Aguardando hub... (!TSEC!s)
if !TRIES! lss 20 goto PING_LOOP

echo  [ERRO] Hub nao respondeu apos 40 segundos.
echo  [ERRO] Servidor nao respondeu apos 40 segundos. >> "%LOG%"
echo.
pause
exit /b 1

:SERVER_UP
echo         Hub respondendo em http://localhost:5100
start "" "http://localhost:5100"

:: -------------------------------------------------------
:: PASSO 7 - Sobe o Higeia (Streamlit, porta 8501)
:: -------------------------------------------------------
echo  [7/7] Iniciando Higeia (porta 8501)...
set "HIGEIA_BAT="
for /d %%d in ("%ROOT%\Higeia*") do (
    if exist "%%d\iniciar.bat" set "HIGEIA_BAT=%%d\iniciar.bat"
)

if not "!HIGEIA_BAT!"=="" (
    start "" /B cmd /c "!HIGEIA_BAT!"
    echo         Higeia iniciando em segundo plano...
) else (
    echo         Higeia nao encontrado. Pulando.
)

echo.
echo  ============================================================
echo    Tudo pronto! Olimpus e Higeia estao no ar.
echo  ============================================================
echo.
echo   Hub:    http://localhost:5100
echo   Higeia: http://localhost:8501
echo.
timeout /t 4 >nul
exit /b 0
