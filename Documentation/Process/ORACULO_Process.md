# Documentação de Processos - Oráculo (Hub de Notícias)

## Processos de Negócio

### 1. Publicação de Notícia

**Fluxo**:
1. Autor cria rascunho da notícia
2. Preenche título, conteúdo, categoria
3. Adiciona imagens e tags
4. Salva como rascunho
5. Envia para revisão
6. Editor revisa conteúdo
7. Editor aprova ou solicita correções
8. Notícia é publicada
9. Notificação enviada para assinantes

**Regras de Publicação**:
- Título deve ter 5-100 caracteres
- Conteúdo deve ter pelo menos 100 caracteres
- Deve ter pelo menos uma categoria
- Imagem de capa recomendada

### 2. Gestão de Newsletter

**Fluxo**:
1. Editor cria newsletter
2. Seleciona notícias e conteúdo
3. Define público-alvo
4. Agenda ou envia imediatamente
5. Sistema envia emails
6. Métricas de abertura são coletadas
7. Relatórios são gerados

**Tipos de Público**:
- Todos os usuários
- Departamento específico
- Função específica
- Usuários personalizados

### 3. Moderação de Comentários

**Fluxo**:
1. Usuário comenta em notícia
2. Comentário é salvo
3. Sistema verifica palavras proibidas
4. Comentário é publicado ou marcado para revisão
5. Moderador revisa se necessário
6. Comentário é aprovado ou rejeitado
7. Usuário é notificado

**Regras de Moderação**:
- Sem palavras ofensivas
- Sem links externos
- Máximo 500 caracteres
- Respeito às políticas da empresa

### 4. Análise de Engajamento

**Fluxo**:
1. Sistema coleta métricas de interação
2. Calcula taxas de engajamento
3. Identifica notícias populares
4. Gera relatórios para comunicação
5. Sugere melhorias de conteúdo
6. Ajusta estratégia de distribuição

**Métricas Chave**:
- Número de visualizações
- Taxa de curtidas
- Número de comentários
- Tempo médio de leitura
- Taxa de abertura (newsletter)

## Solução de Problemas

### Problemas Comuns

1. **Notícias não aparecem**:
   - Verificar status de publicação
   - Verificar data de publicação
   - Verificar permissões

2. **Busca não funciona**:
   - Verificar conexão com Elasticsearch
   - Verificar índices estão criados
   - Reindexar conteúdo

3. **Newsletter não envia**:
   - Verificar configuração de email
   - Verificar lista de inscritos
   - Verificar logs de envio

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5030/api/ping

# Testar busca
curl -X POST http://localhost:5030/api/search -d '{"query": "teste"}' -H "Content-Type: application/json"

# Verificar status Elasticsearch
curl http://localhost:9200/_cluster/health

# Verificar logs
tail -f /var/log/oraculo/oraculo.log
```