# Documentação de Processos - Atlas (Gestão de Acessos)

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