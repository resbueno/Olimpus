# Documentação Técnica Detalhada - Minotauro (Merge de Planilhas)

## Visão Geral

**Nome**: Minotauro - Merge de Planilhas  
**Porta**: 5095  
**Tecnologias**: Flask, JavaScript Vanilla, SheetJS  

## Arquitetura do Frontend

### Estrutura do SPA (minotauro.html)

```
minotauro.html
├── <head> — estilos, fontes
├── Topbar
├── Shell
│   ├── Sidebar — configuração do merge
│   │   ├── Upload Planilha Principal
│   │   ├── Upload Planilha de Origem
│   │   ├── Seleção de chaves
│   │   ├── Seleção de colunas a trazer
│   │   ├── Tipo de join
│   │   └── Botão "Cruzar"
│   └── Panel — preview do resultado
│       ├── Tabela de dados
│       └── Estatísticas (total, matches, sem match)
└── <script> — lógica de merge
```

### Algoritmo de Merge

```javascript
function mergePlanilhas(main, origin, keyMain, keyOrigin, colsToBring, joinType) {
  // Indexa planilha de origem pela chave
  const originIndex = new Map();
  for (const row of origin) {
    const key = buildKey(row, keyOrigin);
    if (!originIndex.has(key)) originIndex.set(key, []);
    originIndex.get(key).push(row);
  }

  const result = [];

  // Percorre planilha principal
  for (const mainRow of main) {
    const key = buildKey(mainRow, keyMain);
    const matches = originIndex.get(key) || [];

    if (matches.length === 0) {
      if (joinType === 'inner') continue; // Inner: pula sem correspondência
      // Left/Full: mantém com colunas vazias
      const emptyRow = { ...mainRow };
      for (const col of colsToBring) emptyRow[col] = '';
      result.push(emptyRow);
    } else {
      for (const match of matches) {
        const merged = { ...mainRow };
        for (const col of colsToBring) merged[col] = match[col] ?? '';
        result.push(merged);
      }
    }
  }

  // Full Outer: adiciona linhas da origem sem match
  if (joinType === 'full') {
    const usedKeys = new Set(main.map(r => buildKey(r, keyMain)));
    for (const [key, rows] of originIndex) {
      if (!usedKeys.has(key)) result.push(...rows);
    }
  }

  return result;
}

function buildKey(row, cols) {
  return cols.map(c => String(row[c] ?? '').trim()).join('||');
}
```

### Leitura de Arquivos

```javascript
async function loadFile(file) {
  const buffer = await file.arrayBuffer();
  const wb = XLSX.read(buffer, { type: 'array', cellDates: true });
  const ws = wb.Sheets[wb.SheetNames[0]];
  return XLSX.utils.sheet_to_json(ws, { defval: '' });
}
```

## Implantação

### Requisitos
- Python 3.10+
- flask>=3.0
- flask-cors>=4.0

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `MINOTAURO_PORT` | `5095` | Porta HTTP |
| `MINOTAURO_HOST` | `127.0.0.1` | Interface de escuta |

## Limitações

- Sem suporte a cruzamento de mais de 2 planilhas simultâneas (encadeie manualmente)
- Arquivo resultante limitado pelo tamanho do heap JavaScript (~1 GB em navegadores modernos)
- Sem suporte nativo a planilhas com múltiplas abas — usa sempre a primeira aba
