# Documentação Técnica - Hermes (Gestão de Ativos)

## Visão Geral

**Nome**: Hermes - Gestão de Ativos e Patrimônio
**Porta**: 5050
**Prioridade**: BAIXA
**Tecnologias**: Flask, React, PostgreSQL, QR Code
**Responsável**: Equipe de TI e Facilities

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Hermes - Gestão de Ativos] --> B[API REST]
    A --> C[Frontend React]
    A --> D[Banco de Dados]
    A --> E[Armazenamento]
    A --> F[Integração]
    B --> G[/api/ativos]
    B --> H[/api/movimentacoes]
    B --> I[/api/manutencoes]
    C --> J[Dashboard]
    C --> K[Cadastro de Ativos]
    C --> L[Movimentações]
    C --> M[Manutenções]
    D --> N[PostgreSQL]
    E --> O[MinIO]
    F --> P[Hera]
    F --> Q[Atlas]
```

### Fluxo de Gestão de Ativos

1. **Cadastro**: Ativo é registrado no sistema
2. **Etiquetagem**: QR Code é gerado
3. **Atribuição**: Ativo é atribuído a usuário/local
4. **Movimentação**: Ativo é transferido
5. **Manutenção**: Manutenções são registradas
6. **Baixa**: Ativo é baixado do patrimônio

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Ativos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ativos` | GET | Lista ativos | `?tipo=equipamento&status=ativo` |
| `/api/ativos` | POST | Cria ativo | `{"nome", "tipo", "valor"}` |
| `/api/ativos/<id>` | GET | Detalhes ativo | - |
| `/api/ativos/<id>` | PUT | Atualiza ativo | `{"nome", "localizacao"}` |
| `/api/ativos/<id>` | DELETE | Remove ativo | - |
| `/api/ativos/<id>/qrcode` | GET | Gera QR Code | - |
| `/api/ativos/<id>/baixa` | POST | Baixa ativo | `{"motivo"}` |

### Movimentações

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/movimentacoes` | GET | Lista movimentações | `?ativo_id=1` |
| `/api/movimentacoes` | POST | Registra movimentação | `{"ativo_id", "local_origem", "local_destino"}` |
| `/api/movimentacoes/<id>` | GET | Detalhes movimentação | - |

### Manutenções

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/manutencoes` | GET | Lista manutenções | `?ativo_id=1&status=pendente` |
| `/api/manutencoes` | POST | Agendar manutenção | `{"ativo_id", "tipo", "data"}` |
| `/api/manutencoes/<id>` | PUT | Atualiza manutenção | `{"status", "relatorio"}` |
| `/api/manutencoes/<id>/concluir` | POST | Conclui manutenção | `{"relatorio", "custo"}` |

### Localizações

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/localizacoes` | GET | Lista localizações | - |
| `/api/localizacoes` | POST | Cria localização | `{"nome", "descricao", "responsavel"}` |
| `/api/localizacoes/<id>` | GET | Detalhes localização | - |

### Relatórios

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/relatorios/ativos` | GET | Relatórios de ativos | `?tipo=equipamento` |
| `/api/relatorios/depreciacao` | GET | Depreciação | `?ano=2026` |
| `/api/relatorios/manutencoes` | GET | Manutenções | `?mes=4&ano=2026` |

### Integração com Hera

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/hera/sincronizar` | POST | Sincroniza usuários | - |
| `/api/hera/ativos` | GET | Ativos por usuário | `?user_id=1` |

## Banco de Dados

### Esquema Principal

```sql
-- Ativos
CREATE TABLE ativos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    tipo VARCHAR(100) NOT NULL, -- equipamento, mobiliario, veiculo, imovel
    codigo_patrimonio VARCHAR(50) UNIQUE,
    numero_serie VARCHAR(100),
    valor_aquisicao DECIMAL(15, 2),
    data_aquisicao DATE,
    vida_util INTEGER, -- em meses
    status VARCHAR(50) DEFAULT 'ativo', -- ativo, manutencao, baixado
    localizacao_id INTEGER REFERENCES localizacoes(id),
    responsavel_id INTEGER REFERENCES usuarios(id),
    departamento_id INTEGER,
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Movimentações
CREATE TABLE movimentacoes (
    id SERIAL PRIMARY KEY,
    ativo_id INTEGER REFERENCES ativos(id),
    local_origem_id INTEGER REFERENCES localizacoes(id),
    local_destino_id INTEGER REFERENCES localizacoes(id),
    usuario_origem_id INTEGER REFERENCES usuarios(id),
    usuario_destino_id INTEGER REFERENCES usuarios(id),
    data_movimentacao TIMESTAMP DEFAULT NOW(),
    motivo TEXT,
    observacoes TEXT,
    criado_por INTEGER REFERENCES usuarios(id)
);

