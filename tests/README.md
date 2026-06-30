# Olimpus Test Suite

Suite de testes automatizados para os apps do Olimpus.

## Estrutura

```
tests/
├── pytest.ini          # Configuração pytest
├── conftest.py        # Fixtures globais
├── requirements.txt   # Dependências
├── .env               # Credenciais (git ignore)
├── app/
│   ├── test_atlas.py     # 12 testes
│   ├── test_argos.py    # 8 testes
│   ├── test_hestia.py   # 16 testes
│   ├── test_hera.py    # 8 testes
│   ├── test_iris.py    # 6 testes
│   ├── test_ploutos.py # 6 testes
│   ├── test_hub.py     # 4 testes
│   ├── test_cronos.py # 14 testes
│   ├── test_oraculo.py # 8 testes
│   ├── test_hercules.py # 10 testes
│   └── test_hermes.py # 8 testes
├── integration/
│   └── test_sso.py    # 5 testes
└── reports/           # Saída relatórios
```

## Como Executar

### Windows
```batch
cd Olimpus
tests\run_tests.bat
```

### Linux/Mac
```bash
cd Olimpus
chmod +x tests/run_tests.sh
./tests/run_tests.sh
```

### Manual
```bash
pip install -r tests/requirements.txt
python -m pytest tests/app -v --html=tests/reports/report.html
```

## Apps testados

| App | Porta | Testes |
|-----|-------|--------|
| Atlas | 5010 | 12 |
| Hub | 5100 | 4 |
| Argos | 5000 | 8 |
| Héstia | 5020 | 16 |
| Cronos | 5025 | 14 |
| Hera | 5041 | 8 |
| Hércules | 5001 | 10 |
| Hermes | 5050 | 8 |
| Iris | 5070 | 6 |
| Oráculo | 5030 | 8 |
| Ploutos | 5080 | 6 |

**Total: 90 testes**

## Relatórios

- `tests/report.html` - Visual no navegador
- `tests/report.json` - Parse automático

## Tags

```bash
# Apenas API
pytest tests/app -m api -v

# Apenas integração
pytest tests/integration -m integration -v

# Ignorar lentos
pytest tests/app -m "not slow" -v
```

## Configuração

Edite `.env` com suas credenciais:
```
TEST_EMAIL=admin@olimpus.local
TEST_PASSWORD=sua_senha
```

## Requisitos

- Python 3.8+
- Atlas rodando em localhost:5010
- Apps Olimpus rodando nas portas corretas