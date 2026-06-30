# Documentação Técnica - Olimpus Environment

## Visão Geral

Este diretório contém a documentação técnica completa para todos os aplicativos do ambiente Olimpus. Cada documento descreve em detalhes a arquitetura, endpoints da API, processos de negócio, integrações e procedimentos operacionais para cada aplicação.

## Estrutura da Documentação

```
Documentation/
├── INDEX.md                    # Este arquivo - Índice geral
├── ATLAS_Documentacao_Tecnica.md      # Gestão de Acessos (IAM)
├── HUB_Documentacao_Tecnica.md        # Portal Unificado
├── HESTIA_Documentacao_Tecnica.md     # Intranet Corporativa
├── CRONOS_Documentacao_Tecnica.md     # Ponto Eletrônico
├── HERA_Documentacao_Tecnica.md       # Gestão de Pessoas (RH)
├── IRIS_Documentacao_Tecnica.md        # Gestão de Formulários e Workflow
├── PLOUTOS_Documentacao_Tecnica.md    # Gestão Financeira
├── ORACULO_Documentacao_Tecnica.md    # Hub de Notícias
├── HERMES_Documentacao_Tecnica.md     # Gestão de Ativos
├── HERCULES_Documentacao_Tecnica.md  # Gestão de Tarefas
├── ARGOS_Documentacao_Tecnica.md      # Monitoração
├── TEMIS_Documentacao_Tecnica.md      # Gestão de Contratos
└── TIRESIAS_Documentacao_Tecnica.md   # OCR e Processamento de Documentos
```

## Aplicativos Documentados

### Aplicativos Críticos (Prioridade CRÍTICA)

| Aplicativo | Porta | Arquivo | Descrição |
|------------|-------|---------|-----------|
| **Atlas** | 5010 | [ATLAS_Documentacao_Tecnica.md](ATLAS_Documentacao_Tecnica.md) | Identity and Access Management (IAM) Central |
| **Hub** | 5100 | [HUB_Documentacao_Tecnica.md](HUB_Documentacao_Tecnica.md) | Portal Unificado de Acesso aos Apps |

### Aplicativos de Alta Prioridade

| Aplicativo | Porta | Arquivo | Descrição |
|------------|-------|---------|-----------|
| **Héstia** | 5020 | [HESTIA_Documentacao_Tecnica.md](HESTIA_Documentacao_Tecnica.md) | Intranet Corporativa e Colaboração |
| **Cronos** | 5025 | [CRONOS_Documentacao_Tecnica.md](CRONOS_Documentacao_Tecnica.md) | Ponto Eletrônico e Gestão de Jornada |
| **Hera** | 5041 | [HERA_Documentacao_Tecnica.md](HERA_Documentacao_Tecnica.md) | Gestão de Pessoas e RH |
| **Iris** | 5070 | [IRIS_Documentacao_Tecnica.md](IRIS_Documentacao_Tecnica.md) | Gestão de Formulários e Workflow |
| **Argos** | 5000 | [ARGOS_Documentacao_Tecnica.md](ARGOS_Documentacao_Tecnica.md) | Monitoração e Observabilidade |
| **Têmis** | 5020 | [TEMIS_Documentacao_Tecnica.md](TEMIS_Documentacao_Tecnica.md) | Gestão de Contratos e Obrigações |

### Aplicativos de Média Prioridade

| Aplicativo | Porta | Arquivo | Descrição |
|------------|-------|---------|-----------|
| **Ploutos** | 5080 | [PLOUTOS_Documentacao_Tecnica.md](PLOUTOS_Documentacao_Tecnica.md) | Gestão Financeira e Contabilidade |
| **Oráculo** | 5030 | [ORACULO_Documentacao_Tecnica.md](ORACULO_Documentacao_Tecnica.md) | Hub de Notícias e Comunicação |
| **Hércules** | 5001 | [HERCULES_Documentacao_Tecnica.md](HERCULES_Documentacao_Tecnica.md) | Gestão de Tarefas e Projetos |

### Aplicativos de Baixa Prioridade

| Aplicativo | Porta | Arquivo | Descrição |
|------------|-------|---------|-----------|
| **Hermes** | 5050 | [HERMES_Documentacao_Tecnica.md](HERMES_Documentacao_Tecnica.md) | Gestão de Ativos e Patrimônio |
| **Tiresias** | 5090 | [TIRESIAS_Documentacao_Tecnica.md](TIRESIAS_Documentacao_Tecnica.md) | OCR e Processamento de Documentos |

## Estrutura Padrão dos Documentos

Cada documento de aplicação segue a mesma estrutura para facilitar a consulta:

