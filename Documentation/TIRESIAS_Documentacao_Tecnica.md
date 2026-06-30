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

## Processos de Negócio

### 1. Processamento de Documento

**Fluxo**:
1. Usuário faz upload do documento
2. Sistema valida tipo de arquivo
3. Documento é salvo no MinIO
4. Metadados são salvos no banco
5. Processamento OCR é iniciado
6. Texto é extraído
7. Dados são estruturados
8. Resultados são salvos
9. Usuário é notificado

**Tipos de Documento Suportados**:
- PDF
- JPEG/PNG
- TIFF
- DOCX (via conversão)

### 2. Validação de Resultados

**Fluxo**:
1. Usuário visualiza resultados OCR
2. Sistema destaca áreas de baixa confiança
3. Usuário corrige erros
4. Correções são salvas
5. Documento é marcado como validado
6. Dados são exportados
7. Relatório de qualidade é gerado

**Métricas de Qualidade**:
- Taxa de confiança média
- Número de correções
- Tempo de validação
- Precisão por campo

### 3. Processamento em Lote

**Fluxo**:
1. Usuário seleciona documentos
2. Define template de processamento
3. Inicia processamento em lote
4. Sistema processa documentos sequencialmente
5. Progresso é monitorado
6. Resultados são consolidados
7. Relatório final é gerado
8. Usuário é notificado

**Estratégias de Processamento**:
- Sequencial (padrão)
- Paralelo (para servidores potentes)
- Priorização por tipo de documento

### 4. Exportação de Dados

**Fluxo**:
1. Usuário seleciona documentos processados
2. Escolhe formato de exportação
3. Sistema gera arquivo
4. Dados são validados
5. Arquivo é disponibilizado para download
6. Exportação é registrada
7. Usuário recebe confirmação

**Formatos de Exportação**:
- JSON
- CSV
- Excel
- XML
- PDF (com OCR sobreposto)

## Processamento OCR

### Pré-processamento de Imagem

```python
def pre_processar_imagem(imagem):
    # Converter para escala de cinza
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    
    # Aplicar threshold
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Remover ruído
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    
    # Aumentar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    return enhanced
```

### Extração de Texto

```python
def extrair_texto(imagem, template=None):
    # Configurar Tesseract
    config = '--psm 6'
    if template and template['language']:
        config += f' -l {template["language"]}'
    
    # Extrair texto
    texto = pytesseract.image_to_string(imagem, config=config)
    
    # Extrair dados estruturados se template fornecido
    dados = {}
    if template and template['fields']:
        for field in template['fields']:
            x, y, w, h = field['region']
            roi = imagem[y:y+h, x:x+w]
            dados[field['name']] = pytesseract.image_to_string(roi)
    
    return {
        'texto_completo': texto,
        'dados_extraidos': dados,
        'confianca': calcular_confianca(texto)
    }
```

### Pós-processamento

```python
def pos_processar(texto, template=None):
    # Limpar texto
    texto_limpo = limpar_texto(texto)
    
    # Aplicar correções baseadas em template
    if template and template['correcoes']:
        for correcao in template['correcoes']:
            texto_limpo = texto_limpo.replace(correcao['de'], correcao['para'])
    
    # Extrair dados estruturados
    dados = extrair_dados_estruturados(texto_limpo, template)
    
    return {
        'texto': texto_limpo,
        'dados': dados
    }
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

## Solução de Problemas

### Problemas Comuns

1. **OCR não processa**:
   - Verificar Tesseract instalado
   - Verificar permissões de arquivo
   - Verificar logs de erro

2. **Baixa precisão**:
   - Verificar qualidade do documento
   - Ajustar pré-processamento
   - Usar template específico

3. **Processamento lento**:
   - Verificar uso de GPU
   - Reduzir tamanho da imagem
   - Processar em lote

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5090/api/ping

# Testar OCR
tesseract --version

# Verificar logs
tail -f /var/log/tiresias/tiresias.log
```

## Roadmap

### Próximas Versões

- **v2.1**: Suporte a mais idiomas
- **v2.2**: Reconhecimento de tabelas
- **v2.3**: Classificação automática de documentos
- **v2.4**: Integração com ABBYY FineReader

### Melhorias Planejadas

- Cache mais agressivo para dados estáticos
- Processamento paralelo com GPU
- Integração com mais engines OCR
- Suporte a múltiplos idiomas
- API GraphQL para consultas complexas

## Contatos

**Suporte Técnico**: suporte@olimpus.local
**Digitalização**: digitalizacao@olimpus.local
**Desenvolvimento**: dev@olimpus.local