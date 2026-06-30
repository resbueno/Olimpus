# Resumo de Implementação — Cálculo de Férias CLT

## O que foi implementado

### 1. **Módulo de Cálculo de Férias** (`ferias_calc.py`)
Classe `FeriasCalculador` com todas as regras da CLT:

- ✅ **Cálculo de dias de férias**: Proporcional (2,5 dias/mês) ou integral (30 dias)
- ✅ **Cálculo de valor**: Salário/30 × dias + adicional de 1/3
- ✅ **Validação de fracionamento**: Máximo 3 períodos com regras de mínimos
- ✅ **Geração de opções**: Todas as opções válidas de divisão de férias
- ✅ **Cálculo completo**: Integrado com fracionamento

### 2. **Alterações no Banco de Dados** (`database.py`)

#### Nova coluna em `users`:
- `salario_mensal REAL DEFAULT 0` — Salário para cálculo de férias

#### Novas tabelas:
- `ferias_periodos` — Armazena cada período de um fracionamento
  - `ferias_id` — Referência à solicitação de férias
  - `sequencia` — Ordem (1, 2, 3)
  - `data_inicio`, `data_fim` — Datas do período
  - `duracao_dias` — Número de dias

#### Alteração em `ferias`:
- `fracionado INTEGER DEFAULT 0` — Flag indicando se tem períodos

#### Funções adicionadas:
- `create_ferias_periodos()` — Cria períodos fracionados
- `get_ferias()` — Agora retorna períodos se fracionado

### 3. **Novos Endpoints da API** (`app.py`)

#### `POST /api/ferias/<user_id>/calcular`
Calcula valor das férias baseado em salário e dias.

**Resposta:**
```json
{
  "ok": true,
  "data": {
    "usuario": {"id": 1, "nome": "João"},
    "ferias": {
      "salario_mensal": 3000,
      "dias": 30,
      "valor_diario": 100,
      "valor_base": 3000,
      "valor_adicional": 1000,
      "valor_total": 4000
    }
  }
}
```

#### `GET /api/ferias/opcoes-fracionamento?dias=30`
Lista todas as opções válidas de divisão de férias.

**Resposta:** Array com 3+ opções (integral, 2 períodos, 3 períodos)

#### `POST /api/ferias/<ferias_id>/periodos`
Adiciona períodos fracionados a uma solicitação existente.

**Body:**
```json
{
  "periodos": [
    {"data_inicio": "2024-01-15", "data_fim": "2024-01-28", "duracao_dias": 14},
    {"data_inicio": "2024-06-01", "data_fim": "2024-06-08", "duracao_dias": 8},
    {"data_inicio": "2024-12-01", "data_fim": "2024-12-08", "duracao_dias": 8}
  ]
}
```

### 4. **Testes Unitários** (`test_ferias_calc.py`)

11 testes cobrindo:
- Cálculo de valor base
- Cálculo proporcional
- Validação de 1, 2 e 3 períodos (válidos e inválidos)
- Validação de períodos excedentes
- Geração de opções
- Cálculo de dias proporcionais
- Cálculo completo com fracionamento

**Status:** ✅ TODOS PASSANDO

### 5. **Documentação** (`FERIAS_CLT.md`)

Guia completo com:
- Regras CLT de férias
- Cálculo de valor (com exemplos)
- Regras de fracionamento
- Documentação de todos os endpoints
- Exemplos de uso (API e JavaScript)
- Fluxo completo de solicitação
- Validações implementadas
- Referências legais

## Regras CLT Implementadas

### Direito às Férias
- 30 dias corridos por ano de trabalho
- 2,5 dias por mês (proporcional)
- Adicional obrigatório de 1/3 (Lei 7.060/1982)

### Fracionamento (Divisão)
1. **Período Integral**: 30 dias em uma vez
2. **2 Períodos**: Mínimo 5 dias cada (ex: 14+16, 15+15, 20+10)
3. **3 Períodos**: Mínimo 14 no maior e 5 em cada um dos demais (ex: 14+8+8)

## Fluxo de Uso Recomendado

```
1. RH configura salário:
   PUT /api/users/1 {"salario_mensal": 3000}

2. Colaborador consulta opções:
   GET /api/ferias/opcoes-fracionamento?dias=30

3. Colaborador calcula valor:
   POST /api/ferias/1/calcular {"dias": 30}

4. Colaborador solicita férias:
   POST /api/ferias {"data_inicio": "...", "data_fim": "...", "user_id": 1}

5. (Opcional) RH adiciona fracionamento:
   POST /api/ferias/123/periodos {"periodos": [...]}

6. RH aprova:
   PUT /api/ferias/123/status {"status": "aprovada"}
```

## Validações Implementadas

✅ Máximo 3 períodos de férias  
✅ Mínimo 14 dias no maior período (se 3 períodos)  
✅ Mínimo 5 dias em cada período (se 2 ou 3)  
✅ Soma total deve ser 30 dias  
✅ Salário obrigatório (> 0)  
✅ Datas em formato YYYY-MM-DD  

## Arquivos Criados/Modificados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `ferias_calc.py` | **NOVO** | Módulo de cálculo CLT |
| `database.py` | MODIFICADO | Migração + funções de períodos |
| `app.py` | MODIFICADO | 3 novos endpoints |
| `FERIAS_CLT.md` | **NOVO** | Documentação completa |
| `test_ferias_calc.py` | **NOVO** | 11 testes unitários (todos passando) |

## Próximos Passos (Opcional)

- [ ] Integração com frontend (componentes para cálculo/visualização)
- [ ] Notificações por e-mail (aprovação/recusa)
- [ ] Exportação de relatório de férias em PDF
- [ ] Validação de datas (feriados, período de aviso prévio)
- [ ] Histórico de períodos utilizados no ano
- [ ] Dashboard RH com saldo de férias por colaborador
