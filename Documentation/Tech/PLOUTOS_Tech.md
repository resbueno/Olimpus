# Documentação Técnica - Ploutos (Gestão Financeira)

## Visão Geral

**Nome**: Ploutos - Gestão Financeira e Contabilidade
**Porta**: 5080
**Prioridade**: ALTA
**Tecnologias**: Flask, PostgreSQL, Redis
**Responsável**: Equipe Financeira

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Ploutos - Gestão Financeira] --> B[API REST]
    A --> C[Frontend]
    A --> D[Banco de Dados]
    A --> E[Cache]
    A --> F[Integração]
    B --> G[/api/lancamentos]
    B --> H[/api/contas]
    B --> I[/api/relatorios]
    C --> J[Dashboard]
    C --> K[Lançamentos]
    C --> L[Relatórios]
    D --> M[PostgreSQL]
    E --> N[Redis]
    F --> O[Iris]
    F --> P[Atlas]
```

### Fluxo Financeiro

1. **Lançamento**: Usuário registra transação
2. **Validação**: Sistema valida regras contábeis
3. **Armazenamento**: Transação salva no banco
4. **Consolidação**: Dados agregados para relatórios
5. **Análise**: Gestores analisam resultados
6. **Exportação**: Dados enviados para contabilidade

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Lançamentos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/lancamentos` | GET | Lista lançamentos | `?conta_id=1&mes=4&ano=2026` |
| `/api/lancamentos` | POST | Cria lançamento | `{"descricao", "valor", "tipo", "conta_id"}` |
| `/api/lancamentos/<id>` | GET | Detalhes lançamento | - |
| `/api/lancamentos/<id>` | PUT | Atualiza lançamento | `{"descricao", "valor"}` |
| `/api/lancamentos/<id>` | DELETE | Remove lançamento | - |

### Contas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/contas` | GET | Lista contas | `?tipo=receita` |
| `/api/contas` | POST | Cria conta | `{"nome", "tipo", "categoria"}` |
| `/api/contas/<id>` | GET | Detalhes conta | - |
| `/api/contas/<id>` | PUT | Atualiza conta | `{"nome", "categoria"}` |

### Fluxo de Caixa

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/fluxo-caixa` | GET | Fluxo de caixa | `?mes=4&ano=2026` |
| `/api/fluxo-caixa/projecao` | GET | Projeção | `?meses=3` |
| `/api/fluxo-caixa/saldo` | GET | Saldo atual | - |

### Contas a Pagar/Receber

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/contas-pagar` | GET | Contas a pagar | `?status=pendente` |
| `/api/contas-pagar` | POST | Cria conta a pagar | `{"descricao", "valor", "data_vencimento"}` |
| `/api/contas-pagar/<id>/pagar` | POST | Registra pagamento | `{"data_pagamento", "valor_pago"}` |
| `/api/contas-receber` | GET | Contas a receber | `?status=pendente` |
| `/api/contas-receber` | POST | Cria conta a receber | `{"descricao", "valor", "data_vencimento"}` |
| `/api/contas-receber/<id>/receber` | POST | Registra recebimento | `{"data_recebimento", "valor_recebido"}` |

### Relatórios

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/relatorios/mensal` | GET | Relatórios mensais | `?mes=4&ano=2026` |
| `/api/relatorios/anual` | GET | Relatórios anuais | `?ano=2026` |
| `/api/relatorios/dre` | GET | DRE | `?mes=4&ano=2026` |
| `/api/relatorios/balanco` | GET | Balanço patrimonial | `?mes=4&ano=2026` |

### Integração com Iris

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/iris/solicitacoes` | GET | Solicitações de compra | `?status=aprovado` |
| `/api/iris/<id>/aprovar` | POST | Aprovar solicitação | `{"valor_aprovado"}` |
| `/api/iris/<id>/rejeitar` | POST | Rejeitar solicitação | `{"motivo"}` |

## Banco de Dados

### Esquema Principal

