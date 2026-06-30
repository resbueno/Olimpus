# Documentação Técnica - Iris (Gestão de Formulários e Workflow)

## Visão Geral

**Nome**: Iris - Automação de Processos
**Porta**: 5070
**Prioridade**: ALTA
**Tecnologias**: Flask, React, PostgreSQL, Redis
**Responsável**: Equipe de Processos e Automação

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Iris - Workflow Engine] --> B[API REST]
    A --> C[Frontend React]
    A --> D[Banco de Dados]
    A --> E[Cache]
    A --> F[Integração]
    B --> G[/api/formularios]
    B --> H[/api/ordens]
    B --> I[/api/workflow]
    C --> J[Form Builder]
    C --> K[Process Viewer]
    C --> L[Dashboard]
    D --> M[PostgreSQL]
    E --> N[Redis]
    F --> O[Hera]
    F --> P[Ploutos]
    F --> Q[Atlas]
```

### Fluxo de Processamento

1. **Design**: Usuário cria template de formulário
2. **Publicação**: Formulário é publicado
3. **Solicitação**: Usuário preenche formulário
4. **Workflow**: Processo segue etapas definidas
5. **Aprovação**: Aprovadores analisam solicitação
6. **Conclusão**: Processo é finalizado
7. **Arquivamento**: Dados são armazenados

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "password"}` | `{"ok": true}` |
| `/api/auth/status` | GET | Status de autenticação | - | `{"authenticated": true}` |

### Templates de Formulários

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/formularios` | GET | Lista templates | `?ativo=1&categoria=rh` |
| `/api/formularios` | POST | Cria template | `{"nome", "campos", "etapas"}` |
| `/api/formularios/<id>` | GET | Detalhes template | - |
| `/api/formularios/<id>` | PUT | Atualiza template | `{"nome", "campos"}` |
| `/api/formularios/<id>` | DELETE | Remove template | - |
| `/api/formularios/<id>/versoes` | GET | Histórico de versões | - |

### Ordens de Serviço

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/ordens` | GET | Lista ordens | `?status=aberta&prioridade=alta` |
| `/api/ordens` | POST | Cria ordem | `{"formulario_id", "dados", "prioridade"}` |
| `/api/ordens/<id>` | GET | Detalhes ordem | - |
| `/api/ordens/<id>` | PUT | Atualiza ordem | `{"dados", "status"}` |
| `/api/ordens/<id>/avancar` | POST | Avança etapa | `{"acao", "comentario"}` |
| `/api/ordens/<id>/anexos` | POST | Adiciona anexo | `file + {"descricao"}` |

### Workflow

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/workflow/etapas` | GET | Lista etapas | `?formulario_id=1` |
| `/api/workflow/<ordem_id>/historico` | GET | Histórico | - |
| `/api/workflow/<ordem_id>/aprovadores` | GET | Aprovadores | - |
| `/api/workflow/<ordem_id>/delegar` | POST | Delegar aprovação | `{"user_id", "comentario"}` |

### Estatísticas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/stats` | GET | Estatísticas gerais | - |
| `/api/stats/formularios` | GET | Uso de formulários | `?mes=4&ano=2026` |
| `/api/stats/ordens` | GET | Desempenho de ordens | `?status=concluida` |
| `/api/stats/tempos` | GET | Tempos médios | `?formulario_id=1` |

## Banco de Dados

### Esquema Principal

