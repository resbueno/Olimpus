# Documentação Técnica - Tiresias (OCR)

## Visão Geral

**Nome**: Tiresias - Processamento OCR e Documentos
**Porta**: 5090
**Prioridade**: MÉDIA
**Tecnologias**: Flask, React, PostgreSQL, Tesseract, OpenCV
**Responsável**: Equipe de Digitalização

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Tiresias - OCR] --> B[API REST]
    A --> C[Frontend React]
    A --> D[Processamento]
    A --> E[Banco de Dados]
    A --> F[Armazenamento]
    B --> G[/api/ocr/upload]
    B --> H[/api/ocr/process]
    B --> I[/api/ocr/results]
    C --> J[Upload]
    C --> K[Processamento]
    C --> L[Resultados]
    D --> M[Tesseract]
    D --> N[OpenCV]
    E --> O[PostgreSQL]
    F --> P[MinIO]
```

### Fluxo de Processamento OCR

1. **Upload**: Documento é enviado
2. **Pré-processamento**: Imagem é preparada
3. **OCR**: Texto é extraído
4. **Pós-processamento**: Texto é limpo
5. **Validação**: Resultado é validado
6. **Armazenamento**: Resultados são salvos
7. **Exportação**: Dados são exportados

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Processamento OCR

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ocr/upload` | POST | Upload de documento | `file + {"template_id"}` |
| `/api/ocr/process` | POST | Processar documento | `{"document_id", "template_id"}` |
| `/api/ocr/status/<id>` | GET | Status de processamento | - |
| `/api/ocr/results/<id>` | GET | Resultados OCR | - |
| `/api/ocr/history` | GET | Histórico de processamentos | `?limit=10` |

### Templates

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ocr/templates` | GET | Lista templates | - |
| `/api/ocr/templates` | POST | Cria template | `{"nome", "config"}` |
| `/api/ocr/templates/<id>` | GET | Detalhes template | - |
| `/api/ocr/templates/<id>` | PUT | Atualiza template | `{"nome", "config"}` |

### Validação

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ocr/validate` | POST | Validar resultados | `{"document_id", "valid", "correcoes"}` |
| `/api/ocr/<id>/export` | POST | Exportar resultados | `{"format": "json"}` |

### Lote

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ocr/batch` | POST | Processamento em lote | `{"document_ids", "template_id"}` |
| `/api/ocr/batch/<id>/status` | GET | Status do lote | - |

## Banco de Dados

### Esquema Principal

```sql
-- Documentos
CREATE TABLE documentos (
    id SERIAL PRIMARY KEY,
    nome_arquivo VARCHAR(255) NOT NULL,
    caminho_arquivo VARCHAR(512) NOT NULL,
    tipo VARCHAR(100),
    tamanho INTEGER,
    status VARCHAR(50) DEFAULT 'uploaded', -- uploaded, processing, processed, validated, error
    template_id INTEGER REFERENCES templates(id),
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Resultados OCR
CREATE TABLE ocr_resultados (
    id SERIAL PRIMARY KEY,
    documento_id INTEGER REFERENCES documentos(id),
    texto_completo TEXT,
    dados_extraidos JSONB,
    confianca DECIMAL(5, 2),
    tempo_processamento INTEGER, -- em segundos
    status VARCHAR(50) DEFAULT 'raw', -- raw, validated, corrected
    validado_por INTEGER REFERENCES usuarios(id),
    validado_em TIMESTAMP,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Templates
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    config JSONB NOT NULL, -- Configuração de campos e regiões
    tipo_documento VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE,
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Processamento em lote
CREATE TABLE batch_processing (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, error
    total_documentos INTEGER DEFAULT 0,
    documentos_processados INTEGER DEFAULT 0,
    template_id INTEGER REFERENCES templates(id),
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    concluido_em TIMESTAMP
);

-- Batch documentos
CREATE TABLE batch_documentos (
    id SERIAL PRIMARY KEY,
    batch_id INTEGER REFERENCES batch_processing(id),
    documento_id INTEGER REFERENCES documentos(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, error
    resultado_id INTEGER REFERENCES ocr_resultados(id),
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
```

### Índices Importantes

```sql
CREATE INDEX idx_documentos_status ON documentos(status);
CREATE INDEX idx_documentos_template ON documentos(template_id);
CREATE INDEX idx_documentos_criado_em ON documentos(criado_em);
CREATE INDEX idx_resultados_documento ON ocr_resultados(documento_id);
CREATE INDEX idx_resultados_status ON ocr_resultados(status);
CREATE INDEX idx_templates_nome ON templates USING gin (to_tsvector('portuguese', nome));
CREATE INDEX idx_templates_tipo ON templates(tipo_documento);
CREATE INDEX idx_batch_status ON batch_processing(status);
CREATE INDEX idx_batch_criado_em ON batch_processing(criado_em);
CREATE INDEX idx_batch_documents_batch ON batch_documentos(batch_id);
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

## Integração com Outros Apps

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
   - Permissões granulares por documento
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Documentos criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Conformidade**:
   - LGPD compliance
   - Retenção de dados por 5 anos
   - Audit trail completo

## Monitoramento e Logging

### Métricas Monitoradas

- Número de documentos processados
- Tempo médio de processamento
- Taxa de sucesso
- Precisão do OCR
- Uso de CPU/GPU

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "tiresias",
  "action": "document_processed",
  "user": "admin@olimpus.local",
  "document_id": 123,
  "template": "NF-e",
  "time": 5.2,
  "confidence": 0.92,
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- MinIO (ou S3 compatível)
- Tesseract OCR
- OpenCV
- 8GB RAM mínima (16GB recomendado)
- GPU NVIDIA (recomendado para melhor performance)
- 50GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=tiresias_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/tiresias
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio_access
MINIO_SECRET_KEY=minio_secret
TESSERACT_PATH=/usr/bin/tesseract
TESSERACT_LANGUAGES=por+eng
ATLAS_URL=http://localhost:5010
PORT=5090
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Instalar Tesseract
apt-get install tesseract-ocr
apt-get install tesseract-ocr-por
apt-get install libtesseract-dev

# 3. Configurar banco de dados
flask db upgrade

# 4. Configurar MinIO
mc mb minio/tiresias-documents
mc policy set public minio/tiresias-documents

# 5. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5090 app:app

# 6. Configurar systemd
cp tiresias.service /etc/systemd/system/
systemctl enable tiresias
systemctl start tiresias
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres tiresias > tiresias_db_backup_$(date +%Y%m%d).sql

# Backup MinIO
mc mirror minio/tiresias-documents /backup/tiresias-documents-$(date +%Y%m%d)

# Restore PostgreSQL
psql -U postgres tiresias < tiresias_db_backup.sql

# Restore MinIO
mc mirror /backup/tiresias-documents minio/tiresias-documents
```

### Atualizações

1. Parar serviço: `systemctl stop tiresias`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start tiresias`
7. Verificar saúde: `curl http://localhost:5090/api/ping`