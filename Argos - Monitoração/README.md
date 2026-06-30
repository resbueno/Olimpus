# SYNTHMON — Plataforma Local de Monitoração Recorrente Multi-URL

## Requisitos

- Python 3.11+
- pip

## Instalação

```bash
# 1. Instalar dependências Python
pip install -r requirements.txt

# 2. Instalar navegadores do Playwright
python -m playwright install chromium

# 3. Iniciar a plataforma
python app.py
```

Acesse o painel em: **http://localhost:5000**

---

## Estrutura de arquivos

```
monitor_platform/
├── app.py               # Servidor Flask (API + painel)
├── database.py          # Camada SQLite (CRUD + criptografia de senha)
├── scheduler_manager.py # Orquestrador APScheduler
├── worker.py            # Motor Playwright (execução da jornada)
├── dashboard.html       # Painel web local
├── requirements.txt     # Dependências Python
├── monitor.db           # Banco SQLite (gerado automaticamente)
├── secret.key           # Chave de criptografia (gerada automaticamente)
└── monitor.log          # Log de execuções
```

---

## Arquitetura

```
Painel Web (dashboard.html)
        ↓ HTTP/REST
    API Flask (app.py)
        ↓
  ┌─────┴──────────┐
  │                │
database.py   scheduler_manager.py
(SQLite)          │
                  ↓
            worker.py (Playwright)
                  ↓
            monitor.db (histórico)
```

---

## Endpoints da API

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/monitors` | Lista todos os monitores |
| POST | `/api/monitors` | Cria novo monitor |
| PUT | `/api/monitors/:id` | Atualiza monitor |
| DELETE | `/api/monitors/:id` | Remove monitor |
| POST | `/api/monitors/:id/toggle` | Ativa/desativa |
| POST | `/api/monitors/:id/run` | Executa agora |
| GET | `/api/monitors/:id/history` | Histórico do monitor |
| GET | `/api/history` | Histórico geral |
| GET | `/api/stats` | Estatísticas globais |
| GET | `/api/scheduler/jobs` | Jobs ativos |

---

## Configuração do Seletor de Menu

O campo **Seletor do Menu Alvo** aceita três formatos:

| Formato | Exemplo | Comportamento |
|---------|---------|---------------|
| CSS Selector | `#btn-dashboard` | Localiza e clica no elemento |
| Texto | `Relatórios` | Encontra elemento pelo texto visível |
| URL direta | `url:https://sistema/painel` | Navega diretamente para a URL |

---

## Segurança

- Senhas são **criptografadas** com Fernet (AES-128-CBC) antes de salvar no banco
- A chave `secret.key` é gerada automaticamente e armazenada localmente
- **Nunca compartilhe** o arquivo `secret.key` ou `monitor.db`

---

## Logs

O arquivo `monitor.log` registra todas as execuções, erros e eventos do scheduler.

Para acompanhar em tempo real:
```bash
tail -f monitor.log
```

---

## Plano de Testes (resumo executivo)

Camada | Cobertura
-------|----------
Cadastro | CT01, CT02 — CRUD + validação de campos
Jornada | CT03, CT04 — Playwright end-to-end + medição de tempo
Recorrência | CT06, CT07, CT08 — Scheduler com múltiplos intervalos
Falhas | CT09–CT12 — URL inválida, senha errada, seletor ausente, DB lock
Performance | CT13, CT14 — Limite de 60s por jornada, 20 URLs simultâneas

Critério de aprovação: **100% testes críticos PASS · 95% gerais PASS · 0 falhas bloqueantes**
