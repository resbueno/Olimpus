# Documentação Técnica Detalhada - Odisseu (Business Intelligence)

## Visão Geral

**Nome**: Odisseu - Business Intelligence  
**Porta**: 5085  
**Tecnologias**: Flask, JavaScript Vanilla, SheetJS, Canvas API  

## Arquitetura do Frontend

### Estrutura do SPA (odisseu.html)

```
odisseu.html
├── <head> — estilos, fontes
├── Topbar — nome do módulo, botões globais
├── Shell
│   ├── Sidebar — configuração de visualizações
│   │   ├── Upload de dados
│   │   ├── Seleção de tipo de gráfico
│   │   ├── Configuração de eixos
│   │   ├── Filtros ativos
│   │   └── Opções de exportação
│   └── Panel — área de visualizações
│       ├── Canvas dos gráficos
│       └── Tabela de dados filtrados
└── <script> — engine de BI
```

### Pipeline de Análise

```javascript
async function analyzeData(rawData, config) {
  // 1. Filtrar dados
  let data = applyFilters(rawData, config.filters);

  // 2. Agregar por eixo X
  const aggregated = aggregate(data, config.xAxis, config.yAxis, config.aggFn);

  // 3. Ordenar
  const sorted = sortData(aggregated, config.sortBy, config.sortDir);

  // 4. Renderizar gráfico
  renderChart(sorted, config.chartType, config.palette);

  return { data: sorted, total: data.length };
}
```

### Motor de Agregação

```javascript
function aggregate(data, xCol, yCol, fn) {
  const groups = new Map();

  for (const row of data) {
    const key = String(row[xCol] ?? '');
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(parseFloat(row[yCol]) || 0);
  }

  return [...groups.entries()].map(([key, values]) => ({
    label: key,
    value: applyAggFn(values, fn),
  }));
}

function applyAggFn(values, fn) {
  switch (fn) {
    case 'sum':   return values.reduce((a, b) => a + b, 0);
    case 'avg':   return values.reduce((a, b) => a + b, 0) / values.length;
    case 'min':   return Math.min(...values);
    case 'max':   return Math.max(...values);
    case 'count': return values.length;
    default:      return values.reduce((a, b) => a + b, 0);
  }
}
```

### Agrupamento Temporal

```javascript
function groupByPeriod(date, period) {
  const d = new Date(date);
  switch (period) {
    case 'day':     return d.toISOString().slice(0, 10);
    case 'week':    return `${d.getFullYear()}-W${getWeek(d)}`;
    case 'month':   return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    case 'quarter': return `${d.getFullYear()}-Q${Math.floor(d.getMonth() / 3) + 1}`;
    case 'year':    return String(d.getFullYear());
  }
}
```

### Renderização de Gráficos

Os gráficos são desenhados via **Canvas API** nativa do navegador, sem dependências externas de charting.

```javascript
function renderBarChart(canvas, data, palette) {
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  const maxVal = Math.max(...data.map(d => d.value));
  const barW = (width - 80) / data.length;

  ctx.clearRect(0, 0, width, height);

  data.forEach((d, i) => {
    const barH = ((d.value / maxVal) * (height - 60));
    const x = 40 + i * barW;
    const y = height - 30 - barH;

    ctx.fillStyle = palette[i % palette.length];
    ctx.fillRect(x, y, barW - 4, barH);

    // Label eixo X
    ctx.fillStyle = '#666';
    ctx.font = '11px Outfit';
    ctx.textAlign = 'center';
    ctx.fillText(truncate(d.label, 10), x + barW / 2, height - 10);
  });
}
```

## Implantação

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ODISSEU_PORT` | `5085` | Porta HTTP |
| `ODISSEU_HOST` | `127.0.0.1` | Interface de escuta |

## Limitações

- Sem conexão direta a banco de dados — dados precisam ser exportados para CSV/Excel primeiro
- Gráficos 3D não suportados
- Sem drill-down interativo entre gráficos
- Exportação PDF depende da API `window.print()` do navegador