-- Manutenções
CREATE TABLE manutencoes (
    id SERIAL PRIMARY KEY,
    ativo_id INTEGER REFERENCES ativos(id),
    tipo VARCHAR(50) NOT NULL, -- preventiva, corretiva
    data_agendamento TIMESTAMP NOT NULL,
    data_conclusao TIMESTAMP,
    status VARCHAR(50) DEFAULT 'agendada', -- agendada, em_andamento, concluida, cancelada
    responsavel_id INTEGER REFERENCES usuarios(id),
    custo DECIMAL(15, 2),
    relatorio TEXT,
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Localizações
CREATE TABLE localizacoes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    codigo VARCHAR(50) UNIQUE,
    tipo VARCHAR(50), -- sala, andar, predio, externo
    responsavel_id INTEGER REFERENCES usuarios(id),
    departamento_id INTEGER,
    capacidade INTEGER,
    ativa BOOLEAN DEFAULT TRUE
);

-- Usuários (sincronizado com Hera)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    hera_id INTEGER UNIQUE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    departamento_id INTEGER,
    cargo VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE
);

-- Depreciação
CREATE TABLE depreciacao (
    id SERIAL PRIMARY KEY,
    ativo_id INTEGER REFERENCES ativos(id),
    mes INTEGER NOT NULL,
    ano INTEGER NOT NULL,
    valor_depreciado DECIMAL(15, 2),
    valor_acumulado DECIMAL(15, 2),
    criado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE (ativo_id, mes, ano)
);
```

### Índices Importantes

```sql
CREATE INDEX idx_ativos_nome ON ativos USING gin (to_tsvector('portuguese', nome));
CREATE INDEX idx_ativos_tipo ON ativos(tipo);
CREATE INDEX idx_ativos_status ON ativos(status);
CREATE INDEX idx_ativos_localizacao ON ativos(localizacao_id);
CREATE INDEX idx_movimentacoes_ativo ON movimentacoes(ativo_id);
CREATE INDEX idx_movimentacoes_data ON movimentacoes(data_movimentacao);
CREATE INDEX idx_manutencoes_ativo ON manutencoes(ativo_id);
CREATE INDEX idx_manutencoes_status ON manutencoes(status);
CREATE INDEX idx_manutencoes_data ON manutencoes(data_agendamento);
CREATE INDEX idx_localizacoes_nome ON localizacoes USING gin (to_tsvector('portuguese', nome));
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

## Integração com Outros Apps

### Integração com Hera (RH)

1. **Sincronização de Usuários**:
   - Dados de colaboradores
   - Departamentos
   - Status de ativação

2. **Atribuição de Ativos**:
   - Ativos atribuídos a usuários
   - Histórico de responsabilidade
   - Notificações de movimentação

### Integração com Atlas

1. **Autenticação**:
   - Validação de token JWT
   - Verificação de permissões
   - Cache de 5 minutos

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com curta expiração
   - Validação em todos os endpoints

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por ativo
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Dados sensíveis criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Controle Físico**:
   - QR Codes com assinatura digital
   - Validação de movimentações
   - Audit trail completo

## Monitoramento e Logging

### Métricas Monitoradas

- Número de ativos cadastrados
- Taxa de movimentações
- Manutenções pendentes
- Valor total do patrimônio
- Depreciação mensal

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "hermes",
  "action": "ativo_created",
  "user": "admin@olimpus.local",
  "ativo_id": 123,
  "nome": "Notebook Dell",
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- MinIO (ou S3 compatível)
- 2GB RAM mínima
- 10GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=hermes_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/hermes
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio_access
MINIO_SECRET_KEY=minio_secret
ATLAS_URL=http://localhost:5010
HERA_URL=http://localhost:5041
PORT=5050
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
flask db upgrade

# 3. Configurar MinIO
mc mb minio/hermes-qrcodes
mc policy set public minio/hermes-qrcodes

# 4. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5050 app:app

# 5. Configurar systemd
cp hermes.service /etc/systemd/system/
systemctl enable hermes
systemctl start hermes
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres hermes > hermes_db_backup_$(date +%Y%m%d).sql

# Backup MinIO
mc mirror minio/hermes-qrcodes /backup/hermes-qrcodes-$(date +%Y%m%d)

# Restore PostgreSQL
psql -U postgres hermes < hermes_db_backup.sql

# Restore MinIO
mc mirror /backup/hermes-qrcodes minio/hermes-qrcodes
```

### Atualizações

1. Parar serviço: `systemctl stop hermes`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start hermes`
7. Verificar saúde: `curl http://localhost:5050/api/ping`