```sql
-- Templates de formulários
CREATE TABLE formularios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    categoria VARCHAR(100),
    versao INTEGER DEFAULT 1,
    ativo BOOLEAN DEFAULT TRUE,
    criado_por INTEGER REFERENCES usuarios(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Campos de formulário
CREATE TABLE formulario_campos (
    id SERIAL PRIMARY KEY,
    formulario_id INTEGER REFERENCES formularios(id),
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- text, number, date, select, checkbox, file
    label VARCHAR(255),
    placeholder VARCHAR(255),
    obrigatorio BOOLEAN DEFAULT FALSE,
    opcoes JSONB, -- Para campos select/checkbox
    validacao VARCHAR(255), -- Regex ou tipo de validação
    ordem INTEGER DEFAULT 0
);

-- Etapas de workflow
CREATE TABLE workflow_etapas (
    id SERIAL PRIMARY KEY,
    formulario_id INTEGER REFERENCES formularios(id),
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    ordem INTEGER NOT NULL,
    tipo VARCHAR(50), -- entrada, aprovacao, revisao, conclusao
    aprovadores JSONB, -- [{"role": "gestor", "departamento": "TI"}] ou [{"user_id": 123}]
    tempo_limite INTEGER -- Em horas
);

-- Ordens de serviço
CREATE TABLE ordens_servico (
    id SERIAL PRIMARY KEY,
    formulario_id INTEGER REFERENCES formularios(id),
    numero VARCHAR(50) UNIQUE,
    titulo VARCHAR(255),
    dados JSONB NOT NULL,
    criado_por INTEGER REFERENCES usuarios(id),
    prioridade VARCHAR(20) DEFAULT 'normal', -- baixa, normal, alta, critica
    status VARCHAR(50) DEFAULT 'entrada', -- entrada, aprovacao, revisao, conclusao, cancelado
    etapa_atual INTEGER REFERENCES workflow_etapas(id),
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Histórico de workflow
CREATE TABLE workflow_historico (
    id SERIAL PRIMARY KEY,
    ordem_id INTEGER REFERENCES ordens_servico(id),
    etapa_id INTEGER REFERENCES workflow_etapas(id),
    usuario_id INTEGER REFERENCES usuarios(id),
    acao VARCHAR(50) NOT NULL, -- avancar, rejeitar, delegar, comentar
    comentario TEXT,
    dados_anteriores JSONB,
    dados_novos JSONB,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Anexos
CREATE TABLE ordem_anexos (
    id SERIAL PRIMARY KEY,
    ordem_id INTEGER REFERENCES ordens_servico(id),
    nome_arquivo VARCHAR(255) NOT NULL,
    caminho_arquivo VARCHAR(512) NOT NULL,
    tipo VARCHAR(100),
    tamanho INTEGER,
    criado_por INTEGER REFERENCES usuarios(id),
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
CREATE INDEX idx_formularios_nome ON formularios USING gin (to_tsvector('portuguese', nome));
CREATE INDEX idx_formularios_categoria ON formularios(categoria);
CREATE INDEX idx_formulario_campos_formulario ON formulario_campos(formulario_id);
CREATE INDEX idx_workflow_etapas_formulario ON workflow_etapas(formulario_id);
CREATE INDEX idx_ordens_formulario ON ordens_servico(formulario_id);
CREATE INDEX idx_ordens_status ON ordens_servico(status);
CREATE INDEX idx_ordens_prioridade ON ordens_servico(prioridade);
CREATE INDEX idx_workflow_historico_ordem ON workflow_historico(ordem_id);
CREATE INDEX idx_ordem_anexos_ordem ON ordem_anexos(ordem_id);
CREATE INDEX idx_usuarios_email ON usuarios(email);
```

## Processos de Negócio

### 1. Criação de Template de Formulário

**Fluxo**:
1. Usuário acessa Form Builder
2. Define nome, categoria e descrição
3. Adiciona campos ao formulário
4. Configura etapas de workflow
5. Define aprovadores para cada etapa
6. Salva e publica template
7. Template fica disponível para uso

**Tipos de Campo**:
- Texto curto/longo
- Número (inteiro/decimal)
- Data/Hora
- Seleção única/múltipla
- Checkbox
- Upload de arquivo
- Assinatura digital

### 2. Solicitação via Formulário

**Fluxo**:
1. Usuário seleciona template
2. Preenche dados do formulário
3. Anexa documentos se necessário
4. Define prioridade
5. Envia solicitação
6. Sistema cria ordem de serviço
7. Workflow é iniciado

**Validações**:
- Campos obrigatórios preenchidos
- Formato de dados válido
- Permissões do usuário
- Limite de tamanho de anexos

### 3. Processamento de Workflow

**Fluxo**:
1. Ordem é criada no status "entrada"
2. Sistema notifica primeiro aprovador
3. Aprovador analisa solicitação
4. Aprovador aprova ou rejeita
5. Sistema avança para próxima etapa
6. Processo continua até conclusão
7. Solicitante é notificado do resultado

**Ações Possíveis**:
- Aprovar (avança para próxima etapa)
- Rejeitar (retorna para etapa anterior)
- Delegar (transfere aprovação)
- Comentar (adiciona observação)
- Cancelar (encerra processo)

