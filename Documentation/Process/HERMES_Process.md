# Documentação de Processos - Hermes (Gestão de Ativos)

## Processos de Negócio

### 1. Cadastro de Ativo

**Fluxo**:
1. Usuário acessa cadastro de ativos
2. Preenche dados: nome, tipo, valor, série
3. Sistema gera código de patrimônio
4. Ativo é salvo no banco
5. QR Code é gerado
6. Etiqueta é impressa
7. Ativo é atribuído a localização

**Validações**:
- Código de patrimônio único
- Número de série único (se aplicável)
- Valor de aquisição positivo
- Vida útil válida

### 2. Movimentação de Ativos

**Fluxo**:
1. Usuário escaneia QR Code ou busca ativo
2. Seleciona nova localização
3. Informa motivo da movimentação
4. Sistema valida permissões
5. Movimentação é registrada
6. Ativo é atualizado
7. Responsáveis são notificados

**Tipos de Movimentação**:
- Transferência entre locais
- Empréstimo para usuário
- Devolução
- Manutenção externa

### 3. Gestão de Manutenção

**Fluxo**:
1. Sistema ou usuário identifica necessidade
2. Manutenção é agendada
3. Responsável é notificado
4. Manutenção é executada
5. Relatórios e custos são registrados
6. Manutenção é concluída
7. Ativo retorna ao serviço

**Tipos de Manutenção**:
- Preventiva (agendada)
- Corretiva (quebra)
- Preditiva (monitoramento)

### 4. Baixa de Ativos

**Fluxo**:
1. Usuário solicita baixa
2. Informa motivo (venda, sucata, etc.)
3. Gestor aprova solicitação
4. Ativo é marcado como baixado
5. Depreciação é calculada
6. Documentação é arquivada
7. Ativo é removido do inventário

**Motivos de Baixa**:
- Venda
- Sucata
- Doação
- Perda/Roubo
- Obsolescência

## Solução de Problemas

### Problemas Comuns

1. **QR Code não lê**:
   - Verificar qualidade da impressão
   - Verificar iluminação
   - Testar com outro leitor

2. **Movimentação falha**:
   - Verificar permissões
   - Verificar status do ativo
   - Verificar logs de erro

3. **Manutenção não agendada**:
   - Verificar disponibilidade
   - Verificar conflitos
   - Verificar logs

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5050/api/ping

# Gerar QR Code
curl -H "Authorization: Bearer TOKEN" http://localhost:5050/api/ativos/1/qrcode

# Verificar logs
tail -f /var/log/hermes/hermes.log
```