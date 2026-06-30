@echo off
cd /d "%~dp0.."
echo ============================================================
echo  Olimpus — Setup de Usuarios de Teste
echo ============================================================
echo.
echo Verificando dependencias...
pip install -q requests 2>nul
echo.
echo Criando usuarios no Atlas (certifique-se que o Atlas esta rodando)...
echo.
python tests\setup_usuarios.py
echo.
pause
