# Documentação de Processos - Medusa (API Client)

## Processos de Negócio

### 1. Criação e Disparo de Requisição HTTP

**Fluxo**:
1. Usuário cria uma nova requisição (botão "+")
2. Informa o método HTTP (GET, POST, PUT, PATCH, DELETE, etc.)
3. Informa a URL de destino
4. Configura headers necessários (ex: `Authorization`, `Content-Type`)
5. Para métodos com body (POST, PUT, PATCH), informa o payload
6. Clica em "Enviar"
7. Resposta é exibida no painel direito: status, latência, headers e body

**Regras**:
- URL deve ser válida (iniciar com `http://` ou `https://`)
- Body JSON é validado antes do envio — erros de sintaxe são destacados
- Requisições com erro de rede exibem mensagem explicativa

---

### 2. Importação via cURL

**Fluxo**:
1. Usuário copia um comando `curl` (ex: do DevTools do navegador)
2. Cola no campo de importação do Medusa
3. Medusa parseia automaticamente: método, URL, headers e body
4. Requisição é preenchida no editor
5. Usuário revisa e dispara

**Exemplo de cURL suportado**:
```bash
curl -X POST https://api.exemplo.com/users \
  -H "Authorization: Bearer token123" \
  -H "Content-Type: application/json" \
  -d '{"nome": "João", "email": "joao@exemplo.com"}'
```

---

### 3. Organização em Coleções

**Fluxo**:
1. Usuário cria uma coleção (ex: "API de Produção", "Testes de QA")
2. Salva requisições dentro da coleção
3. Coleções ficam listadas na sidebar esquerda
4. Usuário pode exportar a coleção como JSON para compartilhar com o time
5. Outro usuário importa o JSON e tem acesso às mesmas requisições

---

### 4. Importação de HAR

**Fluxo**:
1. Usuário abre o DevTools do navegador (F12)
2. Acessa a aba Network
3. Reproduz o fluxo que deseja replicar
4. Exporta como `.har` (botão direito → "Save all as HAR")
5. No Medusa, usa "Importar HAR"
6. Todas as requisições capturadas são importadas como coleção

---

## Solução de Problemas

### Resposta vazia ou erro de rede
- Verifique se o servidor alvo está acessível: `ping <hostname>`
- Verifique se o HTTPS está ativo e o certificado é válido
- Requisições para `localhost` de diferentes portas podem ser bloqueadas por CORS

### Body não é enviado em requisição GET
- Comportamento correto — GET não suporta body por especificação HTTP
- Use POST se precisar enviar dados no corpo

### JSON inválido no body
- O editor destaca erros de sintaxe em vermelho
- Verifique vírgulas extras, aspas duplas em todas as chaves e valores string
