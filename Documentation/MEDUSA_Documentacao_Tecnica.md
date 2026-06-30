# Documentação Técnica - Medusa (API Client)

## Visão Geral

**Nome**: Medusa - API Client  
**Porta**: 5060  
**Prioridade**: MÉDIA  
**Tecnologias**: Flask, JavaScript (Vanilla), SheetJS  
**Responsável**: Equipe de Desenvolvimento  

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Medusa - API Client] --> B[Servidor Flask]
    A --> C[Frontend SPA]
    B --> D[/ — serve medusa.html]
    B --> E[/api/ping]
    C --> F[Sidebar de Coleções]
    C --> G[Editor de Requisição]
    C --> H[Painel de Resposta]
    G --> I[URL + Método HTTP]
    G --> J[Headers]
    G --> K[Parâmetros Query]
    G --> L[Body / Payload]
    H --> M[Status + Latência]
    H --> N[Headers de Resposta]
    H --> O[Body formatado]
```

### Modelo de Requisição

Todas as requisições HTTP são disparadas **diretamente do navegador** usando a Fetch API. O servidor Flask serve apenas o arquivo HTML.

1. **Configuração**: usuário monta a requisição no editor
2. **Disparo**: JavaScript faz o `fetch()` direto para a API alvo
3. **Resposta**: resultado exibido com destaque de sintaxe

## Endpoints da API

| Endpoint | Método | Descrição | Resposta |
|----------|--------|-----------|----------|
| `/` | GET | Serve a interface Medusa | `medusa.html` |
| `/api/ping` | GET | Verificação de saúde | `{"ok": true}` |

## Funcionalidades

### Coleções de Requisições
- Criação e organização de requisições em coleções
- Persistência local via `localStorage`
- Importação de coleções via JSON
- Exportação de coleções para compartilhamento

### Editor de Requisição
- Suporte a métodos: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
- Editor de URL com suporte a variáveis `{{variavel}}`
- Aba de Headers: adicionar, editar, ativar/desativar headers
- Aba de Params: query parameters com toggle individual
- Aba de Body: JSON, form-data, x-www-form-urlencoded, raw text

### Importação de cURL
- Cole um comando `curl` e o Medusa extrai automaticamente:
  - Método HTTP
  - URL
  - Headers (`-H`)
  - Body (`-d`, `--data`, `--data-raw`)

### Importação de HAR
- Upload de arquivos `.har` (HTTP Archive)
- Importa todas as requisições capturadas
- Útil para replicar sessões do DevTools do navegador

### Painel de Resposta
- Status HTTP com cor indicativa (verde, amarelo, vermelho)
- Latência em milissegundos
- Headers de resposta listados
- Body formatado com destaque de sintaxe JSON
- Opção de visualização raw

## Stack Técnico

### Backend
- **Python** 3.10+
- **Flask** 3.0+ — servidor HTTP mínimo
- **flask-cors** 4.0+

### Frontend
- **JavaScript** Vanilla
- **SheetJS** — para eventuais importações de dados tabulares
- **Outfit / Space Grotesk** — tipografia
- Destaque de sintaxe JSON nativo
- Suporte a **modo escuro**

## Implantação

### Requisitos
- Python 3.10+
- pip

### Inicialização

```bat
cd "Medusa - API Client"
iniciar.bat
```

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `MEDUSA_PORT` | `5060` | Porta HTTP |
| `MEDUSA_HOST` | `127.0.0.1` | Interface de escuta |

## Segurança

- Requisições são feitas diretamente do navegador — o servidor Flask não atua como proxy
- CORS do alvo pode bloquear requisições do navegador; use o Medusa em ambiente de desenvolvimento
- Credenciais (tokens, senhas) são armazenadas apenas em `localStorage` — nunca enviadas ao servidor

## Solução de Problemas

### Requisição bloqueada por CORS
- O servidor alvo deve permitir requisições de `http://localhost:5060`
- Em ambientes de desenvolvimento, desative temporariamente o CORS no alvo ou use um proxy

### cURL com múltiplos `-H` não importa corretamente
- Certifique-se de colar o comando completo em uma única linha ou com `\` de continuação

### Coleções perdidas após reiniciar o navegador
- As coleções são salvas em `localStorage` — use "Exportar Coleção" para backup antes de limpar dados do browser
