# Documentação de Processos - Hércules (Gestão de Tarefas)

## Processos de Negócio

### 1. Criação e Gestão de Tarefas

**Fluxo**:
1. Usuário cria nova tarefa
2. Define título, descrição, prioridade
3. Atribui a projeto e quadro
4. Tarefa é salva no status "todo"
5. Tarefa aparece no quadro Kanban
6. Usuários podem movê-la entre colunas

**Campos Obrigatórios**:
- Título (5-100 caracteres)
- Projeto ou Quadro
- Data de início (opcional)

### 2. Gestão de Projetos

**Fluxo**:
1. Gestor cria novo projeto
2. Define nome, descrição, datas
3. Adiciona membros ao projeto
4. Cria quadros Kanban
5. Configura colunas do quadro
6. Projeto fica disponível para a equipe

**Fases do Projeto**:
- Planejamento
- Execução
- Monitoramento
- Encerramento

### 3. Colaboração em Tempo Real

**Fluxo**:
1. Usuários acessam o mesmo quadro
2. Alterações são sincronizadas via WebSocket
3. Comentários são atualizados em tempo real
4. Notificações são enviadas instantaneamente
5. Histórico de alterações é mantido

**Eventos em Tempo Real**:
- Tarefa criada
- Tarefa movida
- Tarefa atribuída
- Comentário adicionado
- Status alterado

### 4. Integração com Workflows (Iris)

**Fluxo**:
1. Solicitação é aprovada no Iris
2. Tarefa é criada automaticamente
3. Responsável é atribuído
4. Prazo é definido
5. Tarefa é monitorada
6. Conclusão é reportada ao Iris

**Tipos de Integração**:
- Solicitações de compra
- Aprovações de documentos
- Processos de RH
- Solicitações de TI

## Solução de Problemas

### Problemas Comuns

1. **WebSocket não conecta**:
   - Verificar CORS
   - Verificar token de autenticação
   - Verificar logs do Socket.IO

2. **Tarefas não sincronizam**:
   - Verificar conexão WebSocket
   - Verificar permissões
   - Verificar logs de erro

3. **Quadro Kanban não atualiza**:
   - Verificar cache do navegador
   - Verificar conexão WebSocket
   - Recarregar página

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5001/api/ping

# Testar WebSocket
wscat -c ws://localhost:5001/socket.io/?EIO=4&transport=websocket

# Verificar logs
tail -f /var/log/hercules/hercules.log
```