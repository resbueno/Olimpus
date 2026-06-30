# Documentação Técnica - Cronos (Ponto Eletrônico)

## Visão Geral

**Nome**: Cronos - Gestão de Jornada de Trabalho
**Porta**: 5025
**Prioridade**: ALTA
**Tecnologias**: Flask, PostgreSQL, Redis, Celery
**Responsável**: Equipe de Recursos Humanos

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Cronos - Ponto Eletrônico] --> B[API REST]
    A --> C[Worker Assíncrono]
    A --> D[Banco de Dados]
    A --> E[Cache]
    A --> F[Integração]
    B --> G[/api/ponto/bater]
    B --> H[/api/ponto/hoje]
    B --> I[/api/dashboard]
    C --> J[Processamento em lote]
    C --> K[Notificações]
    C --> L[Relatórios]
    D --> M[PostgreSQL]
    E --> N[Redis]
    F --> O[Hera]
    F --> P[Ploutos]
```

### Fluxo de Registro de Ponto

1. **Bater Ponto**: Usuário registra entrada/saída
2. **Validação**: Sistema valida regras de negócio
3. **Armazenamento**: Registro salvo no banco
4. **Processamento**: Worker calcula horas trabalhadas
5. **Notificação**: Alertas para anomalias
6. **Integração**: Dados sincronizados com outros sistemas

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Registro de Ponto

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ponto/bater` | POST | Registrar ponto | `{"tipo": "entrada"}` |
| `/api/ponto/hoje` | GET | Registros de hoje | - |
| `/api/ponto/historico` | GET | Histórico completo | `?mes=4&ano=2026` |
| `/api/ponto/espelho` | GET | Espelho de ponto | `?mes=4&ano=2026` |
| `/api/ponto/<id>` | DELETE | Remover registro | - |

### Dashboard

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/dashboard` | GET | Dashboard principal | - |
| `/api/dashboard/hoje` | GET | Resumo do dia | - |
| `/api/dashboard/semana` | GET | Resumo semanal | - |
| `/api/dashboard/mes` | GET | Resumo mensal | `?mes=4&ano=2026` |

### Ajustes e Solicitações

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ajustes` | GET | Lista solicitações | `?status=pendente` |
| `/api/ajustes` | POST | Solicitar ajuste | `{"data", "tipo", "horario", "motivo"}` |
| `/api/ajustes/<id>` | PUT | Aprovar/Rejeitar | `{"status", "comentario"}` |

### Jornadas de Trabalho

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/jornadas` | GET | Lista jornadas | - |
| `/api/jornadas` | POST | Criar jornada | `{"nome", "tipo", "horas"}` |
| `/api/jornadas/<id>` | GET | Detalhes jornada | - |
| `/api/jornadas/atribuir` | POST | Atribuir a usuário | `{"usuario_id", "jornada_id"}` |

### Banco de Horas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/banco-horas` | GET | Saldo atual | - |
| `/api/banco-horas/historico` | GET | Histórico | `?ano=2026` |
| `/api/banco-horas/compensar` | POST | Compensar horas | `{"minutos", "descricao"}` |
| `/api/banco-horas/abater` | POST | Abater horas | `{"minutos", "descricao"}` |

### Fechamentos e Feriados

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/fechamentos` | GET | Lista fechamentos | `?mes=4&ano=2026` |
| `/api/fechamentos` | POST | Gerar fechamento | `{"mes", "ano"}` |
| `/api/feriados` | GET | Lista feriados | `?ano=2026` |
| `/api/feriados` | POST | Cadastrar feriado | `{"data", "descricao"}` |

## Banco de Dados

### Esquema Principal

```sql
-- Registros de ponto
CREATE TABLE ponto_registros (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    tipo VARCHAR(20) NOT NULL, -- entrada, saida, pausa_inicio, pausa_fim
    horario TIMESTAMP NOT NULL,
    ip VARCHAR(45),
    dispositivo VARCHAR(100),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Jornadas de trabalho
CREATE TABLE jornadas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL, -- fixo, flexivel, escala
    hora_entrada TIME,
    hora_saida TIME,
    hora_inicio_intervalo TIME,
    hora_fim_intervalo TIME,
    carga_horaria_dia INTEGER, -- em minutos
    dias_semana INTEGER[], -- [0=dom, 1=seg, ..., 6=sab]
    ativa BOOLEAN DEFAULT TRUE
);

