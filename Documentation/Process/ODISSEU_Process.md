# Documentação de Processos - Odisseu (Business Intelligence)

## Processos de Negócio

### 1. Análise de Dados com Gráfico

**Fluxo**:
1. Usuário faz upload do CSV ou Excel com os dados
2. Odisseu detecta automaticamente os tipos de coluna
3. Usuário seleciona o tipo de gráfico desejado
4. Configura o eixo X (categorias ou datas)
5. Configura o eixo Y (métrica a visualizar)
6. Define agrupamento se necessário
7. Gráfico é renderizado automaticamente
8. Usuário ajusta filtros para segmentar os dados
9. Exporta o gráfico ou os dados resultantes

---

### 2. Análise de Série Temporal

**Fluxo**:
1. Usuário carrega dados com coluna de data
2. Seleciona tipo "Linha" ou "Área"
3. Define a coluna de data no eixo X
4. Define a métrica numérica no eixo Y
5. Escolhe granularidade: dia, semana, mês, trimestre, ano
6. Escolhe função de agregação: soma, média, contagem
7. Opcional: ativa comparação com período anterior
8. Visualiza a evolução no tempo

---

### 3. Criação de Relatório

**Fluxo**:
1. Usuário configura os gráficos desejados
2. Aplica filtros para o período ou segmento do relatório
3. Adiciona título e descrição ao painel
4. Clica em "Exportar Relatório"
5. Escolhe formato: PDF (com gráficos) ou Excel (com dados)
6. Download gerado pelo navegador

---

## Casos de Uso Comuns

| Análise | Eixo X | Eixo Y | Tipo de Gráfico |
|---------|--------|--------|-----------------|
| Faturamento mensal | Mês | Valor R$ | Linha / Área |
| Top produtos | Produto | Qtd vendida | Barra |
| Distribuição por região | Região | % do total | Pizza |
| Correlação preço vs volume | Preço unitário | Volume | Dispersão |
| Evolução de headcount | Mês de admissão | Colaboradores | Linha |

---

## Solução de Problemas

### Soma incorreta nos gráficos
- Verifique se a coluna numérica não tem texto mesclado (ex: "R$ 1.500")
- Use Higeia para limpar os valores antes de importar no Odisseu

### Filtro de data não funciona
- A coluna precisa ser detectada como data — células formatadas como texto não funcionam
- Tente converter a coluna para formato de data no Excel antes de exportar como CSV

### Gráfico de pizza com muitas fatias
- Limite as categorias a no máximo 10 para manter legibilidade
- Agrupe as menores categorias em "Outros" manualmente antes de importar
