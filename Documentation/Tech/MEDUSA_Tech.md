# Documentação Técnica Detalhada - Medusa (API Client)

## Visão Geral

**Nome**: Medusa - API Client  
**Porta**: 5060  
**Tecnologias**: Flask, JavaScript Vanilla, Fetch API  

## Arquitetura do Frontend

### Estrutura do SPA (medusa.html)

```
medusa.html
├── <head> — estilos CSS com variáveis de tema
├── Topbar — nome do módulo, botões globais
├── Wrap
│   ├── Sidebar (270px) — lista de coleções e requisições
│   │   ├── Header da sidebar (título + botão nova coleção)
│   │   └── Lista de q-items (requisições salvas)
│   └── Main — editor + resposta
│       ├── Barra de URL (método + URL + botão Enviar)
│       ├── Tabs — Headers | Params | Body | Auth
│       └── Painel de Resposta
└── <script> — toda a lógica
```

### Disparo de Requisições

```javascript
async function sendRequest(req) {
  const { method, url, headers, body } = req;

  const opts = {
    method,
    headers: new Headers(headers),
  };

  if (body && !['GET', 'HEAD'].includes(method)) {
    opts.body = body;
  }

  const t0 = performance.now();
  const response = await fetch(url, opts);
  const latency = Math.round(performance.now() - t0);

  return {
    status: response.status,
    statusText: response.statusText,
    headers: [...response.headers.entries()],
    body: await response.text(),
    latency,
  };
}
```

### Parser de cURL

```javascript
function parseCurl(curlStr) {
  const result = { method: 'GET', url: '', headers: {}, body: null };

  // Extrai URL
  const urlMatch = curlStr.match(/curl\s+(?:-[^\s]+\s+)*'?([^'\s]+)'?/);
  if (urlMatch) result.url = urlMatch[1];

  // Extrai método
  const methodMatch = curlStr.match(/-X\s+(\w+)/);
  if (methodMatch) result.method = methodMatch[1].toUpperCase();

  // Extrai headers
  const headerMatches = [...curlStr.matchAll(/-H\s+'([^']+)'/g)];
  for (const [, h] of headerMatches) {
    const [k, ...v] = h.split(':');
    result.headers[k.trim()] = v.join(':').trim();
  }

  // Extrai body
  const bodyMatch = curlStr.match(/(?:--data(?:-raw)?|-d)\s+'([^']+)'/);
  if (bodyMatch) {
    result.body = bodyMatch[1];
    if (!result.method || result.method === 'GET') result.method = 'POST';
  }

  return result;
}
```

### Persistência via localStorage

```javascript
// Salvar coleções
function saveCollections(collections) {
  localStorage.setItem('medusa_collections', JSON.stringify(collections));
}

// Carregar coleções
function loadCollections() {
  const raw = localStorage.getItem('medusa_collections');
  return raw ? JSON.parse(raw) : [];
}
```

## Indicadores de Método HTTP

| Método | Cor |
|--------|-----|
| GET | Azul (`--info`) |
| POST | Verde (`--success`) |
| PUT | Amarelo (`--warn`) |
| DELETE | Vermelho (`--danger`) |
| PATCH | Roxo (`--accent`) |

## Implantação

### Requisitos
- Python 3.10+
- flask>=3.0
- flask-cors>=4.0

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `MEDUSA_PORT` | `5060` | Porta HTTP |
| `MEDUSA_HOST` | `127.0.0.1` | Interface de escuta |

## Limitações Conhecidas

- Sem suporte a WebSockets (apenas HTTP/HTTPS)
- Requisições cross-origin dependem do CORS do servidor alvo
- `localStorage` limitado a ~5 MB — coleções muito grandes devem ser exportadas
