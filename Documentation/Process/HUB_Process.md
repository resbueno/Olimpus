# Documentação de Processos - Hub Olimpus

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