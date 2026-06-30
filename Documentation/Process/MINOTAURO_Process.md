# Documentação de Processos - Minotauro (Merge de Planilhas)

## Processos de Negócio

### 1. Cruzamento de Planilhas (VLOOKUP Visual)

**Fluxo**:
1. Usuário faz upload da planilha principal (base que receberá os dados)
2. Faz upload da planilha de origem (fonte das colunas a trazer)
3. Seleciona a coluna-chave na planilha principal
4. Seleciona a coluna-chave correspondente na planilha de origem
5. Seleciona quais colunas deseja trazer da planilha de origem
6. Escolhe o tipo de join (Left, Inner, Full Outer)
7. Clica em "Cruzar"
8. Revisa o resultado no preview
9. Exporta o arquivo resultante

**Regras**:
- A comparação de chaves é feita por igualdade de string (case-sensitive)
- Linhas sem correspondência no Left Join ficam com valores vazios nas colunas trazidas
- O resultado mantém a ordem da planilha principal

---

### 2. Cruzamento com Chave Composta

**Fluxo**:
1. Usuário seleciona múltiplas colunas como chave em cada planilha
2. O Minotauro concatena as colunas-chave para formar uma chave única
3. O cruzamento é realizado com base na chave concatenada
4. Resultado apresenta as colunas trazidas para as linhas que tiveram correspondência completa

**Exemplo de uso**:
- Cruzar por **CPF + Competência** para trazer salário de uma tabela de folha de pagamento

---

### 3. Exportação do Resultado

**Fluxo**:
1. Após o cruzamento, usuário clica em "Exportar"
2. Escolhe formato: CSV ou Excel (.xlsx)
3. Para CSV, escolhe delimitador
4. Browser faz o download com o nome `resultado_merge_<data>.xlsx`

---

## Casos de Uso Comuns

| Caso | Planilha Principal | Planilha de Origem | Chave | Colunas Trazidas |
|------|-------------------|-------------------|-------|-----------------|
| Enriquecer cadastro | Clientes | CRM | CPF | Segmento, Valor LTV |
| Consolidar NFs | Pedidos | Nota Fiscal | Número do Pedido | Valor NF, Data Emissão |
| Cruzar folha | Colaboradores | Banco de Horas | Matrícula + Mês | Horas Extras |

---

## Solução de Problemas

### Nenhuma linha teve correspondência
- Verifique os tipos de dado: CPF "123.456.789-00" não bate com "12345678900"
- Use o Higeia para normalizar antes de importar no Minotauro
- Verifique se o cabeçalho foi detectado corretamente (primeira linha)

### Resultado tem mais linhas que a planilha principal
- Isso ocorre em Full Outer Join — troque para Left Join se quiser manter apenas as linhas da planilha principal

### Colunas com nome duplicado no resultado
- O Minotauro adiciona o sufixo `_origem` nas colunas que colidem com nomes existentes
