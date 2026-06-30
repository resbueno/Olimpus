# Documentação Técnica - Hub Olimpus

## Visão Geral

**Nome**: Hub Olimpus - Portal Unificado
**Porta**: 5100
**Prioridade**: CRÍTICA
**Tecnologias**: Flask, React, OAuth2, WebSockets
**Responsável**: Equipe de Experiência do Usuário

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Hub Olimpus] --> B[Frontend React]
    A --> C[Backend API]
    A --> D[Autenticação]
    A --> E[Integração Apps]
    B --> F[Dashboard]
    B --> G[App Launcher]
    B --> H[Notificações]
    C --> I[/api/apps]
    C --> J[/api/launch]
    C --> K[/api/ready]
    D --> L[Atlas IAM]
    E --> M[Héstia]
    E --> N[Iris]
    E --> O[Outros Apps]
```

### Fluxo de Navegação

1. **Acesso Inicial**: Usuário acessa `http://localhost:5100`
2. **Redirecionamento**: Se não autenticado, redireciona para Atlas
3. **Autenticação**: Atlas valida credenciais e retorna token
4. **Dashboard**: Hub exibe apps disponíveis para o usuário
5. **Lançamento**: Usuário clica em app, Hub redireciona com token

## Endpoints da API

### Autenticação

| Endpoint | Método | Descrição | Parâmetros | Resposta |
|----------|--------|-----------|------------|----------|
| `/api/ping` | GET | Verificação de saúde | - | `{"ok": true}` |
| `/api/auth/login` | POST | Login via Atlas | `{"email", "senha"}` | `{"ok": true, "token": "..."}` |
| `/api/auth/me` | GET | Dados do usuário | - | `{"ok": true, "data": {...}}` |
| `/api/auth/logout` | POST | Encerra sessão | - | `{"ok": true}` |

### Gestão de Apps

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/apps` | GET | Lista apps disponíveis | - |
| `/api/apps/<folder>` | GET | Detalhes do app | - |
| `/api/launch/<folder>` | GET | Lança aplicativo | - |
| `/api/ready/<port>` | GET | Verifica status da porta | - |

### Notificações

| Endpoint | Método | Descrição | Parâmetros |
|----------|--------|-----------|------------|
| `/api/notifications` | GET | Lista notificações | `?limit=10` |
| `/api/notifications/<id>/read` | POST | Marca como lida | - |
| `/api/notifications/read-all` | POST | Marca todas como lidas | - |

## Processos de Negócio

### 1. Autenticação e Acesso

**Fluxo**:
1. Usuário acessa Hub sem sessão
2. Hub redireciona para Atlas login
3. Usuário insere credenciais no Atlas
4. Atlas valida e retorna token JWT
5. Hub valida token e cria sessão
6. Usuário é redirecionado para dashboard

**Validações**:
- Token deve ser válido e não expirado
- Usuário deve estar ativo no Atlas
- Token deve conter claims necessários

### 2. Lançamento de Aplicativos

**Fluxo**:
1. Usuário clica em ícone de app no Hub
2. Hub verifica permissões do usuário
3. Hub verifica status do app (`/api/ready/<port>`)
4. Hub redireciona para app com token
5. App valida token e concede acesso

**Lógica de Redirecionamento**:
```javascript
// Exemplo de lançamento
function launchApp(appFolder) {
  const token = getSessionToken();
  const appUrl = `http://localhost:${appPort}/${appFolder}?atlas_token=${token}`;
  window.location.href = appUrl;
}
```

### 3. Gerenciamento de Notificações

**Fluxo**:
1. Apps enviam notificações para Hub via API
2. Hub armazena notificações por usuário
3. Hub exibe contador de notificações
4. Usuário clica para ver detalhes
5. Notificações são marcadas como lidas

**Tipos de Notificações**:
- Avisos do sistema
- Mensagens de outros usuários
- Alertas de workflow
- Lembretes de tarefas

## Integração com Outros Apps

### Protocolo de Integração

1. **Registro de Apps**:
   - Apps devem ser registrados no Hub
   - Cada app tem: nome, folder, porta, ícone, descrição

2. **Verificação de Status**:
   - Hub verifica `/api/ready/<port>` antes de lançar
   - Resposta deve conter: `{"ready": true, "version": "x.x.x"}`

3. **Autenticação**:
   - Hub passa token JWT via query parameter
   - Apps validam token com Atlas
   - Apps verificam permissões do usuário

### Exemplo de Integração

**App Registration** (configuração no Hub):
```json
{
  "folder": "hestia",
  "name": "Héstia - Intranet",
  "port": 5020,
  "icon": "home",
  "description": "Intranet corporativa",
  "required_roles": ["user"],
  "visible": true
}
```

**Status Check** (resposta do app):
```json
{
  "ready": true,
  "version": "1.2.3",
  "maintenance": false,
  "message": "Serviço operacional"
}
```

## Frontend Architecture

### Estrutura de Componentes

```
src/
├── components/
│   ├── AppCard.vue          # Cartão de aplicativo
│   ├── NotificationBadge.vue # Badge de notificações
│   ├── UserMenu.vue          # Menu de usuário
│   └── SearchBar.vue        # Barra de busca
├── pages/
│   ├── Dashboard.vue        # Página principal
│   ├── Login.vue            # Página de login
│   └── Notifications.vue     # Página de notificações
├── services/
│   ├── api.js               # Serviço API
│   ├── auth.js              # Serviço de autenticação
│   └── websocket.js         # Serviço WebSocket
└── store/
    ├── index.js             # Vuex store
    ├── apps.js              # Estado dos apps
    └── notifications.js     # Estado das notificações
