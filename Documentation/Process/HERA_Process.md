# Documentação de Processos - Hera (Gestão de Pessoas)

## Processos de Negócio

### 1. Admissão de Colaborador

**Fluxo**:
1. RH inicia processo de admissão
2. Preenche dados pessoais e profissionais
3. Sistema cria usuário no Atlas
4. Inicia processo de onboarding
5. Envia email de boas-vindas
6. Agenda treinamentos iniciais

**Checklist**:
- Documentos pessoais validados
- Contrato assinado
- Equipamentos provisionados
- Acessos configurados
- Treinamentos agendados

### 2. Gestão de Férias

**Fluxo**:
1. Colaborador solicita férias
2. Sistema valida saldo disponível
3. Gestor recebe notificação
4. Gestor aprova ou rejeita
5. RH é notificado
6. Férias registradas no Cronos
7. Colaborador recebe confirmação

**Regras**:
- Mínimo 14 dias de aviso
- Máximo 30 dias por período
- Não pode coincidir com períodos críticos

### 3. Avaliação 360°

**Fluxo**:
1. RH cria ciclo de avaliação
2. Define período e participantes
3. Sistema envia convites
4. Colaboradores respondem avaliações
5. Gestores revisam resultados
6. RH consolida relatórios
7. Feedback individual é dado

**Tipos de Avaliação**:
- Autoavaliação
- Avaliação por pares
- Avaliação por gestor
- Avaliação 360° completa

### 4. Onboarding

**Fluxo**:
1. Novo colaborador é cadastrado
2. Template de onboarding é aplicado
3. Etapas são atribuídas
4. Colaborador completa etapas
5. Responsáveis validam conclusão
6. Onboarding é concluído
7. Feedback é coletado

**Etapas Padrão**:
1. Documentação
2. Treinamento inicial
3. Configuração de equipamentos
4. Apresentação da equipe
5. Treinamentos específicos
6. Avaliação inicial

## Solução de Problemas

### Problemas Comuns

1. **Sincronização com Atlas falha**:
   - Verificar conexão com Atlas
   - Verificar webhooks estão configurados
   - Verificar logs de sincronização

2. **Tarefas Celery não executam**:
   - Verificar RabbitMQ está rodando
   - Verificar worker está ativo
   - Verificar logs do Celery

3. **Cálculo de férias incorreto**:
   - Verificar regras de negócio
   - Verificar dados do colaborador
   - Recalcular manualmente

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5041/api/ping

# Verificar status Celery
celery -A tasks.celery inspect ping

# Listar tarefas agendadas
celery -A tasks.celery inspect scheduled

# Verificar logs
tail -f /var/log/hera/hera.log
tail -f /var/log/hera/celery.log
```