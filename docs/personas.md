# Personas — PT Tax Intelligence Layer

## 1. Pesquisador / Investigador

### Perfil

- **Nome:** Dr. Miguel Santos
- **Idade:** 35-50
- **Formação:** PhD em Engenharia
- **Cargo:** Investigador principal em projeto FCT

### Contexto

- Submete despesas de investigação regularmente
- Precisa de validação rápida se despesas são elegíveis
- Não tem formação em contabilidade ou fiscalidade

### Necessidades

- Saber rapidamente se uma despesa é dedutível
- Entender a base legal sem ler legislação completa
- Confiança na decisão para auditorias futuras

### Frustrações

- Processos manuais lentos
- Respostas vagas de serviços financeiros
- Incerteza sobre conformidade fiscal

### Como usa o sistema

```
Input: { operation_type: "expense", description: "alojamento em conferência", 
         amount: 150, context: { project_type: "FCT" } }
Output: decisão clara + base legal
```

---

## 2. Director de Departamento

### Perfil

- **Nome:** Profª. Maria Oliveira
- **Idade:** 45-60
- **Formação:** Agregação em Física
- **Cargo:** Director de Departamento

### Contexto

- aprova compras e despesas do departamento
- Precisa de validação antes de aprovar
- Responsável perante administração central

### Necessidades

- Decisões rápidas para não bloquear processos
- Clareza sobre riscos associados
- Backup documentado para suas decisões

### Frustrações

- Responsabilidade sem informação suficiente
- Processos que atrasam investigação
- Falta de visibilidade de conformidade

### Como usa o sistema

```
Input: { operation_type: "invoice", description: "equipamento laboratório",
         amount: 5000, context: { project_type: "internal" } }
Output: decisão + riscos + documentação para arquivo
```

---

## 3. Técnico de Contabilidade

### Perfil

- **Nome:** Ricardo Ferreira
- **Idade:** 28-40
- **Formação:** Licenciado em Contabilidade
- **Cargo:** Técnico de Contabilidade - Projetos

### Contexto

- Processa faturas e despesas diariamente
- Conhece regras fiscais mas precisa de validação
- Precisa de documentação para auditorias

### Necessidades

- Validação rápida de dedutibilidade IVA
- Artigos legais específicos para documentação
- Consistente entre operações similares

### Frustrações

- Interpretações variáveis
- Tempo a procurar legislação
- Responsabilidade por decisões duvidosas

### Como usa o sistema

```
Input: { operation_type: "invoice", description: "serviço consultoria",
         amount: 2500, context: { project_type: "Horizon", activity_type: "taxable" } }
Output: decisão com artigos específicos + riscos
```

---

## 4. Auditor Interno

### Perfil

- **Nome:** Dr. Paulo Costa
- **Idade:** 40-55
- **Formação:** Auditor Chartered
- **Cargo:** Auditor Interno

### Contexto

- Revê decisões fiscais periodicamente
- Precisa de trail completo de decisões
- Verifica conformidade com legislação

### Necessidades

- Histórico de todas as decisões
- Base legal documentada
- Capacidade de reproduzir decisões

### Frustrações

- Falta de audit trail
- Decisões sem justificação
- Dificuldade em verificar fontes

### Como usa o sistema

```
Input: buscar decisões por período + projeto
Output: lista decisões + filtros + exportação
```

---

## 5. Administrador de Sistemas (TI)

### Perfil

- **Nome:** Engª. Ana Rodrigues
- **Idade:** 30-45
- **Formação:** Engenharia Informática
- **Cargo:** Administradora de Sistemas

### Contexto

- Mantém infraestrutura do sistema
- Integra com outros sistemas da universidade
- Monitoriza performance e disponibilidade

### Necessidades

- Logs claros para debug
- Métricas de utilização
- Fácil manutenção e updates

### Frustrações

- Sistema que não dá visibilidade
- Dependências externas que falham silenciosamente
- Atualizações que quebram funcionalidades

### Como usa o sistema

```
Dashboard de monitoring: uptime, latência, erros, utilização
Logs: pesquisa por correlation ID
Alertas: configuração de thresholds
```

---

## 6. Director Financeiro

### Perfil

- **Nome:** Dr. José Manuel
- **Idade:** 50-65
- **Formação:** Gestão / Contabilidade
- **Cargo:** Director de Serviços Financeiros

### Contexto

- Responsável por toda a conformidade fiscal
- Precisa de visão agregada de riscos
- Reporta a Reitoria

### Necessidades

- Relatórios de decisões por período
- Visão de riscos agregados
- Conformidade documentada

### Frustrações

- Falta de visibilidade
- Auditorias que revelam problemas
- Decisões inconsequentes

### Como usa o sistema

```
Relatórios mensais: decisões por tipo, riscos, tendências
Alertas: decisões de alto risco
Auditoria: trail completo por período
```

---

## Resumo de Necessidades por Persona

| Persona | Decisão | Velocidade | Base Legal | Riscos | Audit Trail |
|---------|---------|------------|------------|--------|-------------|
| Pesquisador | ✓ | crítica | importante | secundário | secundário |
| Director Dept. | ✓ | crítica | importante | importante | importante |
| Técnico Contab. | ✓ | importante | crítica | importante | importante |
| Auditor | secundário | secundário | crítica | importante | crítico |
| Admin Sistemas | — | — | — | — | importante |
| Director Financeiro | secundário | secundário | importante | crítico | crítico |

---

## Priorização de Requisitos por Persona

### Alta Prioridade

- Pesquisador: resposta rápida + decisão clara
- Técnico Contabilidade: artigos legais específicos + consistência
- Director Departamento: riscos jelas + documentação

### Média Prioridade

- Auditor: busca e reprodução de decisões
- Director Financeiro: relatórios agregados

### Baixa Prioridade

- Admin Sistemas: tooling de monitoring