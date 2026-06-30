# Documentação Técnica - Argos (Monitoração)

## Visão Geral

**Nome**: Argos - Monitoração e Observabilidade
**Porta**: 5000
**Prioridade**: ALTA
**Tecnologias**: Flask, React, PostgreSQL, Prometheus, Grafana
**Responsável**: Equipe de Infraestrutura

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Argos - Monitoração] --> B[API REST]
    A --> C[Frontend]
    A --> D[Banco de Dados]
    A --> E[Monitoração]
    A --> F[Alertas]
    B --> G[/api/monitors]
    B --> H[/api/checks]
    B --> I[/api/alerts]
    C --> J[Dashboard]
    C --> K[Monitores]
    C --> L[Alertas]
    D --> M[PostgreSQL]
    E --> N[Prometheus]
    F --> O[SMTP]
    F --> P[Webhooks]
```

### Fluxo de Monitoração

1. **Configuração**: Monitores são configurados
2. **Verificação**: Checks são executados
3. **Armazenamento**: Resultados são salvos
4. **Análise**: Dados são analisados
5. **Alerta**: Notificações são enviadas
6. **Visualização**: Dashboards são atualizados

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Monitores

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/monitors` | GET | Lista monitores | `?ativo=true` |
| `/api/monitors` | POST | Cria monitor | `{"nome", "url", "intervalo"}` |
| `/api/monitors/<id>` | GET | Detalhes monitor | - |
| `/api/monitors/<id>` | PUT | Atualiza monitor | `{"nome", "url"}` |
| `/api/monitors/<id>` | DELETE | Remove monitor | - |
| `/api/monitors/<id>/toggle` | POST | Ativa/Desativa monitor | - |
| `/api/monitors/<id>/run` | POST | Executa monitor manualmente | - |

### Histórico

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/monitors/<id>/history` | GET | Histórico de checks | `?limit=100` |
| `/api/checks` | GET | Todos os checks | `?status=down&limit=50` |
| `/api/checks/<id>` | GET | Detalhes do check | - |

### Alertas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/alerts` | GET | Lista alertas | `?status=open` |
| `/api/alerts/<id>` | GET | Detalhes alerta | - |
| `/api/alerts/<id>/acknowledge` | POST | Reconhece alerta | - |
| `/api/alerts/<id>/resolve` | POST | Resolve alerta | `{"resolucao"}` |

### Status

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/status` | GET | Status geral | - |
| `/api/status/summary` | GET | Resumo de status | - |
| `/api/status/services` | GET | Status de serviços | - |

### Integração

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/webhooks` | POST | Recebe webhook | `{"event", "data"}` |
| `/api/integrations` | GET | Lista integrações | - |
| `/api/integrations` | POST | Cria integração | `{"tipo", "config"}` |

## Banco de Dados

### Esquema Principal

```sql
-- Monitores
CREATE TABLE monitors (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    url VARCHAR(512) NOT NULL,
    tipo VARCHAR(50) DEFAULT 'http', -- http, ping, tcp, docker
    intervalo INTEGER DEFAULT 60, -- em segundos
    timeout INTEGER DEFAULT 10, -- em segundos
    ativo BOOLEAN DEFAULT TRUE,
    notificar BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Checks
CREATE TABLE checks (
    id SERIAL PRIMARY KEY,
    monitor_id INTEGER REFERENCES monitors(id),
    status VARCHAR(20) NOT NULL, -- up, down, warning
    response_time INTEGER, -- em ms
    response_code INTEGER,
    response_body TEXT,
    error_message TEXT,
    checked_at TIMESTAMP DEFAULT NOW()
);

-- Alertas
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    monitor_id INTEGER REFERENCES monitors(id),
    check_id INTEGER REFERENCES checks(id),
    status VARCHAR(20) DEFAULT 'open', -- open, acknowledged, resolved
    severity VARCHAR(20) DEFAULT 'critical', -- critical, warning, info
    message TEXT NOT NULL,
    acknowledged_by INTEGER REFERENCES usuarios(id),
    acknowledged_at TIMESTAMP,
    resolved_by INTEGER REFERENCES usuarios(id),
    resolved_at TIMESTAMP,
    resolution TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Usuários (sincronizado com Atlas)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    atlas_id INTEGER UNIQUE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    ativo BOOLEAN DEFAULT TRUE
);

-- Integrações
CREATE TABLE integrations (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- email, slack, teams, webhook
    config JSONB NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Notificações
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id),
    integration_id INTEGER REFERENCES integrations(id),
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed
    message TEXT,
    response TEXT,
    sent_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Índices Importantes

```sql
CREATE INDEX idx_monitors_nome ON monitors USING gin (to_tsvector('portuguese', nome));
CREATE INDEX idx_monitors_ativo ON monitors(ativo);
CREATE INDEX idx_checks_monitor ON checks(monitor_id);
CREATE INDEX idx_checks_status ON checks(status);
CREATE INDEX idx_checks_data ON checks(checked_at);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_monitor ON alerts(monitor_id);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_integrations_tipo ON integrations(tipo);
CREATE INDEX idx_notifications_status ON notifications(status);
```

## Integração com Prometheus e Grafana

### Configuração do Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'argos'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:5000']

  - job_name: 'services'
    scrape_interval: 30s
    static_configs:
      - targets:
        - 'atlas:5010'
        - 'hestia:5020'
        - 'cronos:5025'
        - 'hera:5041'
        - 'iris:5070'
        - 'ploutos:5080'
```

### Métricas Expostas

```
# Métricas do Argos
argos_monitors_total{status="up"}
argos_monitors_total{status="down"}
argos_checks_total{status="success"}
argos_checks_total{status="failed"}
argos_alerts_open{severity="critical"}
argos_response_time_seconds{monitor="atlas"}

# Métricas dos serviços monitorados
up{job="services", instance="atlas:5010"}
response_time_seconds{job="services", instance="hestia:5020"}
```

### Dashboard do Grafana

**Painéis Principais**:
- Status geral dos serviços
- Tempo de resposta por serviço
- Alertas abertos por severidade
- Histórico de disponibilidade
- Tendências de performance

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com curta expiração
   - Validação em todos os endpoints

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por monitor
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Dados sensíveis criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Monitoração**:
   - Auto-monitoração
   - Alertas para falhas internas
   - Redundância de componentes

## Monitoramento e Logging

### Métricas Monitoradas

- Número de monitores ativos
- Taxa de sucesso de checks
- Tempo médio de resposta
- Alertas abertos por severidade
- Tempo médio de resolução

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "WARNING",
  "service": "argos",
  "action": "monitor_down",
  "monitor": "atlas",
  "status": "down",
  "response_time": 0,
  "error": "Connection refused"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Prometheus
- Grafana
- 4GB RAM mínima
- 20GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=argos_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/argos
REDIS_URL=redis://localhost:6379/0
PROMETHEUS_URL=http://localhost:9090
ATLAS_URL=http://localhost:5010
PORT=5000
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
flask db upgrade

# 3. Configurar Prometheus
cp prometheus.yml /etc/prometheus/
systemctl restart prometheus

# 4. Configurar Grafana
# Importar dashboard do Argos

# 5. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 6. Configurar systemd
cp argos.service /etc/systemd/system/
systemctl enable argos
systemctl start argos
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres argos > argos_db_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql -U postgres argos < argos_db_backup.sql
```

### Atualizações

1. Parar serviço: `systemctl stop argos`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start argos`
7. Verificar saúde: `curl http://localhost:5000/api/ping`