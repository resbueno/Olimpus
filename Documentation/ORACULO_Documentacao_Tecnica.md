# Documentação Técnica - Oráculo (Hub de Notícias)

## Visão Geral

**Nome**: Oráculo - Comunicação Corporativa
**Porta**: 5030
**Prioridade**: MÉDIA
**Tecnologias**: Flask, React, PostgreSQL, Elasticsearch
**Responsável**: Equipe de Comunicação Interna

## Arquitetura

### Componentos Principais

```mermaid
graph TD
    A[Oráculo - Hub de Notícias] --> B[API REST]
    A --> C[Frontend React]
    A --> D[Banco de Dados]
    A --> E[Busca]
    A --> F[Integração]
    B --> G[/api/noticias]
    B --> H[/api/categorias]
    B --> I[/api/comentarios]
    C --> J[News Feed]
    C --> K[Categorias]
    C --> L[Dashboard]
    D --> M[PostgreSQL]
    E --> N[Elasticsearch]
    F --> O[Hestia]
    F --> P[Atlas]
```

### Fluxo de Publicação

1. **Criação**: Autor cria notícia
2. **Revisão**: Editor revisa conteúdo
3. **Publicação**: Notícia é publicada
4. **Distribuição**: Notícia é distribuída
5. **Interação**: Usuários comentam e curtem
6. **Análise**: Métricas são coletadas

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Notícias

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/noticias` | GET | Lista notícias | `?categoria=ti&limit=10` |
| `/api/noticias` | POST | Cria notícia | `{"titulo", "conteudo", "categoria"}` |
| `/api/noticias/<id>` | GET | Detalhes notícia | - |
| `/api/noticias/<id>` | PUT | Atualiza notícia | `{"titulo", "conteudo"}` |
| `/api/noticias/<id>` | DELETE | Remove notícia | - |
| `/api/noticias/<id>/publicar` | POST | Publica notícia | - |
| `/api/noticias/<id>/like` | POST | Curtir notícia | - |

### Categorias

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/categorias` | GET | Lista categorias | - |
| `/api/categorias` | POST | Cria categoria | `{"nome", "descricao"}` |
| `/api/categorias/<id>` | GET | Detalhes categoria | - |
| `/api/categorias/<id>` | PUT | Atualiza categoria | `{"nome", "descricao"}` |

### Comentários

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/comentarios` | GET | Lista comentários | `?noticia_id=1` |
| `/api/comentarios` | POST | Cria comentário | `{"noticia_id", "conteudo"}` |
| `/api/comentarios/<id>` | PUT | Atualiza comentário | `{"conteudo"}` |
| `/api/comentarios/<id>` | DELETE | Remove comentário | - |

### Newsletter

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/newsletter` | GET | Lista newsletters | - |
| `/api/newsletter` | POST | Cria newsletter | `{"assunto", "conteudo", "departamentos"}` |
| `/api/newsletter/<id>/enviar` | POST | Envia newsletter | - |
| `/api/newsletter/inscricoes` | GET | Lista inscritos | `?departamento=ti` |

### Estatísticas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/stats` | GET | Estatísticas gerais | - |
| `/api/stats/noticias` | GET | Estatísticas de notícias | `?mes=4&ano=2026` |
| `/api/stats/engajamento` | GET | Métricas de engajamento | `?categoria=ti` |

### Integração com Hestia

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/hestia/sincronizar` | POST | Sincroniza notícias | - |
| `/api/hestia/noticias` | GET | Notícias para Hestia | `?limit=5` |

## Banco de Dados

### Esquema Principal

```sql
-- Notícias
CREATE TABLE noticias (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    resumo TEXT,
    categoria_id INTEGER REFERENCES categorias(id),
    autor_id INTEGER REFERENCES usuarios(id),
    data_publicacao TIMESTAMP,
    data_criacao TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'rascunho', -- rascunho, revisao, publicado, arquivado
    destaque BOOLEAN DEFAULT FALSE,
    imagem_capa VARCHAR(512),
    tags VARCHAR(255)[]
);

-- Categorias
CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    cor VARCHAR(20),
    icone VARCHAR(50),
    ativa BOOLEAN DEFAULT TRUE
);

