# Documentação Técnica - Héstia (Intranet Corporativa)

## Visão Geral

**Nome**: Héstia - Intranet e Colaboração
**Porta**: 5020
**Prioridade**: ALTA
**Tecnologias**: Flask, React, PostgreSQL, Elasticsearch
**Responsável**: Equipe de Comunicação Interna

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Héstia - Intranet] --> B[API REST]
    A --> C[Frontend React]
    A --> D[Banco de Dados]
    A --> E[Busca]
    A --> F[Armazenamento]
    B --> G[/api/news]
    B --> H[/api/documents]
    B --> I[/api/people]
    B --> J[/api/communities]
    C --> K[Dashboard]
    C --> L[News Feed]
    C --> M[Document Library]
    C --> N[People Directory]
    D --> O[PostgreSQL]
    E --> P[Elasticsearch]
    F --> Q[MinIO]
```

### Fluxo de Informação

1. **Publicação**: Usuário cria notícia ou documento
2. **Armazenamento**: Conteúdo salvo no banco e arquivos no MinIO
3. **Indexação**: Elasticsearch indexa conteúdo para busca
4. **Exibição**: Frontend busca e exibe conteúdo
5. **Interação**: Usuários comentam, curtem e compartilham

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |
| `/api/auth/logout` | POST | Encerra sessão | - | `{"ok": true}` |

### Notícias

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/news` | GET | Lista notícias | `?limit=10&offset=0` |
| `/api/news` | POST | Cria notícia | `{"title", "content", "tags"}` |
| `/api/news/<id>` | GET | Detalhes da notícia | - |
| `/api/news/<id>` | PUT | Atualiza notícia | `{"title", "content"}` |
| `/api/news/<id>` | DELETE | Remove notícia | - |
| `/api/news/<id>/like` | POST | Curtir notícia | - |
| `/api/news/<id>/comments` | GET | Comentários | - |
| `/api/news/<id>/comments` | POST | Adicionar comentário | `{"content"}` |

### Documentos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/documents` | GET | Lista documentos | `?folder=root` |
| `/api/documents` | POST | Upload documento | `file + {"folder", "tags"}` |
| `/api/documents/<id>` | GET | Detalhes documento | - |
| `/api/documents/<id>/download` | GET | Baixar documento | - |
| `/api/documents/<id>` | DELETE | Remover documento | - |
| `/api/documents/folders` | GET | Lista pastas | - |
| `/api/documents/folders` | POST | Criar pasta | `{"name", "parent"}` |

### Diretório de Pessoas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/people` | GET | Lista pessoas | `?search=nome&departamento=TI` |
| `/api/people/<id>` | GET | Perfil detalhado | - |
| `/api/people/birthdays` | GET | Aniversariantes | `?month=4` |
| `/api/people/kudos` | GET | Lista kudos | `?limit=10` |
| `/api/people/kudos` | POST | Enviar kudos | `{"to_person_id", "message"}` |

### Comunidades

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/communities` | GET | Lista comunidades | - |
| `/api/communities` | POST | Criar comunidade | `{"name", "description"}` |
| `/api/communities/<id>` | GET | Detalhes comunidade | - |
| `/api/communities/<id>/members` | GET | Membros | - |
| `/api/communities/<id>/join` | POST | Entrar na comunidade | - |

### Eventos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/events` | GET | Lista eventos | `?from=2026-04-01&to=2026-04-30` |
| `/api/events` | POST | Criar evento | `{"title", "date", "location"}` |
| `/api/events/<id>` | GET | Detalhes evento | - |
| `/api/events/<id>/rsvp` | POST | Confirmar presença | `{"attending": true}` |

### Estatísticas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/stats` | GET | Estatísticas gerais | - |
| `/api/stats/news` | GET | Estatísticas de notícias | - |
| `/api/stats/documents` | GET | Estatísticas de documentos | - |
| `/api/stats/people` | GET | Estatísticas de pessoas | - |

## Banco de Dados

### Esquema Principal

