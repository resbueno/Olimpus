# Frontend — Implementação de Férias CLT

## Alterações no `hera.html`

### 1. Nova Seção de Cálculo de Férias
**Localização:** Linha 363 (antes da tabela de solicitações)

Dois cards lado a lado:
- **Card 1: Calcular Valor das Férias**
  - Select para escolher colaborador
  - Input para dias (1-30)
  - Exibição do resultado com discriminação:
    - Salário mensal
    - Valor base (salário/30 × dias)
    - Adicional 1/3
    - Total (com adicional)

- **Card 2: Opções de Divisão**
  - Lista todas as opções válidas (integral, 2 períodos, 3 períodos)
  - Mostra períodos recomendados
  - Exibe observações importantes

### 2. Coluna "Fracionado" na Tabela
- Mostra "Sim" (em verde) ou "Não" para cada solicitação
- Indica se tem períodos adicionados

### 3. Botão "Fraccionar" para RH
- Aparece apenas para solicitações pendentes
- Disponível apenas para RH/Admin
- Abre modal para adicionar até 3 períodos

### 4. Modal Expandido de Solicitar Férias
- Mantém funcionalidade original
- Pronto para integração com seleção de fracionamento

## Novas Funções JavaScript

### `inicializarCalculoFerias()`
- Carregada ao abrir seção de férias
- Popula o select de colaboradores

### `atualizarCalculoFerias()`
- Acionada ao mudar colaborador ou dias
- Faz requisição POST a `/api/ferias/<user_id>/calcular`
- Exibe valores com formatação de moeda
- Carrega opções de fracionamento automaticamente

### `carregarOpcoesFracionamento(dias)`
- Requisição GET a `/api/ferias/opcoes-fracionamento?dias=30`
- Renderiza cada opção com detalhes
- Mostra observações importantes

### `openModalFracionarFerias(fid)`
- Abre modal para adicionar períodos
- Carrega dados da solicitação existente
- Exibe aviso com regras CLT

### `carregarPeriodsUI(fid)`
- Popula formulário com inputs para 3 períodos
- Pré-preenche com sugestões (14+8+8 ou ajustado)
- Define validação de dias (mínimos)

### `savePeriodsFerias(fid)`
- Valida se pelo menos um período foi preenchido
- Faz requisição POST a `/api/ferias/<fid>/periodos`
- Exibe toast de sucesso/erro
- Recarrega lista de férias

## Integração com o Sistema Existente

### Padrão de Navegação
- Seção é carregada via `loadSection('ferias')`
- Inicialização automática: `loadFerias()` + `inicializarCalculoFerias()`

### Padrão de API
- Usa `apiFetch()` existente
- Segue padrão de resposta: `{ok: true, data: ...}`

### Padrão de UI
- Modals via `showModal()` / `closeModal()`
- Toasts via `toast(msg, type)`
- Badges via `badge(text)`
- Formatação de datas via `fmtDate()`

### Estilos
- Novo CSS `.form-input` para inputs soltos no modal
- Usa variáveis de cor existentes
- Responsivo (mobile-first)

## Fluxo de Uso no Frontend

### 1. Colaborador Calcula Férias
```
1. Vai para seção "Férias"
2. Seleciona seu nome no card "Calcular Valor"
3. Ajusta dias (padrão: 30)
4. Vê resultado: valor base + adicional
5. Visualiza opções de divisão
```

### 2. Colaborador Solicita Férias
```
1. Clica "+ Solicitar"
2. Preenche datas início/fim
3. Adiciona observação (opcional)
4. Confirma solicitação
```

### 3. RH Adiciona Fracionamento
```
1. Vê solicitação pendente
2. Clica "Fraccionar"
3. Preenche até 3 períodos com datas
4. Confirma adição
5. Status atualizado para mostrar fracionamento
```

### 4. RH Aprova/Recusa
```
1. Clica "Aprovar" ou "Recusar"
2. Status muda para aprovada/recusada
3. Botão "Fraccionar" desaparece
```

## Validações no Frontend

✅ Obrigatoriedade: Colaborador e datas (ao solicitar)  
✅ Range de dias: 1-30  
✅ Avisos: Exibe regras CLT no modal de fracionamento  
✅ Backend valida: Fracionamento, soma de períodos, mínimos  

## Responsividade

- Grid 2 colunas colapsível para 1 em mobile
- Inputs responsivos no modal
- Tabela scrollável em telas pequenas
- Formatação adaptável

## Próximos Passos (Opcional)

- [ ] Cálculo automático de datas (fim baseado em dias)
- [ ] Visualização em calendário dos períodos
- [ ] Exportação de PDF com detalhes
- [ ] Notificação visual quando férias são aprovadas
- [ ] Saldo de férias do ano anterior
- [ ] Histórico de períodos usados
