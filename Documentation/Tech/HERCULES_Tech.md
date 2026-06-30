# Documentação Técnica - Hércules (Gestão de Tarefas)

## Visão Geral

**Nome**: Hércules - Gestão de Tarefas e Projetos
**Porta**: 5001
**Prioridade**: MÉDIA
**Tecnologias**: Flask, React, PostgreSQL, WebSockets
**Responsável**: Equipe de Produtividade

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Hércules - Gestão de Tarefas] --> B[API REST]
    A --> C[Frontend React]
    A --> D[Banco de Dados]
    A --> E[Tempo Real]
    A --> F[Integração]
    B --> G[/api/tarefas]
    B --> H[/api/projetos]
    B --> I[/api/quadros]
    C --> J[Kanban Board]
    C --> K[Tarefa Detalhada]
    C --> L[Projeto]
    D --> M[PostgreSQL]
    E --> N[WebSockets]
    F --> O[Iris]
    F --> P[Atlas]
```

### Fluxo de Gestão de Tarefas

1. **Criação**: Usuário cria tarefa
2. **Atribuição**: Tarefa é atribuída
3. **Execução**: Tarefa é movida para "Doing"
4. **Revisão**: Tarefa é revisada
5. **Conclusão**: Tarefa é finalizada
6. **Arquivamento**: Tarefa é arquivada

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Tarefas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/tarefas` | GET | Lista tarefas | `?projeto_id=1&status=todo` |
| `/api/tarefas` | POST | Cria tarefa | `{"titulo", "descricao", "projeto_id"}` |
| `/api/tarefas/<id>` | GET | Detalhes tarefa | - |
| `/api/tarefas/<id>` | PUT | Atualiza tarefa | `{"titulo", "descricao"}` |
| `/api/tarefas/<id>` | DELETE | Remove tarefa | - |
| `/api/tarefas/<id>/assign` | POST | Atribui tarefa | `{"user_id"}` |
| `/api/tarefas/<id>/move` | POST | Move tarefa | `{"coluna": "doing"}` |

### Comentários

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/tarefas/<id>/comentarios` | GET | Lista comentários | - |
| `/api/tarefas/<id>/comentarios` | POST | Adiciona comentário | `{"conteudo"}` |
| `/api/comentarios/<id>` | PUT | Atualiza comentário | `{"conteudo"}` |
| `/api/comentarios/<id>` | DELETE | Remove comentário | - |

### Projetos

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/projetos` | GET | Lista projetos | `?status=ativo` |
| `/api/projetos` | POST | Cria projeto | `{"nome", "descricao"}` |
| `/api/projetos/<id>` | GET | Detalhes projeto | - |
| `/api/projetos/<id>` | PUT | Atualiza projeto | `{"nome", "descricao"}` |
| `/api/projetos/<id>/membros` | GET | Membros do projeto | - |
| `/api/projetos/<id>/membros` | POST | Adiciona membro | `{"user_id"}` |

### Quadros (Kanban)

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/quadros` | GET | Lista quadros | `?projeto_id=1` |
| `/api/quadros` | POST | Cria quadro | `{"nome", "projeto_id"}` |
| `/api/quadros/<id>` | GET | Detalhes quadro | - |
| `/api/quadros/<id>/colunas` | GET | Colunas do quadro | - |
| `/api/quadros/<id>/colunas` | POST | Adiciona coluna | `{"nome", "posicao"}` |

### Timeline

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/projetos/<id>/timeline` | GET | Timeline do projeto | - |
| `/api/tarefas/<id>/historico` | GET | Histórico da tarefa | - |