1. **Visão Geral** - Descrição geral, porta, prioridade, tecnologias
2. **Arquitetura** - Diagrama de componentes e fluxos principais
3. **Endpoints da API** - Lista completa de endpoints com métodos, parâmetros e respostas
4. **Banco de Dados** - Esquema do banco de dados com tabelas e índices
5. **Processos de Negócio** - Fluxos detalhados dos principais processos
6. **Integração com Outros Apps** - Como o aplicativo se integra com outros sistemas
7. **Segurança** - Medidas de segurança implementadas
8. **Monitoramento e Logging** - Métricas monitoradas e exemplos de logs
9. **Implantação** - Requisitos e processo de implantação
10. **Manutenção** - Procedimentos de backup, restore e atualização
11. **Solução de Problemas** - Problemas comuns e comandos úteis
12. **Roadmap** - Próximas versões e melhorias planejadas
13. **Contatos** - Informações de suporte

## Como Usar Esta Documentação

### Para Desenvolvedores
- Consulte os **Endpoints da API** para integração
- Veja o **Banco de Dados** para entender a estrutura de dados
- Revise os **Processos de Negócio** para entender os fluxos
- Use a seção **Implantação** para configurar ambientes

### Para Administradores
- Consulte **Implantação** para requisitos e configuração
- Use **Manutenção** para procedimentos operacionais
- Veja **Monitoramento e Logging** para configuração de monitoração
- Revise **Solução de Problemas** para diagnóstico

### Para Usuários Finais
- A documentação técnica é voltada para equipes técnicas
- Para documentação de usuário, consulte os manuais específicos

## Convenções Utilizadas

### Formatação
- **Negrito**: Termos importantes ou títulos
- `Código`: Comandos, endpoints, nomes de variáveis
- *Itálico*: Nomes de arquivos ou diretórios
- ```blocos```: Exemplos de código ou configuração

### Ícones
- ✅ - Funcionalidade implementada
- ⚠️ - Atenção ou advertência
- 📋 - Lista ou checklist
- 🔗 - Link ou referência

## Atualizações e Versões

### Histórico de Atualizações

| Data | Versão | Descrição |
|------|--------|-----------|
| 2026-04-20 | 1.0 | Documentação inicial completa para todos os apps |
| 2026-04-20 | 1.1 | Adicionados documentos para Têmis e Tiresias |

### Como Contribuir

1. **Reportar Erros**: Abra uma issue no repositório
2. **Sugerir Melhorias**: Envie um pull request
3. **Atualizar Documentação**: Siga o padrão estabelecido
4. **Revisar Alterações**: Participe das revisões de documentação

## Ferramentas Recomendadas

### Para Leitura
- **Visual Studio Code** - Com extensões Markdown
- **Typora** - Editor Markdown avançado
- **Obsidian** - Para conhecimento conectado

### Para Diagramação
- **Mermaid** - Para diagramas (usado nesta documentação)
- **Draw.io** - Para diagramas complexos
- **Lucidchart** - Para colaboração

### Para Desenvolvimento
- **Postman** - Para teste de APIs
- **DBeaver** - Para acesso a bancos de dados
- **pgAdmin** - Para PostgreSQL

## Glossário

### Termos Comuns

- **API**: Application Programming Interface
- **JWT**: JSON Web Token (usado para autenticação)
- **RBAC**: Role-Based Access Control
- **OCR**: Optical Character Recognition
- **SSO**: Single Sign-On
- **IAM**: Identity and Access Management
- **DRE**: Demonstração de Resultados do Exercício
- **LGPD**: Lei Geral de Proteção de Dados
- **OAuth2**: Protocolo de autorização
- **WebSocket**: Protocolo de comunicação bidirecional

### Termos Específicos do Olimpus

- **Atlas**: Sistema central de autenticação e autorização
- **Hub**: Portal unificado de acesso aos aplicativos
- **Héstia**: Intranet corporativa
- **Cronos**: Sistema de ponto eletrônico
- **Hera**: Sistema de gestão de pessoas
- **Iris**: Plataforma de automação de processos
- **Ploutos**: Sistema financeiro
- **Oráculo**: Hub de notícias
- **Hermes**: Gestão de ativos
- **Hércules**: Gestão de tarefas
- **Argos**: Monitoração
- **Têmis**: Gestão de contratos
- **Tiresias**: OCR e processamento de documentos

## Contatos

### Suporte Técnico
- **Email**: suporte@olimpus.local
- **Telefone**: (XX) XXXX-XXXX
- **Horário**: 08:00 - 18:00 (segunda a sexta)

### Documentação
- **Responsável**: Equipe de Arquitetura
- **Email**: arquitetura@olimpus.local
- **Atualizações**: Envie sugestões para este email

## Licença

Esta documentação é propriedade da Olimpus e destinada apenas para uso interno. Não distribuir sem autorização.

© 2026 Olimpus - Todos os direitos reservados.