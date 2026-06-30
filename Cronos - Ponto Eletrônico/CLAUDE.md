# Cronos — Ponto Eletrônico · Guia de Retomada para o Claude

## Status do projeto
Implementação inicial concluída. O app está funcional e pronto para testes.

## Stack e padrões do Olimpus
- **Backend**: Python + Flask, porta **5025**
- **Banco**: SQLite (`cronos.db`) — sem ORM, SQL puro via `sqlite3`
- **Auth**: delegada ao Atlas (localhost:5010) via `POST /api/auth/login`
- **Frontend**: single HTML file (`cronos.html`) com CSS e JS embutidos
- **Roles**: `admin` > `rh` > `gestor` > `colaborador`
- **SSO**: `?atlas_token=<token>` na URL inicial → sessão automática
- **Fallback**: se Atlas offline, usa banco local (`check_password`)

## Arquivos
| Arquivo | Descrição |
|---|---|
| `app.py` | API Flask — todas as rotas REST |
| `database.py` | Persistência SQLite — motor de regras, cálculo de horas |
| `cronos.html` | SPA frontend — CSS + JS embutidos |
| `requirements.txt` | `flask>=3.0`, `flask-cors>=4.0` |
| `iniciar.bat` | Inicia o servidor em background (pythonw) na porta 5025 |
| `cronos.db` | Banco SQLite (criado na primeira execução) |
| `cronos.key` | Chave de sessão Flask (criada na primeira execução) |

## Módulos implementados
1. **Dashboard** — horas trabalhadas hoje, saldo do banco de horas, registros recentes
2. **Ponto** — bater ponto (entrada/saída/intervalo/retorno), histórico do dia
3. **Histórico** — espelho de ponto por período, filtros por colaborador (gestor/RH)
4. **Ajustes** — solicitação de ajuste de ponto pelo colaborador, aprovação pelo gestor
5. **Jornadas** — criação e edição de escalas (fixo/flexível/turno) com horários
6. **Banco de Horas** — saldo, lançamentos, compensação de horas
7. **Fechamentos** — fechamento mensal por colaborador, exportação CSV
8. **Feriados** — cadastro de feriados nacionais/regionais
9. **Usuários** — listagem e edição de colaboradores
10. **Configurações** — tolerâncias, adicional noturno, sincronização com Atlas

## Sincronização com Atlas
- Rota: `POST /api/atlas/sync` (requer role admin ou rh)
- Pede e-mail e senha do Atlas
- Importa **empresas → departamentos** e **pessoas → colaboradores**
- Campo `atlas_id` na tabela `users` vincula com o id da pessoa no Atlas
- Jornada padrão é atribuída automaticamente se nenhuma foi definida

## Tabelas do banco
```
departamentos           — id, nome, atlas_empresa_id, criado_em
users                   — id, nome, email, senha_hash, role, departamento_id,
                          cargo, gestor_id, jornada_id, ativo, atlas_id, criado_em
jornadas                — id, nome, tipo, hora_entrada, hora_saida,
                          hora_inicio_intervalo, hora_fim_intervalo,
                          carga_horaria_dia, dias_semana, ativo
registros_ponto         — id, user_id, tipo, timestamp, observacao,
                          latitude, longitude, origem, aprovado
ajustes_ponto           — id, user_id, data, tipo_atual, tipo_solicitado,
                          horario_atual, horario_solicitado, motivo,
                          status, aprovado_por, aprovado_em
feriados                — id, data, nome, tipo, criado_em
banco_horas             — user_id, saldo_minutos, atualizado_em
banco_horas_lancamentos — id, user_id, minutos, tipo, referencia, descricao, criado_em
fechamentos             — id, user_id, mes, ano, dias_trabalhados,
                          horas_trabalhadas_min, horas_extras_50_min,
                          horas_extras_100_min, adicional_noturno_min,
                          saldo_banco_min, status, fechado_em, fechado_por
configuracoes           — chave, valor
```

## Motor de regras (database.py)
- `calcular_dia(user_id, data)` — calcula trabalhado, extras 50%, extras 100%, noturno para um dia
- `resumo_mes(user_id, ano, mes)` — consolidado mensal com todos os totais
- Respeita jornada configurada para o colaborador
- Detecta feriados e finais de semana para classificar extras como 100%
- Adicional noturno configurável via tabela `configuracoes` (hora_noturna_inicio/fim, percentual)
- Tolerâncias de entrada/saída também configuráveis

## Credenciais padrão (fallback sem Atlas)
- E-mail: `admin@olimpus.local`
- Senha: `Cronos@2024`
- Role: `admin`

## O que pode ser feito a seguir (backlog)
- [ ] Geolocalização e foto no registro de ponto (UC1.2)
- [ ] QR Code para registro de ponto remoto
- [ ] Aprovação em lote de horas extras pelo gestor
- [ ] Relatório de espelho de ponto em PDF
- [ ] Integração com Hera (férias impactam banco de horas)
- [ ] Alertas de inconsistência (ponto sem saída, jornada ultrapassada)
- [ ] Acumulação automática de banco de horas no fechamento mensal
- [ ] Notificações por e-mail (ajuste aprovado/recusado)
- [ ] Multi-jornada semanal (escalas com dias alternados)

## Padrão de resposta da API
```json
{ "ok": true, "data": {...} }
{ "error": "mensagem de erro" }
```

## Como rodar
```bash
cd "Cronos - Ponto Eletrônico"
python app.py
# Acesse: http://localhost:5025
```

## Contexto do Olimpus
O Cronos faz parte do ecossistema Olimpus. Outros apps rodando:
- **Atlas** (5010) — IAM central, fonte de usuários e empresas/departamentos
- **Oráculo** (5030) — Hub de notícias, newsletters por departamento
- **Hércules** (5001) — Gestão de tarefas
- **Hera** (5041) — Gestão de Pessoas (RH)
