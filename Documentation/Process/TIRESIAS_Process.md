# Documentação de Processos - Tiresias (OCR)

## Processos de Negócio

### 1. Processamento de Documento

**Fluxo**:
1. Usuário faz upload do documento
2. Sistema valida tipo de arquivo
3. Documento é salvo no MinIO
4. Metadados são salvos no banco
5. Processamento OCR é iniciado
6. Texto é extraído
7. Dados são estruturados
8. Resultados são salvos
9. Usuário é notificado

**Tipos de Documento Suportados**:
- PDF
- JPEG/PNG
- TIFF
- DOCX (via conversão)

### 2. Validação de Resultados

**Fluxo**:
1. Usuário visualiza resultados OCR
2. Sistema destaca áreas de baixa confiança
3. Usuário corrige erros
4. Correções são salvas
5. Documento é marcado como validado
6. Dados são exportados
7. Relatório de qualidade é gerado

**Métricas de Qualidade**:
- Taxa de confiança média
- Número de correções
- Tempo de validação
- Precisão por campo

### 3. Processamento em Lote

**Fluxo**:
1. Usuário seleciona documentos
2. Define template de processamento
3. Inicia processamento em lote
4. Sistema processa documentos sequencialmente
5. Progresso é monitorado
6. Resultados são consolidados
7. Relatório final é gerado
8. Usuário é notificado

**Estratégias de Processamento**:
- Sequencial (padrão)
- Paralelo (para servidores potentes)
- Priorização por tipo de documento

### 4. Exportação de Dados

**Fluxo**:
1. Usuário seleciona documentos processados
2. Escolhe formato de exportação
3. Sistema gera arquivo
4. Dados são validados
5. Arquivo é disponibilizado para download
6. Exportação é registrada
7. Usuário recebe confirmação

**Formatos de Exportação**:
- JSON
- CSV
- Excel
- XML
- PDF (com OCR sobreposto)

## Processamento OCR

### Pré-processamento de Imagem

```python
def pre_processar_imagem(imagem):
    # Converter para escala de cinza
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    
    # Aplicar threshold
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Remover ruído
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    
    # Aumentar contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    
    return enhanced
```

### Extração de Texto

```python
def extrair_texto(imagem, template=None):
    # Configurar Tesseract
    config = '--psm 6'
    if template and template['language']:
        config += f' -l {template["language"]}'
    
    # Extrair texto
    texto = pytesseract.image_to_string(imagem, config=config)
    
    # Extrair dados estruturados se template fornecido
    dados = {}
    if template and template['fields']:
        for field in template['fields']:
            x, y, w, h = field['region']
            roi = imagem[y:y+h, x:x+w]
            dados[field['name']] = pytesseract.image_to_string(roi)
    
    return {
        'texto_completo': texto,
        'dados_extraidos': dados,
        'confianca': calcular_confianca(texto)
    }
```

### Pós-processamento

```python
def pos_processar(texto, template=None):
    # Limpar texto
    texto_limpo = limpar_texto(texto)
    
    # Aplicar correções baseadas em template
    if template and template['correcoes']:
        for correcao in template['correcoes']:
            texto_limpo = texto_limpo.replace(correcao['de'], correcao['para'])
    
    # Extrair dados estruturados
    dados = extrair_dados_estruturados(texto_limpo, template)
    
    return {
        'texto': texto_limpo,
        'dados': dados
    }
```

## Solução de Problemas

### Problemas Comuns

1. **OCR não processa**:
   - Verificar Tesseract instalado
   - Verificar permissões de arquivo
   - Verificar logs de erro

2. **Baixa precisão**:
   - Verificar qualidade do documento
   - Ajustar pré-processamento
   - Usar template específico

3. **Processamento lento**:
   - Verificar uso de GPU
   - Reduzir tamanho da imagem
   - Processar em lote

4. **Performance lenta**:
   - Verificar índices do banco
   - Verificar cache Redis
   - Analisar queries lentas

### Comandos Úteis

```bash
# Verificar saúde
curl http://localhost:5090/api/ping

# Testar OCR
tesseract --version

# Verificar logs
tail -f /var/log/tiresias/tiresias.log
```