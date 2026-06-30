# Documentação de Processos - Cronos (Ponto Eletrônico)

## Processos de Negócio

### 1. Registro de Ponto

**Fluxo**:
1. Usuário clica em "Bater Ponto"
2. Sistema detecta tipo (entrada/saída)
3. Valida regras de negócio
4. Registra horário exato
5. Calcula horas trabalhadas
6. Atualiza dashboard em tempo real

**Regras de Validação**:
- Não pode bater ponto fora do horário permitido
- Intervalos mínimos entre registros
- Máximo de horas por dia
- Validação de IP e dispositivo

### 2. Cálculo de Horas Trabalhadas

**Algoritmo**:
```python
def calcular_horas_trabalhadas(registros):
    # Ordena registros por horário
    registros_ordenados = sorted(registros, key=lambda x: x.horario)
    
    total_minutos = 0
    entrada = None
    
    for reg in registros_ordenados:
        if reg.tipo == 'entrada' and entrada is None:
            entrada = reg.horario
        elif reg.tipo == 'saida' and entrada is not None:
            saida = reg.horario
            # Subtrai intervalo se aplicável
            intervalo = calcular_intervalo(entrada, saida, registros)
            total_minutos += (saida - entrada).total_seconds() / 60 - intervalo
            entrada = None
    
    return total_minutos
```

### 3. Solicitação de Ajuste

**Fluxo**:
1. Usuário identifica erro no registro
2. Solicita ajuste via interface
3. Gestor recebe notificação
4. Gestor aprova ou rejeita
5. Sistema ajusta registros
6. Banco de horas é atualizado

**Tipos de Ajuste**:
- Correção de horário
- Adição de registro faltante
- Remoção de registro incorreto
- Justificativa de atraso

### 4. Fechamento Mensal

**Fluxo**:
1. Sistema calcula horas trabalhadas
2. Compara com jornada esperada
3. Calcula saldo de banco de horas
4. Gera relatório para aprovação
5. Gestor aprova fechamento
6. Dados enviados para folha de pagamento

**Cálculos**:
- Horas trabalhadas = Σ (saída - entrada - intervalo)
- Horas extras = max(0, horas_trabalhadas - jornada_esperada)
- Saldo banco = saldo_anterior + horas_extras - horas_compensadas

## Solução de Problemas

### Problemas Comuns

1. **Registro de ponto falha**:
   - Verificar conexão com banco
   - Verificar regras de negócio
   - Verificar logs de validação

2. **Tarefas Celery não executam**:
   - Verificar RabbitMQ está rodando
   - Verificar worker está ativo
   - Verificar logs do Celery

3. **Cálculo de horas incorreto**:
   - Verificar registros de ponto
   - Verificar jornada configurada
   - Recalcular manualmente

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5025/api/ping

# Verificar status Celery
celery -A tasks.celery inspect ping

# Listar tarefas agendadas
celery -A tasks.celery inspect scheduled

# Verificar logs
tail -f /var/log/cronos/cronos.log
tail -f /var/log/cronos/celery.log
```