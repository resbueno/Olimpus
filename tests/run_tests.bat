@echo off
REM run_tests.bat - Run Olimpus Tests
setlocal

cd /d "%~dp0.."

echo ========================================
echo Olimpus Test Suite v1.0
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

REM Install dependencies
echo Checking dependencies...
pip install -q pytest requests pytest-html pytest-json-report python-dotenv Faker 2>nul

REM Create reports folder
if not exist "tests\reports" mkdir "tests\reports"

echo.
echo ========================================
echo Running tests...
echo ========================================

REM Run all tests
python -m pytest tests/app tests/integration -v --tb=short --html=tests/reports/report.html --self-contained-html --json-report --json-report-file=tests/reports/report.json

echo.
echo ========================================
echo Results: tests\reports\report.html
echo JSON: tests\reports\report.json
echo ========================================
echo.

pause