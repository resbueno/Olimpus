# Documentação Técnica - Minotauro (Merge de Planilhas)

## Visão Geral

**Nome**: Minotauro - Merge de Planilhas  
**Porta**: 5095  
**Prioridade**: MÉDIA  
**Tecnologias**: Flask, JavaScript (Vanilla), SheetJS  
**Responsável**: Equipe de Dados  

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Minotauro - Merge de Planilhas] --> B[Servidor Flask]
    A --> C[Frontend SPA]
    B --> D[/ — serve minotauro.html]
    B --> E[/api/ping]
    C --> F[Upload de Planilhas]
    C --> G[Configuração de Merge]
    C --> H[Preview do Resultado]
    C --> I[Exportação]
    F --> J[SheetJS]
    G --> K[Chaves de Cruzamento]
    G --> L[Seleção de Colunas]
    G --> M[Tipo de Join]
    H --> N[Tabela Interativa]
```

### Modelo de Processamento

Todo o cruzamento de dados é executado **no navegador** via JavaScript. O servidor Flask serve apenas o HTML — nenhum dado trafega pelo backend.

## Endpoints da API

| Endpoint | Método | Descrição | Resposta |
|----------|--------|-----------|----------|
| `/` | GET | Serve a interface Minotauro | `minotauro.html` |
| `/api/ping` | GET | Verificação de saúde | `{"ok": true}` |

## Funcionalidades

### Upload de Planilhas
- Suporte a CSV, XLS e XLSX
- Múltiplos arquivos carregados simultaneamente
- Preview automático com contagem de linhas e colunas
- Detecção automática de cabeçalho

### Configuração de Cruzamento (VLOOKUP Visual)
- Seleção da coluna-chave em cada planilha
- Escolha das colunas a trazer da planilha de origem
- Suporte a múltiplas chaves (chave composta)
- Tipo de join configurável:
  - **Left Join**: mantém todas as linhas da planilha principal
  - **Inner Join**: mantém apenas linhas com correspondência
  - **Full Outer Join**: mantém todas as linhas de ambas

### Preview do Resultado
- Tabela interativa com as primeiras 1000 linhas
- Colunas de origem destacadas visualmente
- Linhas sem correspondência sinalizadas
- Contador de linhas com e sem match

### Exportação
- CSV com delimitador configurável
- Excel (.xlsx) mantendo tipagem de dados
- Download direto pelo navegador

## Stack Técnico

### Backend
- **Python** 3.10+
- **Flask** 3.0+
- **flask-cors** 4.0+

### Frontend
- **JavaScript** Vanilla
- **SheetJS (xlsx)** — leitura e escrita de planilhas
- **Outfit / Space Grotesk** — tipografia
- Suporte a **modo escuro**

## Implantação

### Requisitos
- Python 3.10+
- pip

### Inicialização

```bat
cd "Minotauro - Merge de Planilhas"
iniciar.bat
```

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `MINOTAURO_PORT` | `5095` | Porta HTTP |
| `MINOTAURO_HOST` | `127.0.0.1` | Interface de escuta |

## Segurança

- Nenhum dado é enviado ao servidor — processamento 100% local no navegador
- Sem banco de dados, sem persistência no servidor

## Solução de Problemas

### Planilha muito grande trava o navegador
- Arquivos acima de 50 MB podem esgotar a memória da aba
- Divida os arquivos em partes antes de importar

### Correspondência não encontrada para linhas que deveriam bater
- Verifique se há espaços extras nas chaves (Higeia pode ajudar a limpar)
- A comparação é case-sensitive por padrão — normalize antes do merge

### Colunas do resultado aparecem vazias
- Confirme que o nome da coluna-chave é idêntico nas duas planilhas
- Verifique se a planilha foi carregada com o cabeçalho correto detectado
