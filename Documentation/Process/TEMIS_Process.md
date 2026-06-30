# Documentação de Processos - Têmis (Gestão de Contratos)

## Processos de Negócio

### 1. Ciclo de Vida de um Contrato

**Fluxo**:
1. Usuário autenticado cria um contrato informando: título, tipo, número, objeto, contraparte e valor
2. Contrato nasce no status `rascunho`
3. Usuário faz upload do arquivo do contrato (PDF, DOC, DOCX, ODT, TXT)
4. Signatários são adicionados com nome e e-mail
5. Status avança conforme aprovação: `rascunho` → `revisão` → `aprovado` → `assinado` → `vigente`
6. Sistema monitora datas de vencimento e dispara alertas automáticos
7. Ao vencer, status muda para `expirado`

**Statuses disponíveis**: `rascunho`, `revisão`, `aprovado`, `assinado`, `vigente`, `expirado`, `rescindido`, `cancelado`

**Regras**:
- Título do contrato é obrigatório
- Apenas usuários autenticados via Atlas podem criar ou editar contratos
- Todas as mudanças de status são registradas no audit log com timestamp e usuário responsável

---

### 2. Upload e Versionamento de Arquivos

**Fluxo**:
1. Usuário seleciona arquivo do contrato (PDF, DOC, DOCX, ODT ou TXT)
2. Sistema valida a extensão do arquivo
3. Arquivo é salvo com nome seguro: `{id_contrato}_{timestamp}_{nome_original}`
4. Versão anterior é mantida — sistema registra histórico de versões com observações
5. Usuário pode visualizar ou baixar qualquer versão anterior

**Regras**:
- Formatos aceitos: `.pdf`, `.doc`, `.docx`, `.odt`, `.txt`
- Nenhum tamanho máximo definido — limitado pelo disco do servidor
- Arquivo atual e histórico ficam em `db.FILES_DIR` no servidor

---

### 3. Assinatura Digital por Token

**Fluxo**:
1. Signatário é adicionado ao contrato com nome e e-mail
2. Sistema gera um token único de assinatura para o signatário
3. Link de assinatura é enviado ao signatário por e-mail (via notifier)
4. Signatário acessa o link `/api/sign/{token}`
5. Sistema valida o token e registra a assinatura com timestamp
6. Após todos os signatários assinarem, contrato pode avançar para `assinado`

**Regras**:
- Token de assinatura é de uso único
- Assinatura registra: nome, e-mail, data/hora
- Audit log registra cada assinatura realizada

---

### 4. Gestão Fiscal

**Fluxo**:
1. Usuário cadastra tributos vinculados ao contrato (ISS, IRRF, PIS, COFINS, etc.)
2. Informa: tipo de tributo, alíquota, base de cálculo, valor estimado
3. Cadastra eventos fiscais com data prevista (ex: "Emissão de NF mensal", "Recolhimento de ISS")
4. Sistema gera resumo fiscal com totais de tributos por categoria
5. Eventos fiscais vencidos aparecem no painel de alertas
6. Usuário marca eventos como "realizado" com data e valor real

**Regras**:
- Tipo de tributo e data prevista são obrigatórios para eventos fiscais
- Evento realizado registra: data realizada, valor realizado e observações

---

### 5. Análise de Riscos por IA (Claude)

**Fluxo**:
1. Usuário acessa a aba "Análise IA" do contrato
2. Clica em "Analisar Contrato"
3. Têmis monta um prompt com os dados do contrato (título, tipo, valor, vigência, tributos, eventos)
4. Envia para a API da Anthropic (Claude Haiku)
5. Resultado retorna estruturado em JSON com:
   - **Score de risco** (1–10)
   - **Resumo executivo** (2–3 frases)
   - **Riscos identificados** (título, descrição, severidade: alto/médio/baixo)
   - **Cláusulas faltantes** sugeridas
   - **Recomendações** práticas
6. Análise é salva e exibida em painel dedicado
7. Usuário pode solicitar nova análise a qualquer momento

**Pré-requisitos**:
- Chave da API Anthropic configurada em Configurações → IA
- Conexão com a internet

**Regras**:
- A análise é baseada nos dados cadastrados — não lê o arquivo do contrato diretamente
- Considera legislação brasileira (CLT, Código Civil, tributação federal/estadual/municipal)

---

### 6. Alertas Automáticos por E-mail

**Fluxo**:
1. Scheduler verifica diariamente contratos e eventos fiscais
2. Identifica:
   - Contratos expirando nos próximos N dias (configurável)
   - Contratos já expirados
   - Eventos fiscais vencidos
   - Eventos fiscais nos próximos 15 dias
   - Assinaturas pendentes
3. Envia e-mail de alerta para o responsável configurado
4. Registra o alerta no log de alertas

**Pré-requisitos**:
- Gmail configurado em Configurações (usuário + App Password)
- Scheduler deve estar ativo (iniciado com o módulo)

**Configuração de alertas**:
- Período de antecedência para contratos expirando (padrão: 60 dias)
- E-mail de destino
- Ativar/desativar tipos de alerta individualmente

---

## Solução de Problemas

### Contrato não aparece na lista
- Verifique o filtro de status ativo na listagem
- Confirme que o contrato não foi excluído (verificar audit log)

### Assinatura via link não funciona
- Token pode ter expirado ou já ter sido usado
- Gere um novo signatário para reenviar o link

### Análise de IA retorna erro
- Verifique se a chave Anthropic está configurada em Configurações → IA
- Confirme que a biblioteca `anthropic` está instalada: `pip install anthropic`
- Verifique a conexão com a internet

### E-mails de alerta não são enviados
- Confirme que a senha configurada é um **App Password** do Gmail (não a senha da conta)
- Ative o acesso a apps menos seguros ou 2FA + App Password na conta Gmail
- Teste com "Enviar e-mail de teste" em Configurações

### Arquivo não faz upload
- Verifique o formato: apenas `.pdf`, `.doc`, `.docx`, `.odt`, `.txt` são aceitos
- Verifique permissões de escrita na pasta `db.FILES_DIR` do servidor