```

### Estado Global (Vuex)

```javascript
// store/apps.js
state: {
  apps: [],
  loading: false,
  error: null
},

mutations: {
  SET_APPS(state, apps) {
    state.apps = apps;
  },
  SET_LOADING(state, loading) {
    state.loading = loading;
  }
},

actions: {
  async fetchApps({ commit }) {
    commit('SET_LOADING', true);
    try {
      const apps = await api.getApps();
      commit('SET_APPS', apps);
    } catch (error) {
      commit('SET_ERROR', error);
    } finally {
      commit('SET_LOADING', false);
    }
  }
}
```

## Segurança

### Medidas de Segurança

1. **Autenticação**:
   - Delegada para Atlas IAM
   - Tokens JWT com expiração
   - Validação de token em todos os endpoints

2. **Autorização**:
   - Controle de acesso baseado em funções
   - Apps só aparecem se usuário tiver permissão
   - Verificação de roles no lançamento

3. **Proteção de Dados**:
   - Tokens nunca armazenados no frontend
   - Comunicação HTTPS obrigatória
   - CORS restrito a domínios Olimpus

4. **Auditoria**:
   - Log de acessos ao Hub
   - Log de lançamentos de apps
   - Monitoramento de atividades suspeitas

## Monitoramento e Logging

### Métricas Monitoradas

- Número de usuários ativos
- Tempo médio de resposta
- Taxa de sucesso de lançamentos
- Erros de autenticação
- Uso de memória e CPU

### Logs Importantes

```json
{
  "timestamp": "2026-04-20T18:00:00Z",
  "level": "INFO",
  "service": "hub",
  "action": "app_launch",
  "user": "admin@olimpus.local",
  "app": "hestia",
  "status": "success",
  "ip": "192.168.1.100"
}
```

## Implantação

### Requisitos

- Node.js 18+
- Python 3.11+
- Redis 6+ (para sessões)
- 2GB RAM mínima
- 5GB disco

### Variáveis de Ambiente

```env
# Backend
FLASK_ENV=production
SECRET_KEY=hub_secret_key
ATLAS_URL=http://localhost:5010
REDIS_URL=redis://localhost:6379/0
PORT=5100

# Frontend
VUE_APP_API_URL=http://localhost:5100
VUE_APP_ATLAS_URL=http://localhost:5010
```

### Processo de Implantação

```bash
# Backend
cd backend
pip install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:5100 app:app

# Frontend
cd frontend
npm install
npm run build
serve -s dist -l 5100

# Systemd (produção)
cp hub.service /etc/systemd/system/
systemctl enable hub
systemctl start hub
```

## Manutenção

### Atualizações

1. Parar serviços: `systemctl stop hub`
2. Fazer backup dos dados
3. Atualizar código: `git pull`
4. Instalar dependências: `npm install && pip install -r requirements.txt`
5. Build frontend: `npm run build`
6. Iniciar serviços: `systemctl start hub`
7. Verificar saúde: `curl http://localhost:5100/api/ping`

### Limpeza de Cache

```bash
# Limpar cache Redis
redis-cli FLUSHALL

# Limpar cache navegador
# (via interface ou Ctrl+F5)
```

## Solução de Problemas

### Problemas Comuns

1. **Apps não aparecem**:
   - Verificar se app está registrado no Hub
   - Verificar permissões do usuário
   - Verificar status do app (`/api/ready`)

2. **Login falha**:
   - Verificar conexão com Atlas
   - Verificar credenciais
   - Limpar cache do navegador

3. **Redirecionamento infinito**:
   - Verificar sessão e cookies
   - Verificar configuração CORS
   - Verificar logs de autenticação

4. **Performance lenta**:
   - Verificar conexão com Atlas
   - Verificar cache Redis
   - Analisar tempo de resposta dos apps

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5100/api/ping

# Listar apps disponíveis
curl -H "Authorization: Bearer TOKEN" http://localhost:5100/api/apps

# Verificar logs backend
tail -f /var/log/hub/backend.log

# Verificar logs frontend
tail -f /var/log/hub/frontend.log
```

## Roadmap

### Próximas Versões

- **v2.1**: Personalização de dashboard
- **v2.2**: Busca unificada entre apps
- **v2.3**: Integração com Microsoft Teams
- **v2.4**: Modo escuro e temas personalizados

### Melhorias Planejadas

- Cache mais agressivo para apps estáticos
- Notificações em tempo real via WebSocket
- Integração com calendário corporativo
- Relatórios de uso e analytics
- Suporte a múltiplos idiomas

## Contatos

**Suporte Técnico**: suporte@olimpus.local
**Desenvolvimento**: dev@olimpus.local
**Experiência do Usuário**: ux@olimpus.local