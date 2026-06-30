# Documentação Técnica - Atlas (Gestão de Acessos)

## Visão Geral

**Nome**: Atlas - Identity and Access Management (IAM)
**Porta**: 5010
**Prioridade**: CRÍTICA
**Tecnologias**: Flask, SQLAlchemy, JWT, OAuth2
**Responsável**: Equipe de Segurança da Informação

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Atlas - IAM Central] --> B[API REST]
    A --> C[Banco de Dados]
    A --> D[Autenticação]
    A --> E[Integração SSO]
    B --> F[/api/pessoas]
    B --> G[/api/empresas]
    B --> H[/api/sistemas]
    B --> I[/api/acessos]
    C --> J[PostgreSQL]
    D --> K[JWT Tokens]
    D --> L[OAuth2 Provider]
    E --> M[Hub Olimpus]
    E --> N[Outros Apps]
```

### Fluxo de Autenticação

1. **Login**: Usuário envia credenciais para `/api/auth/login`
2. **Validação**: Atlas valida contra banco de dados
3. **Token**: Gera JWT com claims (email, roles, exp)
4. **Sessão**: Token é usado para acesso a outros apps
5. **Logout**: Token é invalidado em `/api/auth/logout`

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Autenticação de usuário | `{"email", "senha"}` | `{"ok": true, "token": "..."}` |
| `/api/auth/logout` | POST | Encerra sessão | - | `{"ok": true}` |
| `/api/auth/status` | GET | Verifica status de autenticação | - | `{"authenticated": true}` |

### Gestão de Pessoas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/pessoas` | GET | Lista todas as pessoas | `?ativo=1` |
| `/api/pessoas` | POST | Cria nova pessoa | `{"nome", "email", "senha", "funcoes"}` |
| `/api/pessoas/<id>` | GET | Detalhes de pessoa | - |
| `/api/pessoas/<id>` | PUT | Atualiza pessoa | `{"nome", "email", ...}` |
| `/api/pessoas/<id>/desativar` | POST | Desativa pessoa | - |

### Gestão de Empresas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/empresas` | GET | Lista empresas | - |
| `/api/empresas` | POST | Cria empresa | `{"nome", "cnpj"}` |
| `/api/empresas/<id>` | GET | Detalhes de empresa | - |
| `/api/empresas/<id>/pessoas` | GET | Pessoas da empresa | - |

### Gestão de Sistemas

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/sistemas` | GET | Lista sistemas cadastrados | - |
| `/api/sistemas` | POST | Cadastra novo sistema | `{"nome", "url", "descricao"}` |
| `/api/sistemas/<id>` | GET | Detalhes do sistema | - |

### Gestão de Funções

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/funcoes` | GET | Lista funções disponíveis | - |
| `/api/funcoes` | POST | Cria nova função | `{"nome", "descricao", "permissoes"}` |
| `/api/funcoes/<id>` | GET | Detalhes da função | - |

## Banco de Dados

### Esquema Principal

```sql
-- Tabelas principais
CREATE TABLE empresas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE pessoas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    empresa_id INTEGER REFERENCES empresas(id),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

CREATE TABLE funcoes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) UNIQUE NOT NULL,
    descricao TEXT,
    sistema BOOLEAN DEFAULT FALSE
);

CREATE TABLE pessoa_funcao (
    pessoa_id INTEGER REFERENCES pessoas(id),
    funcao_id INTEGER REFERENCES funcoes(id),
    PRIMARY KEY (pessoa_id, funcao_id)
);

CREATE TABLE sistemas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    url VARCHAR(255),
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE
);
```

### Índices Importantes

```sql
CREATE INDEX idx_pessoas_email ON pessoas(email);
CREATE INDEX idx_pessoas_empresa ON pessoas(empresa_id);
CREATE INDEX idx_pessoa_funcao_pessoa ON pessoa_funcao(pessoa_id);
CREATE INDEX idx_pessoa_funcao_funcao ON pessoa_funcao(funcao_id);
```

## Processos de Negócio

### 1. Cadastro de Novo Usuário

**Fluxo**:
1. Administrador acessa interface de cadastro
2. Preenche dados: nome, email, senha, empresa, funções
3. Sistema valida email único e formato de senha
4. Senha é hasheada e armazenada
5. Usuário recebe email de boas-vindas
6. Usuário pode fazer login no sistema

**Validações**:
- Email deve ser único no sistema
- Senha deve ter mínimo 8 caracteres
- Senha deve conter letras e números
- Email deve pertencer a domínio válido

### 2. Autenticação e SSO

**Fluxo**:
1. Usuário acessa qualquer app Olimpus
2. App redireciona para Atlas login
3. Usuário insere credenciais
4. Atlas valida e gera JWT token
5. Token é passado para app original
6. App valida token com Atlas
7. Usuário é autenticado no app

**Segurança**:
- Tokens expiram em 8 horas
- Refresh tokens para sessões longas
- Tokens são invalidados no logout
- CORS restrito a domínios Olimpus

