# PT Tax Intelligence Layer

## 0. TL;DR (para alinhar rapidamente)

Um serviço backend, invisível ao utilizador final, que transforma legislação fiscal portuguesa em **decisões estruturadas, auditáveis e integráveis** nos fluxos administrativos da universidade.

Não é um chatbot. Não é uma ferramenta de consulta. É um **motor de decisão com base legal**.

---

# 1. Explicação tipo Feynman (dupla camada)

## 1.1 Como explicar a uma criança

Imagina que tens um robô que ajuda a decidir se uma compra é "permitida" ou "não permitida".

Mas esse robô não pode inventar regras.
Ele tem de ir buscar sempre a regra ao livro oficial (a lei).

Então:
- Tu dizes: "comprei um computador"
- O robô vai ao livro
- Lê as regras
- E responde:
  - "Sim, podes usar isto" (e diz qual a regra)
  - ou "Não tenho a certeza" (se não encontrar uma regra clara)

👉 O mais importante: o robô **nunca adivinha**.

---

## 1.2 Como explicar a um especialista

Sistema de decisão fiscal assistido com:
- grounding jurídico obrigatório
- outputs estruturados (machine-readable)
- separação entre inferência probabilística (LLM) e decisão determinística (rule engine)
- auditabilidade completa (inputs, contexto, base legal)

Objetivo:
> reduzir entropia decisional em contextos administrativos regulados

---

# 2. Problema real (sem romantização)

## 2.1 Situação atual

Na universidade:
- decisões fiscais são feitas manualmente
- dependem de pessoas específicas
- documentação legal está dispersa
- interpretações variam

Consequências:
- inconsistência
- retrabalho
- risco em auditorias
- tempo perdido

---

## 2.2 O problema profundo (não óbvio)

Não é falta de informação.

É:
> incapacidade de transformar legislação em decisões operacionais repetíveis

---

# 3. O que este sistema É (e NÃO É)

## 3.1 É

- Motor de decisão
- API-first
- Sistema de validação
- Infraestrutura transversal

## 3.2 NÃO É

- Chatbot
- Interface principal
- Substituto de contabilista
- Fonte autónoma de verdade

---

# 4. Princípios fundamentais

1. **Sem base legal → sem decisão**
2. **Incerteza explícita > resposta errada**
3. **LLM não decide, auxilia**
4. **Regras determinísticas têm prioridade**
5. **Tudo é auditável**

---

# 5. Arquitetura conceptual

## 5.1 Camadas

### Data Layer
- API legislação (ptdata)
- Cache local

### Reasoning Layer
- LLM com prompting restritivo
- Extração e estruturação

### Rule Engine
- lógica determinística
- override do LLM

### Decision Layer
- agregação final
- scoring
- output estruturado

### Integration Layer
- APIs internas
- hooks em sistemas

---

# 6. Modelo de decisão

Output esperado:

- decisão
- confiança
- base legal
- riscos
- suposições
- perguntas adicionais


## 6.1 Estados possíveis

- deductible
- non_deductible
- partially_deductible
- uncertain

---

# 7. Casos de uso

## 7.1 Investigação
- elegibilidade de despesas

## 7.2 Financeiro
- validação de faturas

## 7.3 Ativos
- classificação fiscal

## 7.4 Auditoria
- explicabilidade

---

# 8. Integração

Este sistema não vive sozinho.

Integra com:
- sistemas internos
- dashboards
- APIs existentes

---

# 9. Riscos (análise hostil)

## 9.1 Ambiguidade legal
Lei não é determinística.

➡️ Mitigação:
- estado "uncertain"

---

## 9.2 Overtrust
Utilizadores podem confiar demasiado.

➡️ Mitigação:
- disclaimers

---

## 9.3 Dependência externa
API pode falhar.

➡️ Mitigação:
- cache

---

## 9.4 Alucinação do LLM

➡️ Mitigação:
- grounding obrigatório

---

# 10. Auditoria ao próprio documento (meta-análise)

## 10.1 Falhas identificadas

### Falha 1 — Simplificação excessiva
O modelo ignora:
- regimes especiais
- exceções contextuais

### Falha 2 — Rule Engine pouco definido
Não especifica regras concretas.

### Falha 3 — Falta de versionamento legal
Lei muda.

### Falha 4 — Falta de contexto institucional
UPorto ≠ empresa genérica

### Falha 5 — Não cobre multi-jurisdição
Projetos europeus introduzem complexidade

---

## 10.2 Correções propostas

### Correção 1 — Introduzir contexto forte
Adicionar:
- tipo de projeto
- regime fiscal

### Correção 2 — Expandir Rule Engine
Criar biblioteca de regras:
- IVA
- amortizações
- deduções

### Correção 3 — Versionamento
Guardar:
- timestamp
- versão legal

### Correção 4 — Logging
Registar:
- input
- decisão
- artigos

### Correção 5 — Multi-layer validation
- LLM + regras + fallback

---

# 11. Evolução futura

- integração com ERP
- automação completa de compliance
- recomendações proativas

---

# 12. Conclusão

Isto não é uma funcionalidade.

É:

> uma camada de infraestrutura cognitiva para decisões regulamentares

Se falhar, falha silenciosamente.
Se for bem feito, torna-se invisível — mas indispensável.

