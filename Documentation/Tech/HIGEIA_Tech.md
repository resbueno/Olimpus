# Documentação Técnica Detalhada - Higeia (Higienizador de Bases)

## Visão Geral

**Nome**: Higeia - Higienizador de Bases  
**Porta**: 8501  
**Tecnologias**: Flask, JavaScript Vanilla, SheetJS  

## Arquitetura do Frontend

### Estrutura do SPA (higeia.html)

O Higeia é uma Single Page Application com toda a lógica embutida em um único arquivo HTML.

```
higeia.html
├── <head> — fontes, estilos CSS (modo claro/escuro), variáveis CSS
├── Topbar — nome do módulo, botões de ação global
├── Shell
│   ├── Sidebar (400px) — painel de configuração
│   │   ├── Drop zone para upload de arquivo
│   │   ├── Seleção de colunas
│   │   ├── Opções de limpeza de texto
│   │   ├── Opções de CPF/CNPJ/Telefone
│   │   ├── Opções de deduplicação
│   │   └── Botão "Higienizar"
│   └── Panel — preview da tabela de dados
└── <script> — toda a lógica de processamento
```

### Pipeline de Processamento

```javascript
// Fluxo principal de higienização
async function higienizar(data, config) {
  let rows = [...data];

  // 1. Limpeza de texto
  if (config.trim)       rows = trimFields(rows, config.cols);
  if (config.lower)      rows = toLowerCase(rows, config.cols);
  if (config.upper)      rows = toUpperCase(rows, config.cols);
  if (config.removeAccents) rows = normalizeAccents(rows, config.cols);

  // 2. Normalização estruturada
  if (config.cpf)        rows = normalizeCPF(rows, config.cpfCol, config.cpfMode);
  if (config.cnpj)       rows = normalizeCNPJ(rows, config.cnpjCol, config.cnpjMode);
  if (config.phone)      rows = normalizePhone(rows, config.phoneCol);

  // 3. Deduplicação
  if (config.dedup)      rows = deduplicate(rows, config.dedupKeys, config.dedupKeep);

  // 4. Filtros
  if (config.filter)     rows = applyFilters(rows, config.filters);

  return rows;
}
```

### Leitura de Arquivos com SheetJS

```javascript
// CSV
const wb = XLSX.read(text, { type: 'string', raw: false });

// Excel
const wb = XLSX.read(arrayBuffer, { type: 'array' });

const ws = wb.Sheets[wb.SheetNames[0]];
const data = XLSX.utils.sheet_to_json(ws, { defval: '' });
```

### Exportação

```javascript
// Para CSV
const csv = XLSX.utils.sheet_to_csv(ws, { FS: delimiter });
downloadFile(csv, 'text/csv', filename + '.csv');

// Para Excel
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, ws, 'Dados');
XLSX.writeFile(wb, filename + '.xlsx');
```

## Validação de CPF

```javascript
function validarCPF(cpf) {
  const digits = cpf.replace(/\D/g, '');
  if (digits.length !== 11 || /^(\d)\1+$/.test(digits)) return false;
  let sum = 0;
  for (let i = 0; i < 9; i++) sum += parseInt(digits[i]) * (10 - i);
  let rem = (sum * 10) % 11;
  if (rem === 10 || rem === 11) rem = 0;
  if (rem !== parseInt(digits[9])) return false;
  sum = 0;
  for (let i = 0; i < 10; i++) sum += parseInt(digits[i]) * (11 - i);
  rem = (sum * 10) % 11;
  if (rem === 10 || rem === 11) rem = 0;
  return rem === parseInt(digits[10]);
}
```

## Implantação

### Requisitos
- Python 3.10+
- flask>=3.0
- flask-cors>=4.0

### Inicialização
```bash
pip install -r requirements.txt
python app.py
```

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `HIGEIA_PORT` | `8501` | Porta HTTP |
| `HIGEIA_HOST` | `127.0.0.1` | Interface de escuta |

## Considerações de Performance

- SheetJS processa ~50 MB/s em CSV no Chrome moderno
- Excel binário (XLSX) é mais lento (~10 MB/s) por ser descomprimido on-the-fly
- Para bases acima de 100k linhas, recomenda-se dividir em lotes
- Deduplicação usa `Map` JavaScript — O(n) para comparações simples
