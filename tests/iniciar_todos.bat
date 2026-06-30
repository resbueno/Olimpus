@echo off
setlocal
cd /d "%~dp0.."

echo ================================================================
echo  OLIMPUS -- PLANO DE TESTES COMPLETO (TODOS OS APPS)
echo  Executa testes de cada app separadamente e gera log por app.
echo ================================================================
echo.
echo IMPORTANTE: Certifique-se que os apps desejados estao rodando.
echo             Para criar usuarios de teste: rode setup_usuarios.bat
echo.

pip install -q pytest requests 2>nul

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set DT=%%I
set DT=%DT:~0,8%_%DT:~8,4%
set SUMARIO=tests\relatorio_completo_%DT%.log

echo Iniciando suite de testes... >> "%SUMARIO%"
echo Data/Hora: %DT% >> "%SUMARIO%"
echo. >> "%SUMARIO%"

set TOTAL_PASS=0
set TOTAL_FAIL=0

REM ── Atlas ──────────────────────────────────────────────────────────
echo [1/12] Testando ATLAS (porta 5010)...
set LOG=tests\atlas\test_atlas_%DT%.log
python -m pytest tests/atlas/test_atlas.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- ATLAS: %LOG% >> "%SUMARIO%"
echo.

REM ── Hera ───────────────────────────────────────────────────────────
echo [2/12] Testando HERA (porta 5041)...
set LOG=tests\hera\test_hera_%DT%.log
python -m pytest tests/hera/test_hera.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- HERA: %LOG% >> "%SUMARIO%"
echo.

REM ── Ploutos ────────────────────────────────────────────────────────
echo [3/12] Testando PLOUTOS (porta 5080)...
set LOG=tests\ploutos\test_ploutos_%DT%.log
python -m pytest tests/ploutos/test_ploutos.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- PLOUTOS: %LOG% >> "%SUMARIO%"
echo.

REM ── Cronos ─────────────────────────────────────────────────────────
echo [4/12] Testando CRONOS (porta 5025)...
set LOG=tests\cronos\test_cronos_%DT%.log
python -m pytest tests/cronos/test_cronos.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- CRONOS: %LOG% >> "%SUMARIO%"
echo.

REM ── Hércules ───────────────────────────────────────────────────────
echo [5/12] Testando HERCULES (porta 5001)...
set LOG=tests\hercules\test_hercules_%DT%.log
python -m pytest tests/hercules/test_hercules.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- HERCULES: %LOG% >> "%SUMARIO%"
echo.

REM ── Hermes ─────────────────────────────────────────────────────────
echo [6/12] Testando HERMES (porta 5050)...
set LOG=tests\hermes\test_hermes_%DT%.log
python -m pytest tests/hermes/test_hermes.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- HERMES: %LOG% >> "%SUMARIO%"
echo.

REM ── Héstia ─────────────────────────────────────────────────────────
echo [7/12] Testando HESTIA (porta 5020)...
set LOG=tests\hestia\test_hestia_%DT%.log
python -m pytest tests/hestia/test_hestia.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- HESTIA: %LOG% >> "%SUMARIO%"
echo.

REM ── Iris ───────────────────────────────────────────────────────────
echo [8/12] Testando IRIS (porta 5070)...
set LOG=tests\iris\test_iris_%DT%.log
python -m pytest tests/iris/test_iris.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- IRIS: %LOG% >> "%SUMARIO%"
echo.

REM ── Oráculo ────────────────────────────────────────────────────────
echo [9/12] Testando ORACULO (porta 5030)...
set LOG=tests\oraculo\test_oraculo_%DT%.log
python -m pytest tests/oraculo/test_oraculo.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- ORACULO: %LOG% >> "%SUMARIO%"
echo.

REM ── Tiresias ───────────────────────────────────────────────────────
echo [10/12] Testando TIRESIAS (porta 5090)...
set LOG=tests\tiresias\test_tiresias_%DT%.log
python -m pytest tests/tiresias/test_tiresias.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- TIRESIAS: %LOG% >> "%SUMARIO%"
echo.

REM ── Têmis (AVISO: porta 5020 = Héstia) ────────────────────────────
echo [11/12] Testando TEMIS (porta 5020 -- conflito com Hestia!)...
echo ATENCAO: Temis usa porta 5020. Certifique-se que Hestia NAO esta rodando.
set LOG=tests\temis\test_temis_%DT%.log
python -m pytest tests/temis/test_temis.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- TEMIS: %LOG% >> "%SUMARIO%"
echo.

REM ── Argos ──────────────────────────────────────────────────────────
echo [12/12] Testando ARGOS (porta 5000)...
set LOG=tests\argos\test_argos_%DT%.log
python -m pytest tests/argos/test_argos.py -v --tb=short --no-header > "%LOG%" 2>&1
findstr /C:"passed" "%LOG%" >> "%SUMARIO%"
findstr /C:"failed" "%LOG%" >> "%SUMARIO%"
echo --- ARGOS: %LOG% >> "%SUMARIO%"
echo.

echo.
echo ================================================================
echo  SUITE CONCLUIDA
echo  Sumario salvo em: %SUMARIO%
echo  Logs individuais: tests\<app>\test_<app>_%DT%.log
echo ================================================================
echo.
type "%SUMARIO%"
echo.
pause
endlocal