### 4. Monitoramento e Métricas

**Fluxo**:
1. Sistema registra todos os eventos
2. Calcula tempos médios por etapa
3. Identifica gargalos
4. Gera relatórios de desempenho
5. Notifica gestores sobre atrasos
6. Sugere melhorias de processo

**Métricas Chave**:
- Tempo médio por etapa
- Taxa de aprovação/rejeição
- Tempo total de processo
- Número de delegações
- Satisfação do solicitante

## Integração com Outros Apps

### Integração com Hera (RH)

1. **Dados de Usuário**:
   - Sincronização de colaboradores
   - Departamentos e cargos
   - Hierarquia organizacional

2. **Processos de RH**:
   - Solicitação de férias
   - Aprovação de treinamentos
   - Processos de admissão/desligamento

### Integração com Ploutos (Financeiro)

1. **Aprovação Financeira**:
   - Solicitações de compra
   - Reembolsos
   - Pagamentos a fornecedores

2. **Integração de Dados**:
   - Centros de custo
   - Projetos financeiros
   - Limites de aprovação

### Integração com Atlas

1. **Autenticação**:
   - Validação de token JWT
   - Verificação de permissões
   - Cache de 5 minutos

2. **Sincronização**:
   - Dados básicos de usuário
   - Status de ativação
   - Funções e permissões

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com curta expiração
   - Validação em todos os endpoints

2. **Autorização**:
   - Controle de acesso por função
   - Permissões granulares por formulário
   - Acesso restrito a dados sensíveis

3. **Proteção de Dados**:
   - Dados sensíveis criptografados
   - Acesso auditado
   - Backups diários com retenção

4. **Upload de Arquivos**:
   - Verificação de vírus
   - Sanitização de nomes
   - Restrição de tipos de arquivo

## Monitoramento e Logging

### Métricas Monitoradas

- Número de ordens criadas por dia
- Tempo médio de processamento
- Taxa de aprovação
- Erros de validação
- Uso de templates

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "iris",
  "action": "ordem_created",
  "user": "admin@olimpus.local",
  "ordem_id": 123,
  "formulario": "Solicitação de Compra",
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
SECRET_KEY=iris_secret_key
DATABASE_URL=postgresql://user:pass@localhost:5432/iris
REDIS_URL=redis://localhost:6379/0
ATLAS_URL=http://localhost:5010
HERA_URL=http://localhost:5041
PLOUTOS_URL=http://localhost:5080
PORT=5070
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
flask db upgrade

# 3. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5070 app:app

# 4. Configurar systemd
cp iris.service /etc/systemd/system/
systemctl enable iris
systemctl start iris
```

## Manutenção

### Backup e Restore

```bash
# Backup PostgreSQL
pg_dump -U postgres iris > iris_db_backup_$(date +%Y%m%d).sql

# Restore PostgreSQL
psql -U postgres iris < iris_db_backup.sql
```

### Atualizações

1. Parar serviço: `systemctl stop iris`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start iris`
7. Verificar saúde: `curl http://localhost:5070/api/ping`

## Solução de Problemas

### Problemas Comuns

1. **Workflow travado**:
   - Verificar etapa atual
   - Verificar aprovadores
   - Forçar avanço manual

2. **Formulário não salva**:
   - Verificar validações
   - Verificar permissões
   - Verificar logs de erro

3. **Anexos não upload**:
   - Verificar espaço em disco
   - Verificar permissões
   - Verificar tamanho do arquivo

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5070/api/ping

# Listar formulários
curl -H "Authorization: Bearer TOKEN" http://localhost:5070/api/formularios

# Verificar logs
tail -f /var/log/iris/iris.log
```

## Roadmap

### Próximas Versões

- **v2.1**: Editor visual de workflow
- **v2.2**: Integração com RPA
- **v2.3**: Mobile app para aprovações
- **v2.4**: Analytics com Power BI

### Melhorias Planejadas

- Cache mais agressivo para templates
- Processamento paralelo de workflows
- Integração com Microsoft Power Automate
- Suporte a múltiplos idiomas
- API GraphQL para consultas complexas

## Contatos

**Suporte Técnico**: suporte@olimpus.local
**Processos**: processos@olimpus.local
**Desenvolvimento**: dev@olimpus.local