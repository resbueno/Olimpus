# Hera — Gestão de Pessoas · Guia de Retomada para o Claude

## Status do projeto
Implementação inicial concluída. O app está funcional e pronto para testes.

## Stack e padrões do Olimpus
- **Backend**: Python + Flask, porta **5041**
- **Banco**: SQLite (`hera.db`) — sem ORM, SQL puro via `sqlite3`
- **Auth**: delegada ao Atlas (localhost:5010) via `POST /api/auth/login`
- **Frontend**: single HTML file (`hera.html`) com CSS e JS embutidos
- **Roles**: `admin` > `rh` > `colaborador`
- **SSO**: `?atlas_token=<token>` na URL inicial → sessão automática
- **Fallback**: se Atlas offline, usa banco local (`check_password`)

## Arquivos
| Arquivo | Descrição |
|---|---|
| `app.py` | API Flask — todas as rotas REST |
| `database.py` | Persistência SQLite — todas as funções de dados |
| `hera.html` | SPA frontend — CSS + JS embutidos |
| `requirements.txt` | `flask>=3.0`, `flask-cors>=4.0` |
| `iniciar.bat` | Inicia o servidor em background (pythonw) |
| `hera.db` | Banco SQLite (criado na primeira execução) |
| `hera.key` | Chave de sessão Flask (criada na primeira execução) |

## Módulos implementados
1. **Dashboard** — stats, kudos recentes, aniversariantes do mês
2. **Colaboradores** — diretório com busca/filtro, edição de perfil
3. **Onboarding** — checklist por colaborador, etapas configuráveis
4. **Férias** — solicitação, aprovação/recusa pelo RH
5. **Avaliações 360°** — ciclos de avaliação, respostas por avaliador/avaliado
6. **Feedbacks** — positivo/construtivo/sugestão entre colaboradores
7. **Kudos** — mural de reconhecimento com feed público
8. **PDI** — planos de desenvolvimento + ações com prazo e status
9. **Treinamentos** — catálogo + inscrição + conclusão com nota
10. **Relatórios** — colaboradores por departamento, férias pendentes
11. **Configurações** — sincronização com Atlas (empresas → departamentos, pessoas → colaboradores)

## Sincronização com Atlas
- Rota: `POST /api/atlas/sync` (requer role admin ou rh)
- Pede e-mail e senha do Atlas
- Importa **empresas → departamentos** e **pessoas → colaboradores**
- Pessoas recém-criadas ganham onboarding inicializado automaticamente
- Campo `atlas_id` na tabela `users` vincula com o id da pessoa no Atlas

## Tabelas do banco
```
departamentos       — id, nome, atlas_empresa_id
users               — id, nome, email, senha_hash, role, departamento_id, cargo,
                      data_admissao, gestor_id, foto_url, ativo, atlas_id
onboarding_etapas   — id, titulo, descricao, ordem, obrigatoria, ativo
onboarding_progresso— user_id, etapa_id, concluida, concluida_em, observacao
ferias              — user_id, data_inicio, data_fim, dias, status, aprovado_por
ciclos_avaliacao    — id, titulo, tipo, data_inicio, data_fim, ativo
avaliacoes          — ciclo_id, avaliado_id, avaliador_id, tipo_avaliador, nota_geral
feedbacks           — de_user_id, para_user_id, texto, tipo, visivel_gestor
kudos               — de_user_id, para_user_id, mensagem, valor
pdi                 — user_id, titulo, objetivo, periodo_inicio, periodo_fim, status
pdi_acoes           — pdi_id, descricao, prazo, status, concluida_em
treinamentos        — titulo, descricao, carga_horaria, modalidade, link
treinamento_inscricoes — treinamento_id, user_id, status, nota, concluido_em
```

## Credenciais padrão (fallback sem Atlas)
- E-mail: `admin@olimpus.local`
- Senha: `Hera@2024`
- Role: `admin`

## O que pode ser feito a seguir (backlog)
- [ ] Organograma visual (hierarquia gestor → subordinados)
- [ ] Exportação de relatórios para Excel/PDF
- [ ] Notificações por e-mail (férias aprovadas, feedback recebido)
- [ ] Ponto eletrônico (batidas, horas extras, banco de horas)
- [ ] Folha de pagamento simplificada
- [ ] Upload de foto de perfil
- [ ] Pulse surveys (pesquisas rápidas de engajamento)
- [ ] OKRs (objetivos e resultados-chave)
- [ ] Integração com Oráculo (newsletter de RH para o departamento)

## Padrão de resposta da API
```json
{ "ok": true, "data": {...} }
{ "error": "mensagem de erro" }
```

## Como rodar
```bash
cd "Hera - Gestão de Pessoas"
python app.py
# Acesse: http://localhost:5041
```

## Contexto do Olimpus
O Hera faz parte do ecossistema Olimpus. Outros apps rodando:
- **Atlas** (5010) — IAM central, fonte de usuários e empresas/departamentos
- **Oráculo** (5030) — Hub de notícias, newsletters por departamento
- **Hércules** (5001) — Gestão de tarefas
- **Argos** (outro) — Monitoração
