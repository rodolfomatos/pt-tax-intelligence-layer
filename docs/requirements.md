# Requisitos Funcionais — PT Tax Intelligence Layer

## 1. Visão Geral

Sistema de apoio à decisão fiscal que transforma legislação portuguesa em decisões estruturadas e auditáveis para fluxos administrativos da universidade.

## 2. Requisitos Funcionais

### 2.1 Análise Fiscal (F001)

**Descrição:** O sistema deve analisar operações e retornar decisões fiscais estruturadas.

**Entrada:**
- `operation_type`: expense | invoice | asset | contract
- `description`: descrição da operação
- `amount`: valor numérico
- `currency`: EUR (obrigatório)
- `entity_type`: university | researcher | department | project
- `context`:
  - `project_type`: FCT | Horizon | internal | other
  - `activity_type`: taxable | exempt | mixed
  - `location`: PT | EU | non-EU

**Saída:**
- `decision`: deductible | non_deductible | partially_deductible | uncertain
- `confidence`: 0.0-1.0
- `legal_basis`: lista de artigos legais
- `explanation`: explicação estruturada
- `risks`: lista de riscos identificados
- `assumptions`: suposições feitas
- `required_followup`: follow-up necessário
- `risk_level`: low | medium | high
- `legal_version_timestamp`: ISO8601

**Critérios de Aceitação:**
- [ ] Retorna decisão válida para entrada válida
- [ ] Inclui pelo menos uma referência legal ou retorna "uncertain"
- [ ] Inclui disclaimer obrigatoriamente
- [ ] Log de toda a decisão para auditabilidade

### 2.2 Validação de Decisões (F002)

**Descrição:** O sistema deve validar decisões existentes.

**Entrada:**
- Objeto de decisão completo

**Saída:**
- Decisão validada com notas
- Indicador de consistência

**Critérios de Aceitação:**
- [ ] Valida consistência interna
- [ ] Verifica presença de base legal
- [ ] Confirma formato de saída

### 2.3 Pesquisa de Legislação (F003)

**Descrição:** O sistema deve permitir pesquisa de legislação fiscal.

**Entrada:**
- Termo de pesquisa
- Filtros opcionais (código, artigo, data)

**Saída:**
- Lista de artigos matching
- Metadados relevantes

**Critérios de Aceitação:**
- [ ] Pesquisa por termo
- [ ] Filtros funcionais
- [ ] Resultados ordenados por relevância

### 2.4 Recuperação de Artigo (F004)

**Descrição:** O sistema deve recuperar artigos específicos.

**Entrada:**
- `code`: código fiscal (CIVA, CIRC, etc.)
- `article`: número do artigo

**Saída:**
- Texto completo do artigo
- Metadados (versão, data)

**Critérios de Aceitação:**
- [ ] Retorna artigo existente
- [ ] Erro claro para artigo inexistente

### 2.5 Cache de Legislação (F005)

**Descrição:** O sistema deve manter cache local de legislação.

**Funcionalidades:**
- Armazenamento de artigos consultadas
- Invalidação periódica
- Fallback quando API indisponível

**Critérios de Aceitação:**
- [ ] Cache persiste entre execuções
- [ ] Fallback funciona quando API falha
- [ ] Cache é atualizável

### 2.6 Logging de Auditoria (F006)

**Descrição:** Todas as decisões devem ser logged para auditoria.

**Dados registrados:**
- Timestamp
- Input completo
- Decisão
- Base legal
- Riscos identificados

**Critérios de Aceitação:**
- [ ] Toda decisão é loggada
- [ ] Logs são pesquisáveis
- [ ] Retenção configurável

### 2.7 Integração MCP ptdata (F007)

**Descrição:** O sistema deve integrar com ptdata MCP API.

**Funcionalidades:**
- Consulta de legislação
- Recuperação de artigos
- Pesquisa semântica

**Critérios de Aceitação:**
- [ ] Conecta com ptdata API
- [ ] Tratamento de erros robusto
- [ ] Timeout configurável

## 3. Requisitos de Interface

### 3.1 API REST

- `POST /tax/analyze` — análise principal
- `POST /tax/validate` — validação de decisões
- `GET /tax/search` — pesquisa legislação
- `GET /tax/article/{code}/{article}` — artigo específico
- `GET /health` — health check

### 3.2 Autenticação

- API key para acesso
- Rate limiting opcional

## 4. Requisitos de Dados

### 4.1 Input Validation

- Todos os campos obrigatórios validados
- Tipos de dados verificados
- Valores enum validados

### 4.2 Output Validation

- Estrutura JSON válida
- Enum values válidos
- Timestamps em formato ISO8601

## 5. Casos de Uso

### UC1: Análise de Despesa Investigativa

1. Pesquisador submete despesa
2. Sistema classifica tipo
3. Sistema busca base legal
4. Sistema aplica regras
5. Retorna decisão com confiança

### UC2: Validação de Fatura

1. Financeiro submete fatura
2. Sistema verifica dedutibilidade
3. Sistema aplica regras IVA
4. Retorna decisão com riscos

### UC3: Classificação de Ativo

1. Departamento regista ativo
2. Sistema determina amortização
3. Sistema verifica elegibilidade fiscal
4. Retorna classificação

### UC4: Revisão de Contrato

1. Legal submete contrato
2. Sistema verifica implicações fiscais
3. Sistema identifica riscos
4. Retorna análise completa