-- Usuários (sincronizado com Hera)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    hera_id INTEGER UNIQUE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    matricula VARCHAR(50) UNIQUE,
    departamento_id INTEGER,
    jornada_id INTEGER REFERENCES jornadas(id),
    ativo BOOLEAN DEFAULT TRUE
);

-- Solicitações de ajuste
CREATE TABLE ajustes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    data DATE NOT NULL,
    tipo_original VARCHAR(20),
    horario_original TIMESTAMP,
    tipo_solicitado VARCHAR(20) NOT NULL,
    horario_solicitado TIMESTAMP NOT NULL,
    motivo TEXT,
    status VARCHAR(20) DEFAULT 'pendente', -- pendente, aprovado, rejeitado
    aprovador_id INTEGER REFERENCES usuarios(id),
    comentario_aprovador TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Banco de horas
CREATE TABLE banco_horas (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    tipo VARCHAR(20) NOT NULL, -- credito, debito, compensacao
    minutos INTEGER NOT NULL,
    descricao TEXT,
    data_registro DATE DEFAULT CURRENT_DATE,
    saldo_anterior INTEGER DEFAULT 0,
    saldo_posterior INTEGER DEFAULT 0,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Fechamentos mensais
CREATE TABLE fechamentos (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    mes INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    horas_trabalhadas INTEGER, -- em minutos
    horas_extras INTEGER, -- em minutos
    horas_debitadas INTEGER, -- em minutos
    horas_credito_anterior INTEGER,
    horas_credito_posterior INTEGER,
    status VARCHAR(20) DEFAULT 'aberto', -- aberto, fechado, aprovado
    criado_em TIMESTAMP DEFAULT NOW(),
    fechado_em TIMESTAMP,
    UNIQUE (usuario_id, mes, ano)
);

-- Feriados
CREATE TABLE feriados (
    id SERIAL PRIMARY KEY,
    data DATE UNIQUE NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    tipo VARCHAR(20), -- nacional, estadual, municipal
    recorrente BOOLEAN DEFAULT FALSE
);
```

### Índices Importantes

```sql
CREATE INDEX idx_ponto_usuario ON ponto_registros(usuario_id);
CREATE INDEX idx_ponto_data ON ponto_registros(horario);
CREATE INDEX idx_ponto_usuario_data ON ponto_registros(usuario_id, horario);
CREATE INDEX idx_usuarios_email ON usuarios(email);
CREATE INDEX idx_usuarios_matricula ON usuarios(matricula);
CREATE INDEX idx_ajustes_status ON ajustes(status);
CREATE INDEX idx_ajustes_data ON ajustes(data);
CREATE INDEX idx_banco_horas_usuario ON banco_horas(usuario_id);
CREATE INDEX idx_fechamentos_usuario ON fechamentos(usuario_id);
CREATE INDEX idx_fechamentos_data ON fechamentos(ano, mes);
CREATE INDEX idx_feriados_data ON feriados(data);
```

## Integração com Outros Apps

### Integração com Hera (RH)

1. **Sincronização de Usuários**:
   - Dados básicos: nome, email, matrícula, departamento
   - Atualização diária via webhook
   - Desativação automática de usuários

2. **Jornadas de Trabalho**:
   - Jornadas definidas no Hera
   - Sincronização em tempo real
   - Atribuição automática a novos usuários

### Integração com Ploutos (Financeiro)

1. **Horas Extras**:
   - Dados de horas extras para folha
   - Exportação mensal automática
   - Formato: CSV com matrícula, horas, valor

2. **Banco de Horas**:
   - Saldo para compensação financeira
   - Relatórios de abono
   - Integração com contabilidade

## Processamento Assíncrono (Celery)

### Tarefas em Segundo Plano

```python
# tasks.py
@celery.task(bind=True)
def processar_fechamento_mensal(self, mes, ano):
    """Processa fechamento mensal para todos os usuários"""
    usuarios = Usuario.query.filter_by(ativo=True).all()
    
    for usuario in usuarios:
        # Calcula horas trabalhadas
        horas_trabalhadas = calcular_horas_trabalhadas(usuario.id, mes, ano)
        
        # Cria fechamento
        fechamento = Fechamento(
            usuario_id=usuario.id,
            mes=mes,
            ano=ano,
            horas_trabalhadas=horas_trabalhadas,
            status='aberto'
        )
        db.session.add(fechamento)
    
    db.session.commit()
    return f"Fechamento {mes}/{ano} processado para {len(usuarios)} usuários"

@celery.task(bind=True)
def notificar_ajustes_pendentes(self):
    """Notifica gestores sobre ajustes pendentes"""
    ajustes = Ajuste.query.filter_by(status='pendente').all()
    
    for ajuste in ajustes:
        gestor = get_gestor(ajuste.usuario_id)
        enviar_notificacao(
            gestor.email,
            f"Ajuste de ponto pendente para {ajuste.usuario.nome}",
            f"Data: {ajuste.data}, Motivo: {ajuste.motivo}"
        )
    
    return f"Notificações enviadas para {len(set(a.gestor_id for a in ajustes))} gestores"
```

### Agendamento de Tarefas

```python
# Agendamento via Celery Beat
CELERYBEAT_SCHEDULE = {
    'fechamento-mensal': {
        'task': 'tasks.processar_fechamento_mensal',
        'schedule': crontab(day=1, hour=2, minute=0),  # Dia 1 de cada mês às 2h
        'args': (None, None),  # mes e ano serão calculados
    },
    'notificar-ajustes': {
        'task': 'tasks.notificar_ajustes_pendentes',
        'schedule': crontab(hour=9, minute=0),  # Todos os dias às 9h
    },
    'limpar-cache': {
        'task': 'tasks.limpar_cache',
        'schedule': crontab(hour=3, minute=0),  # Todos os dias às 3h
    },
}
```

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com curta expiração
   - Validação em todos os endpoints

2. **Proteção de Dados**:
   - Dados sensíveis criptografados
   - Acesso a banco restrito a rede interna
   - Backups diários com retenção

3. **Prevenção de Fraudes**:
   - Validação de IP e dispositivo
   - Detecção de padrões suspeitos
   - Alertas para anomalias

4. **Auditoria**:
   - Log de todas as operações
   - Retenção de logs por 1 ano
   - Monitoramento em tempo real

## Monitoramento e Logging

### Métricas Monitoradas

- Número de registros de ponto por hora
- Taxa de sucesso de registros
- Tempo médio de resposta
- Solicitações de ajuste pendentes
- Saldo médio de banco de horas

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T08:00:00Z",
  "level": "INFO",
  "service": "cronos",
  "action": "ponto_registrado",
  "user": "admin@olimpus.local",
  "tipo": "entrada",
  "horario": "2026-04-20T08:00:00",
  "ip": "192.168.1.100",
  "dispositivo": "web"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Celery + RabbitMQ
- 4GB RAM mínima
- 20GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=cronos_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/cronos
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
HERA_URL=http://localhost:5041
PLOUTOS_URL=http://localhost:5080
ATLAS_URL=http://localhost:5010
PORT=5025
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
flask db upgrade

# 3. Iniciar Celery Worker
celery -A tasks.celery worker --loglevel=info

# 4. Iniciar Celery Beat (agendador)
celery -A tasks.celery beat --loglevel=info

# 5. Iniciar serviço principal
gunicorn -w 4 -b 0.0.0.0:5025 app:app

# 6. Configurar systemd
cp cronos.service /etc/systemd/system/
cp cronos-worker.service /etc/systemd/system/
cp cronos-beat.service /etc/systemd/system/

systemctl enable cronos
systemctl enable cronos-worker
systemctl enable cronos-beat

systemctl start cronos
systemctl start cronos-worker
systemctl start cronos-beat
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres cronos > cronos_db_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql -U postgres cronos < cronos_db_backup.sql
```

### Atualizações

1. Parar serviços: `systemctl stop cronos*`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviços: `systemctl start cronos*`
7. Verificar saúde: `curl http://localhost:5025/api/ping`