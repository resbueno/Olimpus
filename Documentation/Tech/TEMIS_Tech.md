# Documentação Técnica - Têmis (Gestão de Contratos)

## Visão Geral

**Nome**: Têmis - Gestão de Contratos e Obrigações
**Porta**: 5020 (conflito conhecido com Héstia)
**Prioridade**: ALTA
**Tecnologias**: Flask, React, PostgreSQL, DocuSign
**Responsável**: Equipe Jurídica

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Têmis - Gestão de Contratos] --> B[API REST]
    A --> C[Frontend React]
    A --> D[Banco de Dados]
    A --> E[Armazenamento]
    A --> F[Integração]
    B --> G[/api/contratos]
    B --> H[/api/aprovacoes]
    B --> I[/api/obrigacoes]
    C --> J[Dashboard]
    C --> K[Cadastro de Contratos]
    C --> L[Workflow de Aprovação]
    C --> M[Gestão de Obrigações]
    D --> N[PostgreSQL]
    E --> O[MinIO]
    F --> P[DocuSign]
    F --> Q[Atlas]
```

### Fluxo de Gestão de Contratos

1. **Solicitação**: Novo contrato é solicitado
2. **Redação**: Contrato é redigido
3. **Aprovação**: Workflow de aprovação
4. **Assinatura**: Assinatura digital
5. **Arquivamento**: Contrato é arquivado
6. **Monitoramento**: Obrigações são monitoradas
7. **Renovação**: Processo de renovação

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Contratos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/contratos` | GET | Lista contratos | `?status=ativo&tipo=servico` |
| `/api/contratos` | POST | Cria contrato | `{"titulo", "tipo", "valor"}` |
| `/api/contratos/<id>` | GET | Detalhes contrato | - |
| `/api/contratos/<id>` | PUT | Atualiza contrato | `{"titulo", "descricao"}` |
| `/api/contratos/<id>` | DELETE | Remove contrato | - |
| `/api/contratos/<id>/anexos` | GET | Lista anexos | - |
| `/api/contratos/<id>/anexos` | POST | Adiciona anexo | `file + {"descricao"}` |

### Aprovações

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/contratos/<id>/aprovacoes` | GET | Lista aprovações | - |
| `/api/contratos/<id>/aprovacoes` | POST | Solicita aprovação | `{"aprovador_id", "comentario"}` |
| `/api/aprovacoes/<id>` | PUT | Aprova/Rejeita | `{"status", "comentario"}` |
| `/api/aprovacoes/<id>/delegar` | POST | Delega aprovação | `{"user_id"}` |

### Obrigações

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/obrigacoes` | GET | Lista obrigações | `?contrato_id=1&status=pendente` |
| `/api/obrigacoes` | POST | Cria obrigação | `{"contrato_id", "descricao", "data"}` |
| `/api/obrigacoes/<id>` | PUT | Atualiza obrigação | `{"status", "comentario"}` |
| `/api/obrigacoes/<id>/concluir` | POST | Conclui obrigação | `{"evidencia"}` |

### Renovações

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/renovacoes` | GET | Lista renovações | `?status=pendente` |
| `/api/contratos/<id>/renovar` | POST | Solicita renovação | `{"nova_data_fim", "valor_novo"}` |
| `/api/renovacoes/<id>` | PUT | Aprova renovação | `{"comentario"}` |

### Relatórios

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/relatorios/contratos` | GET | Relatórios de contratos | `?tipo=servico&ano=2026` |
| `/api/relatorios/obrigacoes` | GET | Relatórios de obrigações | `?mes=4&ano=2026` |
| `/api/relatorios/renovacoes` | GET | Relatórios de renovações | `?proximos=3` |
| `/api/relatorios/alertas` | GET | Alertas de vencimento | - |

