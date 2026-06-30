# Documentação Técnica - Higeia (Higienizador de Bases)

## Visão Geral

**Nome**: Higeia - Higienizador de Bases  
**Porta**: 8501  
**Prioridade**: MÉDIA  
**Tecnologias**: Flask, JavaScript (Vanilla), SheetJS  
**Responsável**: Equipe de Dados  

## Arquitetura

### Componentes Principais

```mermaid
graph TD
    A[Higeia - Higienizador de Bases] --> B[Servidor Flask]
    A --> C[Frontend SPA]
    B --> D[/ — serve higeia.html]
    B --> E[/api/ping]
    C --> F[Upload CSV/Excel]
    C --> G[Painel de Limpeza]
    C --> H[Preview de Dados]
    C --> I[Exportação]
    F --> J[SheetJS]
    G --> K[Normalização de Texto]
    G --> L[CPF/CNPJ/Telefone]
    G --> M[Deduplicação]
    G --> N[Filtros por Coluna]
```

### Modelo de Processamento

Toda a lógica de higienização é executada **no navegador** via JavaScript. O servidor Flask serve apenas o arquivo HTML — nenhum dado é enviado ao backend.

1. **Upload**: arquivo CSV ou Excel carregado via SheetJS
2. **Preview**: dados exibidos em tabela interativa
3. **Configuração**: usuário seleciona operações desejadas
4. **Processamento**: JavaScript aplica transformações na memória
5. **Exportação**: resultado exportado em CSV ou Excel

## Endpoints da API

| Endpoint | Método | Descrição | Resposta |
|----------|--------|-----------|----------|
| `/` | GET | Serve a interface Higeia | `higeia.html` |
| `/api/ping` | GET | Verificação de saúde | `{"ok": true}` |

## Funcionalidades

### Limpeza de Texto
- Remoção de espaços extras (leading, trailing, duplos)
- Normalização de acentos e caracteres especiais
- Conversão para maiúsculas ou minúsculas
- Remoção de caracteres não imprimíveis

### Normalização de Dados Estruturados
- **CPF**: formata ou remove máscara, valida dígitos verificadores
- **CNPJ**: formata ou remove máscara, valida estrutura
- **Telefone**: padroniza para formato nacional ou internacional
- **CEP**: formata com hífen ou sem máscara

### Deduplicação
- Identifica linhas duplicadas por uma ou mais colunas-chave
- Remove duplicatas mantendo a primeira ou última ocorrência
- Relatório de quantas linhas foram removidas

### Filtros
- Filtro por valor exato em qualquer coluna
- Filtro por valor vazio/nulo
- Filtro por intervalo numérico ou de datas
- Remoção de linhas que atendem ao critério

### Exportação
- CSV com delimitador configurável (`,` ou `;`)
- Excel (.xlsx) com formatação mantida
- Download direto pelo navegador

## Stack Técnico

### Backend
- **Python** 3.10+
- **Flask** 3.0+ — servidor HTTP mínimo
- **flask-cors** 4.0+ — CORS para desenvolvimento local

### Frontend
- **JavaScript** Vanilla — sem frameworks
- **SheetJS (xlsx)** 0.20+ — leitura e escrita de planilhas
- **Outfit / Space Grotesk** — tipografia via Google Fonts
- Suporte a **modo escuro** nativo

## Implantação

### Requisitos
- Python 3.10+
- pip

### Inicialização

```bat
cd "Higeia - Higienizador de Bases"
iniciar.bat
```

O script instala dependências automaticamente e abre `http://localhost:8501`.

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `HIGEIA_PORT` | `8501` | Porta HTTP |
| `HIGEIA_HOST` | `127.0.0.1` | Interface de escuta |

## Segurança

- Nenhum dado é transmitido ao servidor — todo o processamento é local no navegador
- Sem banco de dados, sem persistência de arquivos no servidor
- CORS restrito a `127.0.0.1` em produção

## Monitoramento e Logging

- Log de erros no arquivo `higeia_erro.log` (ignorado pelo git)
- Verificação de saúde via `GET /api/ping`

## Solução de Problemas

### Arquivo muito grande não carrega
- SheetJS tem limite de memória baseado no navegador (~500 MB)
- Divida o arquivo em partes menores antes de importar

### Exportação com caracteres errados
- Certifique-se de que o arquivo de origem está em UTF-8 ou Latin-1
- SheetJS detecta a codificação automaticamente para Excel; para CSV, use o botão de codificação

### Porta 8501 ocupada
- Verifique se outra instância do Higeia já está rodando
- Altere `HIGEIA_PORT` na variável de ambiente ou no `iniciar.bat`
