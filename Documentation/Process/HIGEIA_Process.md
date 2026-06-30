# Documentação de Processos - Higeia (Higienizador de Bases)

## Processos de Negócio

### 1. Higienização de Base de Dados

**Fluxo**:
1. Usuário faz upload do arquivo CSV ou Excel
2. Sistema exibe preview dos dados com contagem de linhas e colunas
3. Usuário seleciona as colunas que serão processadas
4. Usuário configura as operações de limpeza desejadas
5. Clica em "Higienizar"
6. Sistema processa os dados no navegador e exibe resultado
7. Usuário revisa o resultado na tabela de preview
8. Usuário exporta o arquivo higienizado

**Regras**:
- Arquivo original nunca é modificado
- Processamento ocorre inteiramente no navegador (sem envio ao servidor)
- Resultado disponível imediatamente após o processamento

---

### 2. Normalização de CPF/CNPJ

**Fluxo**:
1. Usuário seleciona coluna com CPF ou CNPJ
2. Define se deseja formatar (com máscara) ou limpar (somente dígitos)
3. Higeia valida cada valor e sinaliza os inválidos
4. Valores inválidos ficam marcados em vermelho no preview
5. Usuário decide se mantém ou remove as linhas inválidas
6. Exporta o resultado normalizado

**Regras**:
- CPF válido: 11 dígitos, dígito verificador correto
- CNPJ válido: 14 dígitos, dígito verificador correto
- Valores não numéricos são tratados como inválidos

---

### 3. Deduplicação

**Fluxo**:
1. Usuário seleciona uma ou mais colunas como chave de deduplicação
2. Define critério de manutenção: primeira ou última ocorrência
3. Higeia identifica e destaca duplicatas
4. Exibe relatório: "X linhas duplicadas encontradas"
5. Usuário confirma a remoção
6. Resultado exibido sem as duplicatas

**Regras**:
- Comparação por igualdade exata (case-sensitive por padrão)
- Opção de comparação case-insensitive disponível
- Linhas com todos os campos da chave vazios não são consideradas duplicatas entre si

---

### 4. Exportação

**Fluxo**:
1. Após higienização, usuário clica em "Exportar"
2. Escolhe formato: CSV ou Excel (.xlsx)
3. Para CSV, escolhe delimitador (vírgula ou ponto e vírgula)
4. Browser faz o download automaticamente
5. Arquivo salvo localmente com sufixo `_higienizado`

---

## Solução de Problemas

### Arquivo não é carregado
- Verifique se o formato é CSV, XLS ou XLSX
- Arquivos protegidos por senha não são suportados
- Tamanho máximo recomendado: 100 MB

### Dados aparecem com codificação errada
- CSV: tente re-salvar o arquivo com codificação UTF-8 em um editor de texto
- Excel: SheetJS lê diretamente o formato binário, sem problemas de codificação

### Processamento lento
- Arquivos com mais de 50.000 linhas podem demorar alguns segundos
- Feche outras abas do navegador para liberar memória
