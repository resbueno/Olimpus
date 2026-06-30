# Documentação de Processos - Héstia (Intranet Corporativa)

## Processos de Negócio

### 1. Publicação de Notícias

**Fluxo**:
1. Usuário clica em "Criar Notícia"
2. Preenche título, conteúdo, tags
3. Sistema valida conteúdo
4. Notícia é salva no banco
5. Notificação enviada para seguidores
6. Notícia aparece no feed

**Validações**:
- Título deve ter 5-100 caracteres
- Conteúdo deve ter pelo menos 50 caracteres
- Tags limitadas a 5 por notícia

### 2. Gestão de Documentos

**Fluxo**:
1. Usuário faz upload de arquivo
2. Sistema valida tipo e tamanho
3. Arquivo salvo no MinIO
4. Metadados salvos no PostgreSQL
5. Documento indexado no Elasticsearch
6. Documento disponível para busca

**Regras**:
- Tamanho máximo: 50MB
- Tipos permitidos: PDF, DOCX, XLSX, PPTX, JPEG, PNG
- Nomes de arquivo sanitizados

### 3. Kudos e Reconhecimento

**Fluxo**:
1. Usuário seleciona colega
2. Escreve mensagem de reconhecimento
3. Sistema valida destinatário
4. Kudos salvo no banco
5. Notificação enviada
6. Kudos aparece no perfil

**Regras**:
- Máximo 5 kudos por dia por usuário
- Não pode enviar para si mesmo
- Mensagem limitada a 280 caracteres

### 4. Gestão de Comunidades

**Fluxo**:
1. Usuário cria comunidade
2. Define nome, descrição, privacidade
3. Sistema cria comunidade
4. Criador torna-se administrador
5. Outros usuários podem solicitar entrada
6. Administradores aprovam novos membros

**Tipos**:
- Pública: qualquer um pode entrar
- Privada: requer aprovação
- Secreta: não aparece em buscas

## Solução de Problemas

### Problemas Comuns

1. **Busca não funciona**:
   - Verificar conexão com Elasticsearch
   - Verificar índices estão criados
   - Reindexar conteúdo

2. **Upload falha**:
   - Verificar espaço em disco no MinIO
   - Verificar permissões de escrita
   - Verificar tamanho do arquivo

3. **Notificações não chegam**:
   - Verificar serviço de notificações
   - Verificar conexão com Hub
   - Verificar logs de notificação

4. **Performance lenta**:
   - Verificar índices do Elasticsearch
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5020/api/ping

# Testar busca
curl -X POST http://localhost:5020/api/search/news -d '{"query": "teste"}' -H "Content-Type: application/json"

# Verificar status Elasticsearch
curl http://localhost:9200/_cluster/health

# Verificar logs
tail -f /var/log/hestia/hestia.log
```