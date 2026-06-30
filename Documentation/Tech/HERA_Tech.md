# Documentação Técnica - Hera (Gestão de Pessoas)

## Visão Geral

**Nome**: Hera - Gestão de Pessoas e RH
**Porta**: 5041
**Prioridade**: ALTA
**Tecnologias**: Flask, PostgreSQL, Redis, Celery
**Responsável**: Equipe de Recursos Humanos

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Hera - Gestão de Pessoas] --> B[API REST]
    A --> C[Worker Assíncrono]
    A --> D[Banco de Dados]
    A --> E[Cache]
    A --> F[Integração]
    B --> G[/api/users]
    B --> H[/api/departments]
    B --> I[/api/ferias]
    C --> J[Processamento em lote]
    C --> K[Notificações]
    C --> L[Relatórios]
    D --> M[PostgreSQL]
    E --> N[Redis]
    F --> O[Atlas]
    F --> P[Cronos]
    F --> Q[Iris]
```

### Fluxo de Gestão de Pessoas

1. **Cadastro**: Novo colaborador é cadastrado
2. **Onboarding**: Processo de integração iniciado
3. **Desenvolvimento**: Avaliações e treinamentos
4. **Benefícios**: Gestão de benefícios e folha
5. **Desligamento**: Processo de saída
6. **Análise**: Relatórios e métricas de RH

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Colaboradores

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/users` | GET | Lista colaboradores | `?ativo=1&departamento=TI` |
| `/api/users` | POST | Cria colaborador | `{"nome", "email", "departamento"}` |
| `/api/users/<id>` | GET | Detalhes colaborador | - |
| `/api/users/<id>` | PUT | Atualiza colaborador | `{"nome", "departamento"}` |
| `/api/users/<id>/activate` | POST | Ativa colaborador | - |
| `/api/users/<id>/deactivate` | POST | Desativa colaborador | - |

### Departamentos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/departments` | GET | Lista departamentos | - |
| `/api/departments` | POST | Cria departamento | `{"nome", "gestor_id"}` |
| `/api/departments/<id>` | GET | Detalhes departamento | - |
| `/api/departments/<id>/users` | GET | Colaboradores do departamento | - |

### Férias

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ferias` | GET | Lista solicitações | `?status=pendente` |
| `/api/ferias` | POST | Solicitar férias | `{"user_id", "data_inicio", "data_fim"}` |
| `/api/ferias/<id>` | PUT | Aprovar/Rejeitar | `{"status", "comentario"}` |
| `/api/ferias/saldo/<user_id>` | GET | Saldo de férias | - |

### Avaliações 360°

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ciclos` | GET | Lista ciclos de avaliação | - |
| `/api/ciclos` | POST | Cria ciclo | `{"titulo", "data_inicio", "data_fim"}` |
| `/api/ciclos/<id>` | GET | Detalhes ciclo | - |
| `/api/ciclos/<id>/avaliacoes` | GET | Avaliações do ciclo | - |
| `/api/avaliacoes` | POST | Submeter avaliação | `{"ciclo_id", "avaliado_id", "respostas"}` |

### Onboarding

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/onboarding/etapas` | GET | Lista etapas | - |
| `/api/onboarding/<user_id>` | GET | Progresso do usuário | - |
| `/api/onboarding/<user_id>/etapa/<etapa_id>` | POST | Completa etapa | - |
| `/api/onboarding/template` | POST | Cria template | `{"nome", "etapas"}` |

### Treinamentos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/treinamentos` | GET | Lista treinamentos | - |
| `/api/treinamentos` | POST | Cria treinamento | `{"titulo", "descricao", "data"}` |
| `/api/treinamentos/<id>/inscrever` | POST | Inscrever usuário | `{"user_id"}` |
| `/api/treinamentos/<id>/certificar` | POST | Emitir certificado | `{"user_id"}` |

### Feedback e Kudos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/feedbacks` | GET | Lista feedbacks | `?user_id=123` |
| `/api/feedbacks` | POST | Enviar feedback | `{"to_user_id", "message", "type"}` |
| `/api/kudos/feed` | GET | Feed de kudos | `?limit=10` |
| `/api/kudos` | POST | Enviar kudos | `{"to_user_id", "message"}` |

