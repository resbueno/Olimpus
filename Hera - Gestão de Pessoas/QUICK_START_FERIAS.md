# Quick Start — Cálculo de Férias CLT

## 1. Configurar Salário do Colaborador

Antes de calcular férias, defina o salário mensal:

```bash
curl -X PUT http://localhost:5041/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"salario_mensal": 3000.00}'
```

## 2. Ver Opções de Divisão de Férias

```bash
curl http://localhost:5041/api/ferias/opcoes-fracionamento?dias=30
```

**Resposta:**
- Opção 1: 30 dias (período integral)
- Opção 2: 14 + 16 dias (2 períodos)
- Opção 3: 14 + 8 + 8 dias (3 períodos)

## 3. Calcular Valor das Férias

```bash
curl -X POST http://localhost:5041/api/ferias/1/calcular \
  -H "Content-Type: application/json" \
  -d '{"dias": 30}'
```

**Exemplo de Resposta:**
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

## 4. Solicitar Férias

```bash
curl -X POST http://localhost:5041/api/ferias \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "data_inicio": "2024-01-15",
    "data_fim": "2024-02-14"
  }'
```

**Resposta:**
```json
{
  "ok": true,
  "data": {
    "id": 123
  }
}
```

## 5. Adicionar Períodos Fracionados (RH/Admin)

```bash
curl -X POST http://localhost:5041/api/ferias/123/periodos \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

## 6. Aprovar Férias (RH/Admin)

```bash
curl -X PUT http://localhost:5041/api/ferias/123/status \
  -H "Content-Type: application/json" \
  -d '{"status": "aprovada"}'
```

## 7. Listar Férias

```bash
# Ver todas as férias
curl http://localhost:5041/api/ferias

# Ver férias de um usuário específico
curl http://localhost:5041/api/ferias?user_id=1

# Ver apenas pendentes
curl http://localhost:5041/api/ferias?status=pendente
```

## Exemplo Prático Passo a Passo

### Cenário: João Silva quer tirar 30 dias de férias

**Passo 1:** Admin configura salário dele (R$ 3.000/mês)
```bash
curl -X PUT http://localhost:5041/api/users/1 \
  -H "Content-Type: application/json" \
  -d '{"salario_mensal": 3000.00}'
```

**Passo 2:** João consulta quanto vai receber
```bash
curl -X POST http://localhost:5041/api/ferias/1/calcular \
  -H "Content-Type: application/json" \
  -d '{"dias": 30}'

# Resultado: R$ 4.000,00 (R$ 3.000 + R$ 1.000 de adicional)
```

**Passo 3:** João prefere dividir em 3 períodos e solicita
```bash
curl -X POST http://localhost:5041/api/ferias \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "data_inicio": "2024-01-15",
    "data_fim": "2024-02-14"
  }'

# Obtém: ferias_id = 123
```

**Passo 4:** RH define os 3 períodos
```bash
curl -X POST http://localhost:5041/api/ferias/123/periodos \
  -H "Content-Type: application/json" \
  -d '{
    "periodos": [
      {"data_inicio": "2024-01-15", "data_fim": "2024-01-28", "duracao_dias": 14},
      {"data_inicio": "2024-06-01", "data_fim": "2024-06-08", "duracao_dias": 8},
      {"data_inicio": "2024-12-01", "data_fim": "2024-12-08", "duracao_dias": 8}
    ]
  }'
```

**Passo 5:** RH aprova
```bash
curl -X PUT http://localhost:5041/api/ferias/123/status \
  -H "Content-Type: application/json" \
  -d '{"status": "aprovada"}'
```

✅ **Férias aprovadas!** João receberá R$ 4.000 em 3 períodos.

## Regras CLT Importantes

| Regra | Detalhe |
|-------|---------|
| **Dias** | 30 dias corridos por ano de trabalho |
| **Proporcional** | 2,5 dias por mês (se menos de 12 meses) |
| **Adicional** | 1/3 obrigatório (Lei 7.060/1982) |
| **Fracionamento** | Máximo 3 períodos |
| **Mínimo 1 período** | Sem restrição |
| **Mínimo 2 períodos** | 5 dias cada |
| **Mínimo 3 períodos** | 14 no maior, 5 nos demais |

## Testes Rápidos

Execute os testes para validar a implementação:

```bash
cd "Hera - Gestão de Pessoas"
python test_ferias_calc.py
```

Resultado esperado: **11 testes passando**

## Troubleshooting

**Erro: "Salário mensal não configurado"**
→ Configure o salário via `PUT /api/users/<id>` com `{"salario_mensal": XXX}`

**Erro: "Fracionamento inválido"**
→ Verifique se a soma dos períodos é 30 dias e se segue as regras de mínimos

**Erro: "Sem permissão"**
→ Apenas RH/Admin podem aprovar ou adicionar períodos; colaborador só vê suas próprias férias

## Documentação Completa

Consulte `FERIAS_CLT.md` para:
- Detalhes de cada endpoint
- Exemplos com JavaScript
- Referências legais
- Validações implementadas
