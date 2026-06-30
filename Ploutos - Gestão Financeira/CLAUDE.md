# Ploutos — Gestão Financeira · Guia de Retomada para o Claude

## Status do projeto
Implementação inicial concluída. O app está funcional e pronto para testes.

## Stack e padrões do Olimpus
- **Backend**: Python + Flask, porta **5080**
- **Banco**: SQLite (`ploutos.db`) — sem ORM, SQL puro via `sqlite3`
- **Auth**: delegada ao Atlas (localhost:5010) via `POST /api/auth/login`
- **Frontend**: single HTML file (`ploutos.html`) com CSS e JS embutidos
- **Roles**: `admin` > `financeiro` > `colaborador`
- **SSO**: `?atlas_token=<token>` na URL inicial → sessão automática
- **Fallback**: se Atlas offline, usa banco local (`check_password`)

## Arquivos
| Arquivo | Descrição |
|---|---|
| `app.py` | API Flask — todas as rotas REST |
| `database.py` | Persistência SQLite — todas as funções de dados |
| `ploutos.html` | SPA frontend — CSS + JS embutidos |
| `requirements.txt` | `flask>=3.0`, `flask-cors>=4.0` |
| `iniciar.bat` | Inicia o servidor em background (pythonw) na porta 5080 |
| `ploutos.db` | Banco SQLite (criado na primeira execução) |
| `ploutos.key` | Chave de sessão Flask (criada na primeira execução) |

## Módulos implementados
1. **Dashboard** — saldo do mês, a receber, a pagar, vencidos, próximos pagamentos
2. **Lançamentos** — CRUD completo de receitas e despesas com filtros
3. **Contas a Pagar** — view filtrada por despesas, baixa de pagamento
4. **Contas a Receber** — view filtrada por receitas, baixa de recebimento
5. **Fluxo de Caixa** — gráfico de barras + tabela anual (realizado)
6. **Orçamentos** — planejado vs realizado por categoria/mês com variance %
7. **Categorias** — CRUD de categorias por tipo (receita/despesa)
8. **Centros de Custo** — CRUD de centros de custo
9. **Configurações** — sincronização com Atlas

## Sincronização com Atlas
- Rota: `POST /api/atlas/sync` (requer role admin ou financeiro)
- Importa **empresas → departamentos** e **pessoas → usuários**
- Campo `atlas_id` na tabela `users` vincula com o id da pessoa no Atlas

## Tabelas do banco
```
departamentos   — id, nome, atlas_empresa_id, criado_em
users           — id, nome, email, senha_hash, role, departamento_id,
                  cargo, ativo, atlas_id, criado_em
centro_custos   — id, nome, descricao, ativo, criado_em
categorias      — id, nome, tipo (receita/despesa), centro_custo_id, ativo, criado_em
lancamentos     — id, descricao, valor, tipo, status, data_vencimento,
                  data_pagamento, categoria_id, favorecido, observacao,
                  criado_por, criado_em
orcamentos      — id, ano, mes, categoria_id, valor_planejado, criado_em
                  UNIQUE(ano, mes, categoria_id)
```

## Status dos lançamentos
- `pendente` → aguardando pagamento/recebimento
- `pago` → despesa paga
- `recebido` → receita recebida
- `cancelado` → cancelado (não entra no fluxo)

## Credenciais padrão (fallback sem Atlas)
- E-mail: `admin@olimpus.local`
- Senha: `Ploutos@2024`
- Role: `admin`

## O que pode ser feito a seguir (backlog)
- [ ] Recorrência de lançamentos (mensal/semanal)
- [ ] Anexos (NF, boleto) por lançamento
- [ ] Aprovação multi-nível de pagamentos
- [ ] Previsão de fluxo de caixa (próximos 30/60 dias) baseada em pendentes
- [ ] Conciliação bancária (importação de extrato OFX/CSV)
- [ ] Relatórios em PDF/Excel
- [ ] Multi-empresa (separação de dados por empresa do Atlas)
- [ ] Integração com Cronos (folha de pagamento → lançamento automático)
- [ ] Alertas de vencimento (e-mail ou notificação no Olimpus)

## Padrão de resposta da API
```json
{ "ok": true, "data": {...} }
{ "error": "mensagem de erro" }
```

## Como rodar
```bash
cd "Ploutos - Gestão Financeira"
python app.py
# Acesse: http://localhost:5080
```

## Contexto do Olimpus
O Ploutos faz parte do ecossistema Olimpus. Outros apps:
- **Atlas** (5010) — IAM central
- **Hera** (5041) — Gestão de Pessoas (RH)
- **Cronos** (5025) — Ponto Eletrônico
- **Oráculo** (5030) — Hub de notícias
- **Hércules** (5001) — Gestão de tarefas