### Integração com DocuSign

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/docusign/envelope` | POST | Cria envelope | `{"contrato_id", "signatarios"}` |
| `/api/docusign/<id>/status` | GET | Status do envelope | - |
| `/api/docusign/<id>/documento` | GET | Baixa documento assinado | - |

## Banco de Dados

### Esquema Principal

```sql
-- Contratos
CREATE TABLE contratos (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    tipo VARCHAR(100) NOT NULL, -- servico, compra, aluguel, parceria
    numero VARCHAR(100) UNIQUE,
    valor DECIMAL(15, 2),
    data_inicio DATE NOT NULL,
    data_fim DATE NOT NULL,
    data_assinatura DATE,
    status VARCHAR(50) DEFAULT 'rascunho', -- rascunho, revisao, aprovacao, assinado, ativo, encerrado
    parte_contratante VARCHAR(255) NOT NULL,
    parte_contratada VARCHAR(255) NOT NULL,
    responsavel_id INTEGER REFERENCES usuarios(id),
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Anexos
CREATE TABLE contrato_anexos (
    id SERIAL PRIMARY KEY,
    contrato_id INTEGER REFERENCES contratos(id),
    nome_arquivo VARCHAR(255) NOT NULL,
    caminho_arquivo VARCHAR(512) NOT NULL,
    tipo VARCHAR(100),
    tamanho INTEGER,
    descricao TEXT,
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Aprovações
CREATE TABLE aprovacoes (
    id SERIAL PRIMARY KEY,
    contrato_id INTEGER REFERENCES contratos(id),
    etapa VARCHAR(100) NOT NULL, -- juridico, financeiro, gestor
    aprovador_id INTEGER REFERENCES usuarios(id),
    status VARCHAR(50) DEFAULT 'pendente', -- pendente, aprovado, rejeitado, delegado
    comentario TEXT,
    data_limite TIMESTAMP,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Obrigações
CREATE TABLE obrigacoes (
    id SERIAL PRIMARY KEY,
    contrato_id INTEGER REFERENCES contratos(id),
    descricao TEXT NOT NULL,
    tipo VARCHAR(100), -- pagamento, entrega, relatorio
    data_vencimento DATE NOT NULL,
    data_conclusao DATE,
    status VARCHAR(50) DEFAULT 'pendente', -- pendente, concluida, atrasada, cancelada
    responsavel_id INTEGER REFERENCES usuarios(id),
    valor DECIMAL(15, 2),
    evidencia TEXT,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Renovações
CREATE TABLE renovacoes (
    id SERIAL PRIMARY KEY,
    contrato_id INTEGER REFERENCES contratos(id),
    data_solicitacao TIMESTAMP DEFAULT NOW(),
    data_aprovacao TIMESTAMP,
    nova_data_fim DATE NOT NULL,
    novo_valor DECIMAL(15, 2),
    status VARCHAR(50) DEFAULT 'pendente', -- pendente, aprovado, rejeitado, cancelado
    aprovador_id INTEGER REFERENCES usuarios(id),
    comentario TEXT,
    criado_por INTEGER REFERENCES usuarios(id)
);

-- Alertas
CREATE TABLE alertas (
    id SERIAL PRIMARY KEY,
    contrato_id INTEGER REFERENCES contratos(id),
    tipo VARCHAR(100) NOT NULL, -- vencimento, obrigacao, renovacao
    data_alerta TIMESTAMP DEFAULT NOW(),
    data_referencia DATE NOT NULL,
    dias_antecedencia INTEGER,
    status VARCHAR(50) DEFAULT 'pendente', -- pendente, notificado, resolvido
    mensagem TEXT
);

-- Usuários (sincronizado com Atlas)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    atlas_id INTEGER UNIQUE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    departamento_id INTEGER,
    cargo VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE
);

-- DocuSign Envelopes
CREATE TABLE docusign_envelopes (
    id SERIAL PRIMARY KEY,
    contrato_id INTEGER REFERENCES contratos(id),
    envelope_id VARCHAR(255) NOT NULL,
    status VARCHAR(100),
    data_envio TIMESTAMP DEFAULT NOW(),
    data_conclusao TIMESTAMP,
    documento_url VARCHAR(512),
    signatarios JSONB
);
```

### Índices Importantes

```sql
CREATE INDEX idx_contratos_titulo ON contratos USING gin (to_tsvector('portuguese', titulo));
CREATE INDEX idx_contratos_status ON contratos(status);
CREATE INDEX idx_contratos_data_fim ON contratos(data_fim);
CREATE INDEX idx_contratos_tipo ON contratos(tipo);
CREATE INDEX idx_anexos_contrato ON contrato_anexos(contrato_id);
CREATE INDEX idx_aprovacoes_contrato ON aprovacoes(contrato_id);
CREATE INDEX idx_aprovacoes_status ON aprovacoes(status);
CREATE INDEX idx_obrigacoes_contrato ON obrigacoes(contrato_id);
CREATE INDEX idx_obrigacoes_data ON obrigacoes(data_vencimento);
CREATE INDEX idx_obrigacoes_status ON obrigacoes(status);
CREATE INDEX idx_renovacoes_contrato ON renovacoes(contrato_id);
CREATE INDEX idx_renovacoes_status ON renovacoes(status);
CREATE INDEX idx_alertas_data ON alertas(data_referencia);
CREATE INDEX idx_alertas_status ON alertas(status);
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

## Integração com Outros Apps

### Integração com DocuSign

1. **Envio para Assinatura**:
   - Contrato é enviado para DocuSign
   - Signatários são configurados
   - Campos de assinatura são definidos
   - Envelope é criado

2. **Acompanhamento**:
   - Status do envelope é monitorado
   - Notificações de progresso
   - Documento assinado é baixado
   - Contrato é marcado como assinado

### Integração com Atlas

1. **Autenticação**:
   - Validação de token JWT
   - Verificação de permissões
   - Cache de 5 minutos

2. **Sincronização**:
   - Dados básicos de usuário
   - Departamentos
   - Status de ativação

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com curta expiração
   - Validação em todos os endpoints

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por contrato
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Documentos criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Conformidade**:
   - LGPD compliance
   - Retenção de dados por 10 anos
   - Audit trail completo

## Monitoramento e Logging

### Métricas Monitoradas

- Número de contratos ativos
- Contratos próximos do vencimento
- Obrigações pendentes
- Tempo médio de aprovação
- Taxa de renovação

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "temis",
  "action": "contrato_created",
  "user": "admin@olimpus.local",
  "contrato_id": 123,
  "titulo": "Contrato de Serviços TI",
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- MinIO (ou S3 compatível)
- DocuSign API
- 4GB RAM mínima
- 50GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=temis_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/temis
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio_access
MINIO_SECRET_KEY=minio_secret
DOCUSIGN_CLIENT_ID=your_client_id
DOCUSIGN_CLIENT_SECRET=your_client_secret
DOCUSIGN_REDIRECT_URI=http://localhost:5020/api/docusign/callback
ATLAS_URL=http://localhost:5010
PORT=5020
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar MinIO
mc mb minio/temis-documents
mc policy set public minio/temis-documents

# 3. Configurar banco de dados
flask db upgrade

# 4. Configurar DocuSign
# Seguir processo de OAuth para obter tokens

# 5. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5020 app:app

# 6. Configurar systemd
cp temis.service /etc/systemd/system/
systemctl enable temis
systemctl start temis
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres temis > temis_db_backup_$(date +%Y%m%d).sql

# Backup MinIO
mc mirror minio/temis-documents /backup/temis-documents-$(date +%Y%m%d)

# Restore PostgreSQL
psql -U postgres temis < temis_db_backup.sql

# Restore MinIO
mc mirror /backup/temis-documents minio/temis-documents
```

### Atualizações

1. Parar serviço: `systemctl stop temis`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start temis`
7. Verificar saúde: `curl http://localhost:5020/api/ping`