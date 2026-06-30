# Documentação de Processos - Iris (Gestão de Formulários e Workflow)

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