### Integração com Iris

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/iris/tarefas` | GET | Tarefas do Iris | `?status=pendente` |
| `/api/iris/<id>/criar-tarefa` | POST | Cria tarefa do Iris | `{"projeto_id"}` |

## Banco de Dados

### Esquema Principal

```sql
-- Tarefas
CREATE TABLE tarefas (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    projeto_id INTEGER REFERENCES projetos(id),
    quadro_id INTEGER REFERENCES quadros(id),
    coluna VARCHAR(50) DEFAULT 'todo', -- todo, doing, review, done
    prioridade VARCHAR(20) DEFAULT 'media', -- baixa, media, alta, critica
    status VARCHAR(50) DEFAULT 'aberto', -- aberto, em_andamento, concluido, arquivado
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    criado_por INTEGER REFERENCES usuarios(id),
    atribuido_para INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Projetos
CREATE TABLE projetos (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    data_inicio TIMESTAMP,
    data_fim TIMESTAMP,
    status VARCHAR(50) DEFAULT 'ativo', -- ativo, pausado, concluido, cancelado
    criado_por INTEGER REFERENCES usuarios(id),
    gestor_id INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Membros de projeto
CREATE TABLE projeto_membros (
    id SERIAL PRIMARY KEY,
    projeto_id INTEGER REFERENCES projetos(id),
    user_id INTEGER REFERENCES usuarios(id),
    funcao VARCHAR(100),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Quadros Kanban
CREATE TABLE quadros (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    projeto_id INTEGER REFERENCES projetos(id),
    tipo VARCHAR(50) DEFAULT 'kanban', -- kanban, scrum
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Colunas do quadro
CREATE TABLE quadro_colunas (
    id SERIAL PRIMARY KEY,
    quadro_id INTEGER REFERENCES quadros(id),
    nome VARCHAR(100) NOT NULL,
    posicao INTEGER NOT NULL,
    limite INTEGER DEFAULT NULL
);

-- Comentários
CREATE TABLE comentarios (
    id SERIAL PRIMARY KEY,
    tarefa_id INTEGER REFERENCES tarefas(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    conteudo TEXT NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Histórico de tarefas
CREATE TABLE tarefa_historico (
    id SERIAL PRIMARY KEY,
    tarefa_id INTEGER REFERENCES tarefas(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    acao VARCHAR(100) NOT NULL, -- criado, atualizado, movido, atribuido
    dados_anteriores JSONB,
    dados_novos JSONB,
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
CREATE INDEX idx_tarefas_projeto ON tarefas(projeto_id);
CREATE INDEX idx_tarefas_coluna ON tarefas(coluna);
CREATE INDEX idx_tarefas_prioridade ON tarefas(prioridade);
CREATE INDEX idx_tarefas_atribuido ON tarefas(atribuido_para);
CREATE INDEX idx_projetos_status ON projetos(status);
CREATE INDEX idx_projeto_membros_projeto ON projeto_membros(projeto_id);
CREATE INDEX idx_quadro_colunas_quadro ON quadro_colunas(quadro_id);
CREATE INDEX idx_comentarios_tarefa ON comentarios(tarefa_id);
CREATE INDEX idx_tarefa_historico_tarefa ON tarefa_historico(tarefa_id);
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

## Integração com Outros Apps

### Integração com Iris

1. **Criação de Tarefas**:
   - Solicitações aprovadas no Iris
   - Tornam-se tarefas no Hércules
   - Atribuição automática

2. **Acompanhamento**:
   - Status sincronizado
   - Comentários compartilhados
   - Prazos monitorados

### Integração com Atlas

1. **Autenticação**:
   - Validação de token JWT
   - Verificação de permissões
   - Cache de 5 minutos

2. **Sincronização**:
   - Dados básicos de usuário
   - Departamentos
   - Status de ativação

## Tempo Real (WebSockets)

### Eventos de Tempo Real

```javascript
// Conexão WebSocket
const socket = io('http://localhost:5001');

// Eventos recebidos
socket.on('tarefa_criada', (data) => {
  console.log('Nova tarefa:', data);
  // Atualiza interface
});

socket.on('tarefa_movida', (data) => {
  console.log('Tarefa movida:', data);
  // Atualiza quadro Kanban
});

socket.on('comentario_adicionado', (data) => {
  console.log('Novo comentário:', data);
  // Atualiza lista de comentários
});

// Eventos enviados
socket.emit('tarefa_atualizada', {
  tarefa_id: 123,
  campo: 'status',
  valor: 'concluido'
});
```

### Configuração do Socket.IO

```python
# app.py
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:3000"])

@socketio.on('connect')
def handle_connect():
    print('Cliente conectado')
    emit('conectado', {'status': 'online'})

@socketio.on('tarefa_atualizada')
def handle_tarefa_atualizada(data):
    # Atualiza tarefa no banco
    # Notifica outros clientes
    emit('tarefa_movida', data, broadcast=True, include_self=False)
```

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com curta expiração
   - Validação em todos os endpoints

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por projeto
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Dados sensíveis criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **WebSockets**:
   - Autenticação por token
   - Validação de origem
   - Rate limiting

## Monitoramento e Logging

### Métricas Monitoradas

- Número de tarefas criadas
- Tarefas concluídas por dia
- Tempo médio de conclusão
- Usuários ativos
- Projetos em andamento

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "hercules",
  "action": "tarefa_created",
  "user": "admin@olimpus.local",
  "tarefa_id": 123,
  "titulo": "Implementar Feature X",
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Node.js (para frontend)
- 4GB RAM mínima
- 10GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=hercules_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/hercules
REDIS_URL=redis://localhost:6379/0
ATLAS_URL=http://localhost:5010
IRIS_URL=http://localhost:5070
PORT=5001
```

### Processo de Implantação

```bash
# Backend
cd backend
pip install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:5001 app:app

# Frontend
cd frontend
npm install
npm run build
serve -s dist -l 5001

# Systemd
cp hercules.service /etc/systemd/system/
systemctl enable hercules
systemctl start hercules
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres hercules > hercules_db_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql -U postgres hercules < hercules_db_backup.sql
```

### Atualizações

1. Parar serviços: `systemctl stop hercules`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `npm install && pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Build frontend: `npm run build`
7. Iniciar serviços: `systemctl start hercules`
8. Verificar saúde: `curl http://localhost:5001/api/ping`