```sql
-- Lançamentos financeiros
CREATE TABLE lancamentos (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL,
    valor DECIMAL(15, 2) NOT NULL,
    tipo VARCHAR(20) NOT NULL, -- receita, despesa
    data DATE NOT NULL,
    conta_id INTEGER REFERENCES contas(id),
    categoria_id INTEGER REFERENCES categorias(id),
    centro_custo_id INTEGER REFERENCES centros_custo(id),
    projeto_id INTEGER REFERENCES projetos(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    documento VARCHAR(100),
    observacoes TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Contas contábeis
CREATE TABLE contas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    codigo VARCHAR(50) UNIQUE,
    tipo VARCHAR(20) NOT NULL, -- ativo, passivo, receita, despesa, patrimonio
    categoria VARCHAR(100),
    ativa BOOLEAN DEFAULT TRUE,
    saldo_inicial DECIMAL(15, 2) DEFAULT 0.00
);

-- Categorias
CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL, -- receita, despesa
    descricao TEXT
);

-- Centros de custo
CREATE TABLE centros_custo (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    codigo VARCHAR(50) UNIQUE,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE
);

-- Projetos
CREATE TABLE projetos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    codigo VARCHAR(50) UNIQUE,
    data_inicio DATE,
    data_fim DATE,
    orcamento DECIMAL(15, 2),
    gestor_id INTEGER REFERENCES usuarios(id),
    ativo BOOLEAN DEFAULT TRUE
);

-- Contas a pagar
CREATE TABLE contas_pagar (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL,
    valor DECIMAL(15, 2) NOT NULL,
    data_vencimento DATE NOT NULL,
    data_pagamento DATE,
    valor_pago DECIMAL(15, 2),
    status VARCHAR(20) DEFAULT 'pendente', -- pendente, pago, cancelado
    fornecedor_id INTEGER REFERENCES fornecedores(id),
    conta_id INTEGER REFERENCES contas(id),
    centro_custo_id INTEGER REFERENCES centros_custo(id),
    projeto_id INTEGER REFERENCES projetos(id),
    documento VARCHAR(100),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Contas a receber
CREATE TABLE contas_receber (
    id SERIAL PRIMARY KEY,
    descricao VARCHAR(255) NOT NULL,
    valor DECIMAL(15, 2) NOT NULL,
    data_vencimento DATE NOT NULL,
    data_recebimento DATE,
    valor_recebido DECIMAL(15, 2),
    status VARCHAR(20) DEFAULT 'pendente', -- pendente, recebido, cancelado
    cliente_id INTEGER REFERENCES clientes(id),
    conta_id INTEGER REFERENCES contas(id),
    centro_custo_id INTEGER REFERENCES centros_custo(id),
    projeto_id INTEGER REFERENCES projetos(id),
    documento VARCHAR(100),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Usuários (sincronizado com Atlas)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    atlas_id INTEGER UNIQUE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    departamento_id INTEGER,
    ativo BOOLEAN DEFAULT TRUE
);

-- Fornecedores
CREATE TABLE fornecedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    email VARCHAR(255),
    telefone VARCHAR(20),
    endereco TEXT,
    ativo BOOLEAN DEFAULT TRUE
);

-- Clientes
CREATE TABLE clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cnpj_cpf VARCHAR(18) UNIQUE,
    email VARCHAR(255),
    telefone VARCHAR(20),
    endereco TEXT,
    ativo BOOLEAN DEFAULT TRUE
);
```

### Índices Importantes

```sql
CREATE INDEX idx_lancamentos_data ON lancamentos(data);
CREATE INDEX idx_lancamentos_conta ON lancamentos(conta_id);
CREATE INDEX idx_lancamentos_tipo ON lancamentos(tipo);
CREATE INDEX idx_contas_tipo ON contas(tipo);
CREATE INDEX idx_contas_pagar_status ON contas_pagar(status);
CREATE INDEX idx_contas_pagar_vencimento ON contas_pagar(data_vencimento);
CREATE INDEX idx_contas_receber_status ON contas_receber(status);
CREATE INDEX idx_contas_receber_vencimento ON contas_receber(data_vencimento);
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

## Integração com Outros Apps

### Integração com Iris

1. **Solicitações de Compra**:
   - Recebe solicitações aprovadas
   - Cria contas a pagar
   - Registra lançamento financeiro

2. **Aprovação Financeira**:
   - Valida limites de aprovação
   - Verifica orçamento disponível
   - Aprova ou rejeita solicitações

### Integração com Atlas

1. **Autenticação**:
   - Validação de token JWT
   - Verificação de permissões
   - Cache de 5 minutos

2. **Sincronização**:
   - Dados básicos de usuário
   - Status de ativação
   - Departamentos

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com curta expiração
   - Validação em todos os endpoints

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por dados
   - Acesso restrito a dados financeiros

3. **Proteção de Dados**:
   - Dados sensíveis criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Conformidade**:
   - Lei Sarbanes-Oxley compliance
   - Retenção de dados por 7 anos
   - Audit trail completo

## Monitoramento e Logging

### Métricas Monitoradas

- Volume de lançamentos por dia
- Saldo médio de contas
- Contas a pagar/receber vencidas
- Tempo médio de pagamento
- Precisão de projeções

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "ploutos",
  "action": "lancamento_created",
  "user": "admin@olimpus.local",
  "lancamento_id": 123,
  "valor": 1000.00,
  "tipo": "despesa",
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- 4GB RAM mínima
- 20GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=ploutos_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/ploutos
REDIS_URL=redis://localhost:6379/0
ATLAS_URL=http://localhost:5010
IRIS_URL=http://localhost:5070
PORT=5080
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
flask db upgrade

# 3. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5080 app:app

# 4. Configurar systemd
cp ploutos.service /etc/systemd/system/
systemctl enable ploutos
systemctl start ploutos
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres ploutos > ploutos_db_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql -U postgres ploutos < ploutos_db_backup.sql
```

### Atualizações

1. Parar serviço: `systemctl stop ploutos`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start ploutos`
7. Verificar saúde: `curl http://localhost:5080/api/ping`