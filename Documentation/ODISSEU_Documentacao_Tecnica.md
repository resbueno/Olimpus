# Documentação Técnica - Odisseu (Business Intelligence)

## Visão Geral

**Nome**: Odisseu - Business Intelligence  
**Porta**: 5085  
**Prioridade**: MÉDIA  
**Tecnologias**: Flask, JavaScript (Vanilla), SheetJS  
**Responsável**: Equipe de Dados / Análise  

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Odisseu - Business Intelligence] --> B[Servidor Flask]
    A --> C[Frontend SPA]
    B --> D[/ — serve odisseu.html]
    B --> E[/api/ping]
    C --> F[Upload de Dados]
    C --> G[Configuração de Gráficos]
    C --> H[Painel de Visualizações]
    C --> I[Filtros e Segmentos]
    C --> J[Exportação de Relatórios]
    F --> K[SheetJS]
    G --> L[Eixo X / Y]
    G --> M[Tipo de Gráfico]
    G --> N[Agrupamentos]
```

### Modelo de Processamento

Todo o processamento analítico é executado **no navegador** via JavaScript. O servidor Flask serve apenas o HTML.

## Endpoints da API

| Endpoint | Método | Descrição | Resposta |
|----------|--------|-----------|----------|
| `/` | GET | Serve a interface Odisseu | `odisseu.html` |
| `/api/ping` | GET | Verificação de saúde | `{"ok": true}` |

## Funcionalidades

### Importação de Dados
- Suporte a CSV e Excel (XLS, XLSX)
- Detecção automática de tipos de coluna (numérico, data, texto)
- Preview com contagem de linhas, colunas e amostra de dados

### Tipos de Visualização
- **Barra**: comparação entre categorias
- **Linha**: evolução temporal de métricas
- **Pizza / Donut**: proporções e percentuais
- **Dispersão (Scatter)**: correlação entre duas métricas
- **Área**: acumulação temporal

### Configuração de Gráficos
- Seleção de eixo X (categorias ou datas)
- Seleção de eixo Y (valores numéricos)
- Agrupamento por coluna categórica
- Paleta de cores configurável
- Títulos e legendas editáveis

### Filtros Interativos
- Filtro por valor em qualquer coluna categórica
- Filtro por intervalo em colunas numéricas
- Filtro por período em colunas de data
- Filtros combinados com lógica AND

### Séries Temporais
- Agrupamento por: dia, semana, mês, trimestre, ano
- Funções de agregação: soma, média, mín, máx, contagem
- Comparação entre períodos (Ano Anterior, Mês Anterior)

### Exportação
- Gráfico como imagem PNG
- Dados filtrados como CSV ou Excel
- Relatório PDF com gráficos e tabela de dados

## Stack Técnico

### Backend
- **Python** 3.10+
- **Flask** 3.0+
- **flask-cors** 4.0+

### Frontend
- **JavaScript** Vanilla
- **SheetJS** — leitura de planilhas
- **Canvas API** — renderização de gráficos
- **Outfit / Space Grotesk** — tipografia
- Suporte a **modo escuro**

## Implantação

### Requisitos
- Python 3.10+
- pip

### Inicialização

```bat
cd "Odisseu - Business Intelligence"
iniciar.bat
```

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ODISSEU_PORT` | `5085` | Porta HTTP |
| `ODISSEU_HOST` | `127.0.0.1` | Interface de escuta |

## Segurança

- Nenhum dado é enviado ao servidor — análise 100% local no navegador
- Sem banco de dados, sem persistência no servidor

## Solução de Problemas

### Gráfico não renderiza
- Verifique se a coluna do eixo Y é numérica
- Colunas com texto em células numéricas causam falha na agregação — use Higeia para limpar antes

### Agrupamento temporal incorreto
- Certifique-se de que a coluna de data está no formato ISO (`YYYY-MM-DD`) ou foi detectada como data pelo SheetJS
- Datas em formato texto (`01/01/2026`) podem não ser reconhecidas

### Arquivo grande torna a interface lenta
- Para mais de 100k linhas, aplique filtros logo após o upload para reduzir o volume em memória
