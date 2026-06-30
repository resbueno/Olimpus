@echo off
setlocal
cd /d "%~dp0..\.."

echo ============================================================
echo  OLIMPUS -- PLANO DE TESTES: HERA (Gestao de Pessoas)
echo  Porta: 5041 | Roles testadas: admin / rh (gestor) / colaborador (operador)
echo ============================================================
echo.

pip install -q pytest requests 2>nul

python -c "import requests; r=requests.get('http://localhost:5010/api/ping',timeout=3); exit(0) if r.status_code==200 else exit(1)" 2>nul
if errorlevel 1 (
    echo [AVISO] Atlas nao parece estar rodando em localhost:5010
    echo         O Atlas e necessario para autenticacao.
    echo.
)

python -c "import requests; r=requests.get('http://localhost:5041/api/ping',timeout=3); exit(0) if r.status_code==200 else exit(1)" 2>nul
if errorlevel 1 (
    echo [AVISO] Hera nao parece estar rodando em localhost:5041
    echo         Inicie o Hera antes de executar os testes.
    echo.
)

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set DT=%DT:~0,8%_%DT:~8,4%
set LOGFILE=tests\hera\test_hera_%DT%.log

echo Executando testes...
echo Log: %LOGFILE%
echo.

python -m pytest tests/hera/test_hera.py -v --tb=short --no-header > "%LOGFILE%" 2>&1

echo.
echo ============================================================
type "%LOGFILE%"
echo ============================================================
echo.
echo Log completo salvo em: %LOGFILE%
echo.
pause
endlocal
