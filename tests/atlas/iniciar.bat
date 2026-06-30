@echo off
setlocal
cd /d "%~dp0..\.."

echo ============================================================
echo  OLIMPUS -- PLANO DE TESTES: ATLAS (IAM Central)
echo  Porta: 5010
echo ============================================================
echo.

REM Verifica dependencias
pip install -q pytest requests 2>nul

REM Verifica se Atlas esta rodando
python -c "import requests; r=requests.get('http://localhost:5010/api/ping',timeout=3); exit(0) if r.status_code==200 else exit(1)" 2>nul
if errorlevel 1 (
    echo [AVISO] Atlas nao parece estar rodando em localhost:5010
    echo         Inicie o Atlas antes de executar os testes.
    echo.
)

REM Gera nome do log com data/hora
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set DT=%DT:~0,8%_%DT:~8,4%
set LOGFILE=tests\atlas\test_atlas_%DT%.log

echo Executando testes...
echo Log: %LOGFILE%
echo.

python -m pytest tests/atlas/test_atlas.py -v --tb=short --no-header > "%LOGFILE%" 2>&1

echo.
echo ============================================================
type "%LOGFILE%"
echo ============================================================
echo.
echo Log completo salvo em: %LOGFILE%
echo.
pause
endlocal
