#!/bin/bash
# run_tests.sh - Executar testes Olimpus (Linux/Mac)

cd "$(dirname "$0")/.."

echo "========================================"
echo "Olimpus Test Suite v1.0"
echo "========================================"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "Python nao encontrado"
    exit 1
fi

# Instalar dependencias
pip3 install -q pytest requests pytest-html pytest-json-report python-dotenv Faker 2>/dev/null

# Criar pasta reports
mkdir -p tests/reports

echo ""
echo "========================================"
echo "Executando testes..."
echo "========================================"

# Executar todos os testes
python3 -m pytest tests/app tests/integration -v --tb=short \
    --html=tests/reports/report.html \
    --self-contained-html \
    --json-report \
    --json-report-file=tests/reports/report.json

echo ""
echo "========================================"
echo "Resultado: tests/reports/report.html"
echo "JSON: tests/reports/report.json"
echo "========================================"