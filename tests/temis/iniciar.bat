@echo off
setlocal
cd /d "%~dp0..\.."

echo ============================================================
echo  OLIMPUS -- PLANO DE TESTES: TEMIS (Gestao de Contratos)
echo  Porta: 5020 | Roles testadas: admin (funcao Atlas) / operador (sem funcao admin)
echo  ATENCAO: Temis e Hestia compartilham a porta 5020 -- rode separadamente!
echo ============================================================
echo.

pip install -q pytest requests 2>nul

python -c "import requests; r=requests.get('http://localhost:5010/api/ping',timeout=3); exit(0) if r.status_code==200 else exit(1)" 2>nul
if errorlevel 1 (echo [AVISO] Atlas nao esta rodando em localhost:5010 && echo.)

python -c "import requests; r=requests.get('http://localhost:5020/',timeout=3); exit(0) if r.status_code in [200,302] else exit(1)" 2>nul
if errorlevel 1 (echo [AVISO] Temis nao esta rodando em localhost:5020 && echo.)

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set DT=%DT:~0,8%_%DT:~8,4%
set LOGFILE=tests\temis\test_temis_%DT%.log

echo Executando testes...
echo Log: %LOGFILE%
echo.

python -m pytest tests/temis/test_temis.py -v --tb=short --no-header > "%LOGFILE%" 2>&1

echo.
echo ============================================================
type "%LOGFILE%"
echo ============================================================
echo.
echo Log completo salvo em: %LOGFILE%
echo.
pause
endlocal
