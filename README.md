# Olimpus

Plataforma integrada de gestão corporativa composta por módulos independentes, cada um inspirado em uma divindade da mitologia grega. Um Hub central (porta 5100) agrega todos os sistemas com autenticação unificada via Atlas.

---

## Módulos

| Sistema | Categoria | Porta | Descrição |
|---|---|---|---|
| **Atlas** | Gestão de Acessos | 5010 | IAM central — gerencia identidades, perfis e permissões de todos os sistemas do Olimpus |
| **Héstia** | Intranet | 5020 | Intranet corporativa: feed de notícias, documentos, diretório de pessoas, comunidades e eventos |
| **Cronos** | Ponto Eletrônico | 5025 | Controle de ponto e jornada: horas extras, adicionais noturnos, banco de horas e fechamento mensal |
| **Oráculo** | Hub de Notícias | 5030 | Central de inteligência: agrega notícias externas, KPIs internos e distribui newsletters segmentadas |
| **Hera** | Gestão de Pessoas | 5041 | RH completo: onboarding, folha de pagamento, avaliação 360°, PDI e gestão de férias |
| **Hermes** | Gestão de Ativos | 5050 | Patrimônio corporativo: cadastro, localização, depreciação e manutenção de ativos físicos e digitais |
| **Medusa** | API Client | 5060 | Construtor visual de requisições HTTP — cole cURL, monte headers e dispare contra qualquer API |
| **Iris** | Formulários e Workflow | 5070 | Form Builder com Workflow Engine: formulários drag-and-drop e fluxos de aprovação |
| **Ploutos** | Gestão Financeira | 5080 | Controle financeiro: lançamentos, contas a pagar/receber, fluxo de caixa e orçamentos |
| **Tiresias** | OCR & Documentos | 5090 | OCR local: extrai texto de notas fiscais, contratos e recibos sem enviar dados à nuvem |
| **Minotauro** | Merge de Planilhas | 5095 | Motor de VLOOKUP visual — cruza planilhas por chave sem fórmulas ou macros |
| **Argos** | Monitoração | 5000 | Monitora disponibilidade, tempo de resposta e capturas de tela de aplicações WEB em tempo real |
| **Hércules** | Gestão de Tarefas | 5001 | Gestão de tarefas e projetos internos com acompanhamento de demandas, prazos e equipes |
| **Odisseu** | Business Intelligence | — | Painel de BI interativo: gráficos, filtros, séries temporais e exportação de relatórios |
| **Higeia** | Higienização de Bases | 8501 | Limpeza de CSV/Excel: textos, CPF/CNPJ/telefones, deduplicação, filtros e exportação |

---

## Requisitos

- Python 3.10+
- pip

As dependências de cada módulo estão no seu próprio `requirements.txt`. O Hub instala `flask` e `flask-cors` automaticamente ao iniciar.

---

## Como usar

### Windows

Execute o script na raiz do projeto:

```bat
iniciar.bat
```

O script:
1. Verifica Python e pip
2. Instala dependências do Hub
3. Sobe o Atlas (autenticação)
4. Inicia o Hub na porta 5100 e abre o navegador
5. Inicia o Higeia em segundo plano (porta 8501)

Os demais módulos são iniciados sob demanda pelo Hub, ao clicar em cada sistema.

### macOS / Linux

```bash
bash iniciar.command
```

---

## Arquitetura

```
Olimpus Hub (porta 5100)
│
├── Atlas - Gestão de Acessos/     # IAM — sempre ativo, pré-requisito dos demais
├── Argos - Monitoração/
├── Cronos - Ponto Eletrônico/
├── Hera - Gestão de Pessoas/
├── Hércules - Gestão de Tarefas/
├── Hermes - Gestão de Ativos/
├── Héstia - Intranet Corporativa/
├── Higeia - Higienizador de Bases/
├── Iris - Gestão de Formulários e Workflow/
├── Medusa - API Client/
├── Minotauro - Merge de Planilhas/
├── Odisseu - Business Intelligence/
├── Oráculo - Hub de Notícias/
├── Ploutos - Gestão Financeira/
├── Têmis - Gestão de Contratos/
├── Tiresias - OCR/
├── app.py          # Hub central
├── olimpus.html    # Frontend do Hub
└── iniciar.bat     # Launcher Windows
```

Cada módulo é um servidor Flask independente. O Hub descobre os módulos automaticamente por varredura de diretório, lê o `olimpus.json` de cada pasta e gerencia autenticação via SSO com o Atlas.

---

## Segurança

- Autenticação centralizada no Atlas com tokens HMAC
- Sessões com cookie `HttpOnly` e expiração de 12 horas
- Permissões por sistema configuradas no Atlas (cada usuário vê apenas os módulos liberados)
- Chave de sessão persistida localmente em `olimpus.key` (não versionada)