### Relatórios

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/reports/turnover` | GET | Taxa de turnover | `?ano=2026` |
| `/api/reports/headcount` | GET | Número de colaboradores | `?departamento=TI` |
| `/api/reports/ferias` | GET | Relatórios de férias | `?ano=2026` |
| `/api/reports/avaliacoes` | GET | Resultados avaliações | `?ciclo_id=1` |

## Banco de Dados

### Esquema Principal

```sql
-- Colaboradores
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    atlas_id INTEGER UNIQUE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    matricula VARCHAR(50) UNIQUE,
    departamento_id INTEGER REFERENCES departments(id),
    cargo VARCHAR(100),
    data_admissao DATE,
    data_nascimento DATE,
    genero VARCHAR(20),
    estado_civil VARCHAR(20),
    endereco TEXT,
    telefone VARCHAR(20),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Departamentos
CREATE TABLE departments (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    codigo VARCHAR(20) UNIQUE,
    gestor_id INTEGER REFERENCES users(id),
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE
);

-- Férias
CREATE TABLE ferias (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    dias INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pendente', -- pendente, aprovado, rejeitado, cancelado
    aprovador_id INTEGER REFERENCES users(id),
    comentario TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Ciclos de avaliação
CREATE TABLE ciclos_avaliacao (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    tipo VARCHAR(20) NOT NULL, -- 360, gestor, autoavaliacao
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Avaliações
CREATE TABLE avaliacoes (
    id SERIAL PRIMARY KEY,
    ciclo_id INTEGER REFERENCES ciclos_avaliacao(id),
    avaliador_id INTEGER REFERENCES users(id),
    avaliado_id INTEGER REFERENCES users(id),
    respostas JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'rascunho', -- rascunho, enviado, concluido
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Onboarding
CREATE TABLE onboarding_etapas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    etapa VARCHAR(100) NOT NULL,
    concluida BOOLEAN DEFAULT FALSE,
    data_conclusao TIMESTAMP,
    responsavel_id INTEGER REFERENCES users(id),
    UNIQUE (user_id, etapa)
);

-- Treinamentos
CREATE TABLE treinamentos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    data_inicio TIMESTAMP NOT NULL,
    data_fim TIMESTAMP NOT NULL,
    local VARCHAR(255),
    instrutor VARCHAR(255),
    capacidade INTEGER,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Inscrições em treinamentos
CREATE TABLE treinamento_inscricoes (
    id SERIAL PRIMARY KEY,
    treinamento_id INTEGER REFERENCES treinamentos(id),
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'inscrito', -- inscrito, presente, ausente, certificado
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Feedback
CREATE TABLE feedbacks (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER REFERENCES users(id),
    to_user_id INTEGER REFERENCES users(id),
    message TEXT NOT NULL,
    type VARCHAR(20) DEFAULT 'publico', -- publico, privado
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Kudos
CREATE TABLE kudos (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER REFERENCES users(id),
    to_user_id INTEGER REFERENCES users(id),
    message TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW()
);
```

### Índices Importantes

```sql
CREATE INDEX idx_users_nome ON users USING gin (to_tsvector('portuguese', nome));
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_departamento ON users(departamento_id);
CREATE INDEX idx_users_data_admissao ON users(data_admissao);
CREATE INDEX idx_ferias_usuario ON ferias(user_id);
CREATE INDEX idx_ferias_data ON ferias(data_inicio);
CREATE INDEX idx_avaliacoes_ciclo ON avaliacoes(ciclo_id);
CREATE INDEX idx_avaliacoes_avaliado ON avaliacoes(avaliado_id);
CREATE INDEX idx_onboarding_usuario ON onboarding_etapas(user_id);
CREATE INDEX idx_treinamentos_data ON treinamentos(data_inicio);
CREATE INDEX idx_feedback_usuario ON feedbacks(to_user_id);
```

## Integração com Outros Apps

### Integração com Atlas

1. **Sincronização de Usuários**:
   - Dados básicos: nome, email, status
   - Atualização diária via webhook
   - Desativação automática de usuários

2. **Autenticação**:
   - Validação de token JWT
   - Verificação de permissões
   - Cache de 5 minutos

### Integração com Cronos

1. **Jornadas de Trabalho**:
   - Sincronização de jornadas
   - Atribuição a colaboradores
   - Atualização de mudanças

2. **Férias**:
   - Bloqueio de ponto durante férias
   - Sincronização de datas
   - Relatórios consolidados

### Integração com Iris

1. **Workflows**:
   - Solicitação de férias
   - Aprovação de treinamentos
   - Processos de desligamento

2. **Documentos**:
   - Contratos de trabalho
   - Avaliações assinadas
   - Certificados de treinamento

## Processamento Assíncrono (Celery)

### Tarefas em Segundo Plano

```python
# tasks.py
@celery.task(bind=True)
def processar_onboarding(self, user_id):
    """Processa onboarding para novo colaborador"""
    user = User.query.get(user_id)
    template = OnboardingTemplate.query.filter_by(default=True).first()
    
    for etapa in template.etapas:
        onboarding = OnboardingEtapa(
            user_id=user.id,
            etapa=etapa.nome,
            descricao=etapa.descricao
        )
        db.session.add(onboarding)
    
    db.session.commit()
    
    # Enviar email de boas-vindas
    enviar_email_onboarding(user.email, user.nome)
    
    return f"Onboarding iniciado para {user.nome}"

@celery.task(bind=True)
def notificar_ferias_pendentes(self):
    """Notifica gestores sobre solicitações de férias pendentes"""
    ferias = Ferias.query.filter_by(status='pendente').all()
    
    for feria in ferias:
        gestor = get_gestor(feria.user_id)
        enviar_notificacao(
            gestor.email,
            f"Solicitação de férias pendente: {feria.user.nome}",
            f"Período: {feria.data_inicio} a {feria.data_fim}"
        )
    
    return f"Notificações enviadas para {len(set(f.gestor_id for f in ferias))} gestores"

@celery.task(bind=True)
def gerar_relatorio_turnover(self, ano):
    """Gera relatório mensal de turnover"""
    relatorio = calcular_turnover(ano)
    
    # Salvar relatório
    salvar_relatorio(relatorio, f'turnover_{ano}.pdf')
    
    # Enviar para RH
    enviar_email_rh(
        f"Relatório de Turnover {ano}",
        "Relatório anexo",
        [f'turnover_{ano}.pdf']
    )
    
    return f"Relatório de turnover {ano} gerado e enviado"
```

### Agendamento de Tarefas

```python
# Agendamento via Celery Beat
CELERYBEAT_SCHEDULE = {
    'notificar-ferias': {
        'task': 'tasks.notificar_ferias_pendentes',
        'schedule': crontab(hour=9, minute=0),  # Todos os dias às 9h
    },
    'gerar-turnover': {
        'task': 'tasks.gerar_relatorio_turnover',
        'schedule': crontab(day=1, hour=8, minute=0),  # Dia 1 de cada mês às 8h
        'args': (None,),  # ano será calculado
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

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por dados
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Dados pessoais criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Conformidade**:
   - LGPD compliance
   - Retenção de dados por 5 anos
   - Direito ao esquecimento

## Monitoramento e Logging

### Métricas Monitoradas

- Número de admissões/desligamentos
- Taxa de turnover
- Satisfação em avaliações
- Tempo médio de onboarding
- Solicitações de férias pendentes

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "hera",
  "action": "user_created",
  "user": "admin@olimpus.local",
  "target_user": "novo@olimpus.local",
  "ip": "192.168.1.100"
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
SECRET_KEY=hera_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/hera
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
ATLAS_URL=http://localhost:5010
CRONOS_URL=http://localhost:5025
IRIS_URL=http://localhost:5070
PORT=5041
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
gunicorn -w 4 -b 0.0.0.0:5041 app:app

# 6. Configurar systemd
cp hera.service /etc/systemd/system/
cp hera-worker.service /etc/systemd/system/
cp hera-beat.service /etc/systemd/system/

systemctl enable hera
systemctl enable hera-worker
systemctl enable hera-beat

systemctl start hera
systemctl start hera-worker
systemctl start hera-beat
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres hera > hera_db_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql -U postgres hera < hera_db_backup.sql
```

### Atualizações

1. Parar serviços: `systemctl stop hera*`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviços: `systemctl start hera*`
7. Verificar saúde: `curl http://localhost:5041/api/ping`