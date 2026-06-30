# Férias CLT — Guia Completo

## Visão Geral

O módulo de férias do Hera implementa as regras da CLT (Consolidação das Leis do Trabalho) para cálculo e gerenciamento de férias.

## Principais Regras CLT

### Direito às Férias
- **30 dias corridos** por ano de trabalho completo
- **2,5 dias por mês** de trabalho (proporcional)
- Período aquisitivo: 12 meses de trabalho

### Valor das Férias
- **Valor diário** = Salário mensal ÷ 30
- **Valor base** = Valor diário × Dias de férias
- **Adicional de 1/3** (Lei 7.060/1982) obrigatório
- **Valor total** = Valor base + Adicional (1/3 do valor base)

**Exemplo:**
- Salário: R$ 3.000,00
- Dias: 30
- Valor diário: R$ 100,00
- Valor base: R$ 3.000,00
- Adicional 1/3: R$ 1.000,00
- **Total: R$ 4.000,00**

### Fracionamento (Divisão) de Férias

As férias podem ser **divididas em até 3 períodos**:

#### Opção 1: Período Integral (1 período)
- **30 dias corridos** em uma única vez
- Sem restrições especiais

#### Opção 2: Fracionado em 2 Períodos
- **Mínimo 5 dias corridos** em cada período
- Exemplos válidos:
  - 14 dias + 16 dias
  - 15 dias + 15 dias
  - 20 dias + 10 dias

#### Opção 3: Fracionado em 3 Períodos
- **Mínimo 14 dias corridos** em um período
- **Mínimo 5 dias corridos** em cada um dos demais
- Exemplo padrão: 14 dias + 8 dias + 8 dias

**Restrição:** Um dos períodos em 3 frações deve ter no mínimo 14 dias, com no máximo 5 dias entre os dois períodos menores.

## Como Usar — Endpoints da API

### 1. Calcular Valor das Férias

**Endpoint:** `POST /api/ferias/<user_id>/calcular`

**Autenticação:** Requerida (colaborador vê suas férias, RH/Admin vê de qualquer um)

**Request Body:**
```json
{
  "dias": 30
}
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "usuario": {
      "id": 1,
      "nome": "João Silva"
    },
    "ferias": {
      "salario_mensal": 3000.00,
      "dias": 30,
      "valor_diario": 100.00,
      "valor_base": 3000.00,
      "valor_adicional": 1000.00,
      "valor_total": 4000.00
    }
  }
}
```

### 2. Listar Opções de Fracionamento

**Endpoint:** `GET /api/ferias/opcoes-fracionamento?dias=30`

**Autenticação:** Requerida

**Response:**
```json
{
  "ok": true,
  "data": {
    "opcoes": [
      {
        "id": 1,
        "nome": "Período Integral",
        "descricao": "Usar todas as férias em um único período",
        "periodos": [30],
        "valido": true,
        "observacao": "Sem restrições de data"
      },
      {
        "id": 2.0,
        "nome": "Fracionado em 2 períodos: 5 + 25 dias",
        "descricao": "5 dias em um período e 25 dias em outro",
        "periodos": [5, 25],
        "valido": true,
        "observacao": "Um período pode ser fracionado em até 2 vezes"
      },
      {
        "id": 3,
        "nome": "Fracionado em 3 períodos",
        "descricao": "Dividido em 14 + 8 + 8 dias",
        "periodos": [14, 8, 8],
        "valido": true,
        "observacao": "Máximo 3 períodos (mínimo 14 em um e 5 nos demais)"
      }
    ]
  }
}
```

### 3. Adicionar Períodos Fracionados

**Endpoint:** `POST /api/ferias/<ferias_id>/periodos`

**Autenticação:** Requerida (apenas RH/Admin)

**Request Body:**
```json
{
  "periodos": [
    {
      "data_inicio": "2024-01-15",
      "data_fim": "2024-01-28",
      "duracao_dias": 14
    },
    {
      "data_inicio": "2024-06-01",
      "data_fim": "2024-06-08",
      "duracao_dias": 8
    },
    {
      "data_inicio": "2024-12-01",
      "data_fim": "2024-12-08",
      "duracao_dias": 8
    }
  ]
}
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "periodos_adicionados": 3
  }
}
```

### 4. Solicitar Férias

**Endpoint:** `POST /api/ferias`

**Autenticação:** Requerida

**Request Body:**
```json
{
  "data_inicio": "2024-01-15",
  "data_fim": "2024-02-14",
  "user_id": 1,
  "observacao": "Férias planejadas para janeiro/fevereiro"
}
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "id": 123
  }
}
```

### 5. Listar Férias

**Endpoint:** `GET /api/ferias?user_id=1&status=pendente`

**Autenticação:** Requerida

**Response:**
```json
{
  "ok": true,
  "data": [
    {
      "id": 123,
      "user_id": 1,
      "user_nome": "João Silva",
      "data_inicio": "2024-01-15",
      "data_fim": "2024-02-14",
      "dias": 31,
      "status": "pendente",
      "fracionado": 1,
      "observacao": "Férias planejadas para janeiro/fevereiro",
      "criado_em": "2024-01-10T10:30:45"
    }
  ]
}
```

### 6. Atualizar Status da Solicitação

**Endpoint:** `PUT /api/ferias/<ferias_id>/status`

**Autenticação:** Requerida (apenas RH/Admin)

**Request Body:**
```json
{
  "status": "aprovada"
}
```

