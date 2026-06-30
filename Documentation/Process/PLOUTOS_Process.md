# Documentação de Processos - Ploutos (Gestão Financeira)

## Processos de Negócio

### 1. Lançamento Financeiro

**Fluxo**:
1. Usuário seleciona tipo de lançamento
2. Preenche dados: descrição, valor, conta, categoria
3. Sistema valida saldo disponível
4. Lançamento é salvo no banco
5. Saldo da conta é atualizado
6. Fluxo de caixa é recalculado

**Validações**:
- Valor deve ser positivo
- Conta deve estar ativa
- Data não pode ser futura (para lançamentos manuais)
- Documento deve ser único

### 2. Contas a Pagar

**Fluxo**:
1. Usuário cadastra conta a pagar
2. Sistema valida dados do fornecedor
3. Conta é salva como "pendente"
4. Sistema envia alerta de vencimento
5. Usuário registra pagamento
6. Conta é marcada como "paga"
7. Lançamento é criado automaticamente

**Alertas**:
- 7 dias antes do vencimento
- No dia do vencimento
- 1 dia após vencimento (atraso)

### 3. Contas a Receber

**Fluxo**:
1. Usuário cadastra conta a receber
2. Sistema valida dados do cliente
3. Conta é salva como "pendente"
4. Sistema envia alerta de vencimento
5. Usuário registra recebimento
6. Conta é marcada como "recebida"
7. Lançamento é criado automaticamente

**Integração**:
- Envio de boleto por email
- Notificação de recebimento
- Reconciliação bancária

### 4. Fechamento Mensal

**Fluxo**:
1. Sistema consolida todos os lançamentos
2. Calcula saldo de cada conta
3. Gera DRE (Demonstração de Resultados)
4. Gera balanço patrimonial
5. Exporta dados para contabilidade
6. Envia relatórios para gestores
7. Arquiva dados do mês

**Relatórios Gerados**:
- DRE (Demonstração de Resultados)
- Balanço Patrimonial
- Fluxo de Caixa
- Contas a Pagar/Receber
- Análise por Centro de Custo

## Solução de Problemas

### Problemas Comuns

1. **Saldo incorreto**:
   - Verificar lançamentos
   - Recalcular saldo manualmente
   - Verificar integração com outros sistemas

2. **Relatórios não gerados**:
   - Verificar dados do período
   - Verificar permissões
   - Verificar logs de erro

3. **Integração com Iris falha**:
   - Verificar conexão com Iris
   - Verificar formato dos dados
   - Verificar logs de integração

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5080/api/ping

# Verificar saldo
curl -H "Authorization: Bearer TOKEN" http://localhost:5080/api/fluxo-caixa/saldo

# Verificar logs
tail -f /var/log/ploutos/ploutos.log
```