-- Comentários
CREATE TABLE comentarios (
    id SERIAL PRIMARY KEY,
    noticia_id INTEGER REFERENCES noticias(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    conteudo TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    editado BOOLEAN DEFAULT FALSE
);

-- Curtidas
CREATE TABLE curtidas (
    id SERIAL PRIMARY KEY,
    noticia_id INTEGER REFERENCES noticias(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    UNIQUE (noticia_id, usuario_id)
);

-- Newsletter
CREATE TABLE newsletters (
    id SERIAL PRIMARY KEY,
    assunto VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    data_envio TIMESTAMP,
    enviado_por INTEGER REFERENCES usuarios(id),
    status VARCHAR(20) DEFAULT 'rascunho', -- rascunho, enviado, agendado
    data_agendamento TIMESTAMP
);

-- Inscrições em newsletter
CREATE TABLE newsletter_inscricoes (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(id),
    departamento_id INTEGER,
    ativa BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
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
```

### Índices Importantes

```sql
CREATE INDEX idx_noticias_titulo ON noticias USING gin (to_tsvector('portuguese', titulo));
CREATE INDEX idx_noticias_conteudo ON noticias USING gin (to_tsvector('portuguese', conteudo));
CREATE INDEX idx_noticias_categoria ON noticias(categoria_id);
CREATE INDEX idx_noticias_status ON noticias(status);
CREATE INDEX idx_noticias_data ON noticias(data_publicacao);
CREATE INDEX idx_comentarios_noticia ON comentarios(noticia_id);
CREATE INDEX idx_curtidas_noticia ON curtidas(noticia_id);
CREATE INDEX idx_newsletter_data ON newsletters(data_envio);
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

## Processos de Negócio

### 1. Publicação de Notícia

**Fluxo**:
1. Autor cria rascunho da notícia
2. Preenche título, conteúdo, categoria
3. Adiciona imagens e tags
4. Salva como rascunho
5. Envia para revisão
6. Editor revisa conteúdo
7. Editor aprova ou solicita correções
8. Notícia é publicada
9. Notificação enviada para assinantes

**Regras de Publicação**:
- Título deve ter 5-100 caracteres
- Conteúdo deve ter pelo menos 100 caracteres
- Deve ter pelo menos uma categoria
- Imagem de capa recomendada

### 2. Gestão de Newsletter

**Fluxo**:
1. Editor cria newsletter
2. Seleciona notícias e conteúdo
3. Define público-alvo
4. Agenda ou envia imediatamente
5. Sistema envia emails
6. Métricas de abertura são coletadas
7. Relatórios são gerados

**Tipos de Público**:
- Todos os usuários
- Departamento específico
- Função específica
- Usuários personalizados

### 3. Moderação de Comentários

**Fluxo**:
1. Usuário comenta em notícia
2. Comentário é salvo
3. Sistema verifica palavras proibidas
4. Comentário é publicado ou marcado para revisão
5. Moderador revisa se necessário
6. Comentário é aprovado ou rejeitado
7. Usuário é notificado

**Regras de Moderação**:
- Sem palavras ofensivas
- Sem links externos
- Máximo 500 caracteres
- Respeito às políticas da empresa

### 4. Análise de Engajamento

**Fluxo**:
1. Sistema coleta métricas de interação
2. Calcula taxas de engajamento
3. Identifica notícias populares
4. Gera relatórios para comunicação
5. Sugere melhorias de conteúdo
6. Ajusta estratégia de distribuição

**Métricas Chave**:
- Número de visualizações
- Taxa de curtidas
- Número de comentários
- Tempo médio de leitura
- Taxa de abertura (newsletter)

## Integração com Outros Apps

### Integração com Hestia

1. **Sincronização de Notícias**:
   - Notícias publicadas no Oráculo
   - Aparecem no feed da Hestia
   - Link para notícia completa

2. **Comentários**:
   - Comentários sincronizados
   - Usuários podem comentar em ambos
   - Notificações unificadas

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
   - Permissões granulares por conteúdo
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Dados pessoais criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Moderação**:
   - Filtro de palavras proibidas
   - Moderação manual quando necessário
   - Bloqueio de usuários problemáticos

## Monitoramento e Logging

### Métricas Monitoradas

- Número de notícias publicadas
- Engajamento por notícia
- Taxa de abertura de newsletter
- Comentários por dia
- Erros de publicação

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "oraculo",
  "action": "noticia_published",
  "user": "admin@olimpus.local",
  "noticia_id": 123,
  "titulo": "Novo Projeto Iniciado",
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Elasticsearch 8+
- Redis 6+
- 2GB RAM mínima
- 10GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=oraculo_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/oraculo
ELASTICSEARCH_URL=http://localhost:9200
REDIS_URL=redis://localhost:6379/0
ATLAS_URL=http://localhost:5010
HESTIA_URL=http://localhost:5020
PORT=5030
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
flask db upgrade

# 3. Configurar Elasticsearch
curl -X PUT "localhost:9200/oraculo_noticias" -H 'Content-Type: application/json' -d'
{
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
      "titulo": {"type": "text", "analyzer": "portuguese_analyzer"},
      "conteudo": {"type": "text", "analyzer": "portuguese_analyzer"}
    }
  }
}'

# 4. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5030 app:app

# 5. Configurar systemd
cp oraculo.service /etc/systemd/system/
systemctl enable oraculo
systemctl start oraculo
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres oraculo > oraculo_db_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql -U postgres oraculo < oraculo_db_backup.sql
```

### Atualizações

1. Parar serviço: `systemctl stop oraculo`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start oraculo`
7. Verificar saúde: `curl http://localhost:5030/api/ping`

## Solução de Problemas

### Problemas Comuns

1. **Notícias não aparecem**:
   - Verificar status de publicação
   - Verificar data de publicação
   - Verificar permissões

2. **Busca não funciona**:
   - Verificar conexão com Elasticsearch
   - Verificar índices estão criados
   - Reindexar conteúdo

3. **Newsletter não envia**:
   - Verificar configuração de email
   - Verificar lista de inscritos
   - Verificar logs de envio

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5030/api/ping

# Testar busca
curl -X POST http://localhost:5030/api/search -d '{"query": "teste"}' -H "Content-Type: application/json"

# Verificar status Elasticsearch
curl http://localhost:9200/_cluster/health

# Verificar logs
tail -f /var/log/oraculo/oraculo.log
```

## Roadmap

### Próximas Versões

- **v2.1**: Integração com Microsoft Teams
- **v2.2**: Editor de notícias avançado
- **v2.3**: Podcasts e vídeos
- **v2.4**: Gamificação e rankings

### Melhorias Planejadas

- Cache mais agressivo para conteúdo estático
- Busca por voz
- Integração com calendário corporativo
- Suporte a múltiplos idiomas
- API GraphQL para consultas complexas

## Contatos

**Suporte Técnico**: suporte@olimpus.local
**Comunicação Interna**: comunicacao@olimpus.local
**Desenvolvimento**: dev@olimpus.local