**Valores aceitos:** `"aprovada"` ou `"recusada"`

## Configurar Salário do Colaborador

Para que o cálculo de férias funcione, é necessário configurar o salário mensal do colaborador.

### Via API

**Endpoint:** `PUT /api/users/<user_id>`

**Autenticação:** Requerida

**Request Body:**
```json
{
  "salario_mensal": 3000.00
}
```

## Fluxo Completo de Férias

1. **RH/Admin** configura salário do colaborador:
   ```
   PUT /api/users/1 {"salario_mensal": 3000}
   ```

2. **Colaborador** consulta opções de férias:
   ```
   GET /api/ferias/opcoes-fracionamento?dias=30
   ```

3. **Colaborador** calcula valor das férias:
   ```
   POST /api/ferias/1/calcular {"dias": 30}
   ```

4. **Colaborador** solicita férias:
   ```
   POST /api/ferias {
     "data_inicio": "2024-01-15",
     "data_fim": "2024-02-14",
     "user_id": 1
   }
   ```

5. **(Opcional) RH/Admin** adiciona períodos fracionados:
   ```
   POST /api/ferias/123/periodos {
     "periodos": [
       {"data_inicio": "2024-01-15", "data_fim": "2024-01-28", "duracao_dias": 14},
       {"data_inicio": "2024-06-01", "data_fim": "2024-06-08", "duracao_dias": 8},
       {"data_inicio": "2024-12-01", "data_fim": "2024-12-08", "duracao_dias": 8}
     ]
   }
   ```

6. **RH/Admin** aprova/recusa a solicitação:
   ```
   PUT /api/ferias/123/status {"status": "aprovada"}
   ```

## Validações Implementadas

### Fracionamento
- ✅ Máximo 3 períodos
- ✅ Mínimo 14 dias no maior período (3 períodos)
- ✅ Mínimo 5 dias em cada um dos demais períodos
- ✅ Soma total deve ser 30 dias

### Salário
- ✅ Obrigatório para calcular férias
- ✅ Deve ser maior que 0
- ✅ Suporta valores com decimais (centavos)

### Datas
- ✅ Data de fim deve ser após data de início
- ✅ Formato obrigatório: `YYYY-MM-DD`

## Tabelas do Banco de Dados

### Tabela: `ferias`
```sql
CREATE TABLE ferias (
  id           INTEGER PRIMARY KEY,
  user_id      INTEGER NOT NULL,
  data_inicio  TEXT NOT NULL,
  data_fim     TEXT NOT NULL,
  dias         INTEGER NOT NULL,
  status       TEXT DEFAULT 'pendente',  -- pendente, aprovada, recusada
  fracionado   INTEGER DEFAULT 0,        -- 0 ou 1
  aprovado_por INTEGER,
  aprovado_em  TEXT,
  observacao   TEXT,
  criado_em    TEXT NOT NULL
);
```

### Tabela: `ferias_periodos`
```sql
CREATE TABLE ferias_periodos (
  id           INTEGER PRIMARY KEY,
  ferias_id    INTEGER NOT NULL,
  sequencia    INTEGER NOT NULL,         -- 1, 2, 3
  data_inicio  TEXT NOT NULL,
  data_fim     TEXT NOT NULL,
  duracao_dias INTEGER NOT NULL,
  status       TEXT DEFAULT 'pendente',
  criado_em    TEXT NOT NULL
);
```

## Módulo `ferias_calc.py`

### Classe: `FeriasCalculador`

#### Métodos Principais

**`calcular_dias_ferias(dias_trabalhados: int) -> int`**
- Calcula dias de férias proporcionais (2,5 dias/mês)

**`calcular_valor_ferias(salario_mensal, dias, incluir_adicional=True) -> Dict`**
- Retorna dicionário com valores discriminados

**`validar_fracionamento(periodos: List[int]) -> Tuple[bool, str]`**
- Valida conformidade com regras CLT

**`gerar_opcoes_fracionamento(dias_totais=30) -> List[Dict]`**
- Gera todas as opções válidas de fracionamento

**`calcular_ferias_completo(salario_mensal, dias_ferias, data_inicio, periodos=None) -> Dict`**
- Cálculo completo com fracionamento

## Exemplos de Uso (Frontend)

### Calcular Férias
```javascript
async function calcularFerias(userId, dias = 30) {
  const response = await fetch(`/api/ferias/${userId}/calcular`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dias })
  });
  return await response.json();
}
```

### Listar Opções de Fracionamento
```javascript
async function listarOpcoes(dias = 30) {
  const response = await fetch(`/api/ferias/opcoes-fracionamento?dias=${dias}`);
  return await response.json();
}
```

### Solicitar Férias Fracionadas
```javascript
async function solicitarFerias(userId, dataInicio, dataFim) {
  const response = await fetch('/api/ferias', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      data_inicio: dataInicio,
      data_fim: dataFim
    })
  });
  const { data } = await response.json();
  return data.id;
}

async function adicionarPeriodos(feriasId, periodos) {
  const response = await fetch(`/api/ferias/${feriasId}/periodos`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ periodos })
  });
  return await response.json();
}
```

## Referências Legais

- **CLT** (Consolidação das Leis do Trabalho) — Artigos 129-143
- **Lei 7.060/1982** — Adicional de 1/3 nas férias
- **Lei 8.213/1991** — Concessão proporcional de férias
- **Convenções Coletivas** — Podem prever condições mais favoráveis ao trabalhador