```sql
-- Notícias
CREATE TABLE news (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER REFERENCES pessoas(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    published BOOLEAN DEFAULT TRUE,
    views INTEGER DEFAULT 0
);

-- Documentos
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size INTEGER,
    file_type VARCHAR(100),
    folder_id INTEGER REFERENCES document_folders(id),
    author_id INTEGER REFERENCES pessoas(id),
    created_at TIMESTAMP DEFAULT NOW(),
    tags VARCHAR(255)[]
);

-- Pessoas (sincronizado com Atlas)
CREATE TABLE pessoas (
    id SERIAL PRIMARY KEY,
    atlas_id INTEGER UNIQUE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    departamento VARCHAR(100),
    cargo VARCHAR(100),
    data_nascimento DATE,
    foto_url VARCHAR(512),
    ativo BOOLEAN DEFAULT TRUE
);

-- Comunidades
CREATE TABLE communities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    creator_id INTEGER REFERENCES pessoas(id),
    created_at TIMESTAMP DEFAULT NOW(),
    private BOOLEAN DEFAULT FALSE
);

-- Eventos
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    location VARCHAR(255),
    organizer_id INTEGER REFERENCES pessoas(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Índices Importantes

```sql
CREATE INDEX idx_news_title ON news USING gin (to_tsvector('portuguese', title));
CREATE INDEX idx_news_created ON news(created_at);
CREATE INDEX idx_documents_name ON documents USING gin (to_tsvector('portuguese', name));
CREATE INDEX idx_documents_folder ON documents(folder_id);
CREATE INDEX idx_pessoas_nome ON pessoas USING gin (to_tsvector('portuguese', nome));
CREATE INDEX idx_pessoas_departamento ON pessoas(departamento);
CREATE INDEX idx_events_date ON events(start_date);
```

## Integração com Outros Apps

### Sincronização com Atlas

1. **Dados de Usuário**:
   - Héstia sincroniza dados de pessoas do Atlas
   - Atualização diária via webhook
   - Dados: nome, email, departamento, status

2. **Autenticação**:
   - Validação de token JWT com Atlas
   - Verificação de permissões via roles
   - Cache de permissões por 5 minutos

### Integração com Hermes

- **Ativos**: Exibe ativos relacionados a pessoas
- **Localização**: Mostra localização de equipamentos
- **Manutenção**: Alertas de manutenção no perfil

### Integração com Cronos

- **Aniversários**: Dados de aniversário para Cronos
- **Férias**: Informações de férias no perfil
- **Jornada**: Horário de trabalho atual

## Frontend Architecture

### Estrutura de Componentes

```
src/
├── components/
│   ├── NewsCard.vue          # Cartão de notícia
│   ├── DocumentList.vue       # Lista de documentos
│   ├── PersonProfile.vue      # Perfil de pessoa
│   ├── CommunityCard.vue      # Cartão de comunidade
│   └── EventCalendar.vue      # Calendário de eventos
├── pages/
│   ├── Dashboard.vue          # Página inicial
│   ├── NewsFeed.vue           # Feed de notícias
│   ├── DocumentLibrary.vue    # Biblioteca de documentos
│   ├── PeopleDirectory.vue    # Diretório de pessoas
│   ├── Communities.vue        # Comunidades
│   └── Events.vue             # Eventos
├── services/
│   ├── news.js               # Serviço de notícias
│   ├── documents.js          # Serviço de documentos
│   ├── people.js             # Serviço de pessoas
│   └── search.js             # Serviço de busca
└── store/
    ├── news.js               # Estado das notícias
    ├── documents.js          # Estado dos documentos
    ├── people.js             # Estado das pessoas
    └── communities.js        # Estado das comunidades
```

### Busca Avançada

```javascript
// Serviço de busca com Elasticsearch
async function search(contentType, query, filters) {
  const params = {
    query: query,
    filters: filters,
    size: 20,
    from: 0
  };
  
  const response = await axios.post(
    `/api/search/${contentType}`,
    params
  );
  
  return response.data;
}

// Tipos de busca
search('news', 'projeto', { department: 'TI' });
search('documents', 'relatório', { type: 'pdf' });
search('people', 'joão', { department: 'RH' });
```

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT validados
   - Sessões com timeout

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por conteúdo
   - Proprietários podem gerenciar seu conteúdo

3. **Proteção de Dados**:
   - Documentos privados criptografados
   - Acesso a dados sensíveis auditado
   - Backups diários com retenção

4. **Upload de Arquivos**:
   - Verificação de vírus
   - Sanitização de nomes
   - Restrição de tipos de arquivo

## Monitoramento e Logging

### Métricas Monitoradas

- Número de notícias publicadas
- Documentos uploadados/downloaded
- Usuários ativos por dia
- Tempo médio de busca
- Erros de upload

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "hestia",
  "action": "news_created",
  "user": "admin@olimpus.local",
  "news_id": 123,
  "title": "Novo Projeto Iniciado",
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Elasticsearch 8+
- MinIO (ou S3 compatível)
- 4GB RAM mínima
- 50GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=hestia_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/hestia
ELASTICSEARCH_URL=http://localhost:9200
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minio_access
MINIO_SECRET_KEY=minio_secret
ATLAS_URL=http://localhost:5010
PORT=5020
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar Elasticsearch
curl -X PUT "localhost:9200/hestia_news" -H 'Content-Type: application/json' -d'{
  "settings": {
    "analysis": {
      "analyzer": {
        "portuguese_analyzer": {
          "tokenizer": "standard",
          "filter": ["lowercase", "portuguese_stop", "portuguese_stemmer"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": {"type": "text", "analyzer": "portuguese_analyzer"},
      "content": {"type": "text", "analyzer": "portuguese_analyzer"}
    }
  }
}'

# 3. Configurar banco de dados
flask db upgrade

# 4. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5020 app:app

# 5. Configurar systemd
cp hestia.service /etc/systemd/system/
systemctl enable hestia
systemctl start hestia
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres hestia > hestia_db_backup_$(date +%Y%m%d).sql

# Backup MinIO
mc mirror minio/hestia-documents /backup/hestia-documents-$(date +%Y%m%d)

# Restore PostgreSQL
psql -U postgres hestia < hestia_db_backup.sql

# Restore MinIO
mc mirror /backup/hestia-documents minio/hestia-documents
```

### Atualizações

1. Parar serviço: `systemctl stop hestia`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start hestia`
7. Verificar saúde: `curl http://localhost:5020/api/ping`