### 3. Gestão de Acessos

**Fluxo**:
1. Administrador seleciona usuário
2. Visualiza funções atuais
3. Adiciona/remove funções
4. Sistema registra alteração
5. Acessos são atualizados em tempo real
6. Usuário recebe notificação de mudança

**Controles**:
- Somente administradores podem gerenciar acessos
- Alterações são auditadas
- Funções seguem princípio do menor privilégio

## Integração com Outros Apps

### SSO (Single Sign-On)

Atlas atua como provedor central de identidade:

1. **Fluxo de Login**:
   ```
   App → Atlas (login) → Token JWT → App (validação) → Acesso concedido
   ```

2. **Validação de Token**:
   - Apps validam tokens via `/api/auth/validate`
   - Tokens contêm claims: email, roles, exp
   - Apps verificam permissões com base nos roles

3. **Logout Global**:
   - Logout em qualquer app encerra sessão global
   - Token é adicionado à lista de revogação
   - Todos os apps verificam tokens revogados

### Sincronização de Dados

- **Webhooks**: Atlas notifica apps sobre mudanças de usuário
- **APIs**: Apps consultam Atlas para dados atualizados
- **Cache**: Apps podem cachear dados por 5 minutos

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - BCrypt para hash de senhas
   - Rate limiting em endpoints de login
   - Bloqueio após 5 tentativas falhas

2. **Autorização**:
   - RBAC (Role-Based Access Control)
   - Funções hierárquicas (admin > gerente > usuário)
   - Permissões granulares por endpoint

3. **Proteção de Dados**:
   - Dados sensíveis criptografados
   - Backups diários com retenção de 30 dias
   - Acesso a banco restrito a rede interna

4. **Auditoria**:
   - Log de todas as operações sensíveis
   - Retenção de logs por 6 meses
   - Alertas para atividades suspeitas

## Monitoramento e Logging

### Métricas Monitoradas

- Taxa de login bem-sucedidos vs falhas
- Tempo médio de resposta da API
- Número de usuários ativos
- Tentativas de acesso não autorizado
- Uso de CPU e memória

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "atlas",
  "action": "login_success",
  "user": "admin@olimpus.local",
  "ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0"
}
```

## Implantação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redis 6+ (para cache)
- 2GB RAM mínima
- 10GB disco

### Variáveis de Ambiente

```env
FLASK_ENV=production
SECRET_KEY=super_secret_key_here
DATABASE_URL=postgresql://user:pass@localhost:5432/atlas
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=jwt_secret_here
JWT_EXPIRE_HOURS=8
ADMIN_EMAIL=admin@olimpus.local
ADMIN_PASSWORD=initial_admin_password
```

### Processo de Implantação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
flask db upgrade

# 3. Criar usuário admin inicial
flask create-admin

# 4. Iniciar serviço
gunicorn -w 4 -b 0.0.0.0:5010 app:app

# 5. Configurar sistema init (systemd)
cp atlas.service /etc/systemd/system/
systemctl enable atlas
systemctl start atlas
```

## Manutenção

### Backup e Restore

```bash
# Backup
pg_dump -U postgres atlas > atlas_backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres atlas < atlas_backup.sql
```

### Atualizações

1. Parar serviço: `systemctl stop atlas`
2. Fazer backup do banco
3. Atualizar código: `git pull`
4. Instalar dependências: `pip install -r requirements.txt`
5. Executar migrações: `flask db upgrade`
6. Iniciar serviço: `systemctl start atlas`
7. Verificar saúde: `curl http://localhost:5010/api/ping`

## Solução de Problemas

### Problemas Comuns

1. **Login falhando**:
   - Verificar credenciais
   - Verificar se usuário está ativo
   - Verificar logs de autenticação

2. **Token inválido**:
   - Verificar expiração do token
   - Verificar se token foi revogado
   - Gerar novo token

3. **Banco de dados desconectado**:
   - Verificar conexão PostgreSQL
   - Verificar variáveis de ambiente
   - Reiniciar serviço

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5010/api/ping

# Listar usuários (admin)
curl -H "Authorization: Bearer TOKEN" http://localhost:5010/api/pessoas

# Verificar logs
tail -f /var/log/atlas/atlas.log

# Verificar status do serviço
systemctl status atlas
```

## Roadmap

### Próximas Versões

- **v2.1**: Integração com Active Directory
- **v2.2**: Autenticação multifator (MFA)
- **v2.3**: Interface de auto-serviço para usuários
- **v2.4**: Relatórios avançados de acesso

### Melhorias Planejadas

- Cache mais agressivo para dados estáticos
- API GraphQL para consultas complexas
- Webhooks para notificações em tempo real
- Integração com SIEM para logs de segurança

## Contatos

**Suporte Técnico**: suporte@olimpus.local
**Desenvolvimento**: dev@olimpus.local
**Segurança**: security@olimpus.local