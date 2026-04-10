# Requisitos Não Funcionais — UP Tax Intelligence Layer

## 1. Performance

### 1.1 Tempo de Resposta

- **Análise de decisão:** < 5 segundos (p50), < 10 segundos (p95)
- **Pesquisa de legislação:** < 2 segundos (p95)
- **Recuperação de artigo:** < 1 segundo (p95)

### 1.2 Throughput

- Capacidade de 100 pedidos simultâneos
- Rate limiting: 1000 pedidos/hora por cliente

### 1.3 Escalabilidade

- Suporte a horizontal scaling
- Stateless design para fácil scale-out

## 2. Disponibilidade

### 2.1 SLA

- Uptime: 99.5% (excluindo manutenção planeada)
- Tempo de recuperação: < 30 minutos

### 2.2 Failover

- Fallback para cache quando API ptdata indisponível
- Graceful degradation: modo degradado com dados em cache

### 2.3 Manutenção

- Zero-downtime deployment (rolling updates)
- Janelas de manutenção comunicadas com antecedência

## 3. Segurança

### 3.1 Autenticação

- API Key obrigatória
- Tokens com expiração configurável

### 3.2 Autorização

- Scopes por endpoint
- Rate limiting por API key

### 3.3 Dados

- Dados sensíveis encriptados em repouso
- Logs sem informação sensível
- Conformidade com LGPD

### 3.4 Rede

- HTTPS obrigatório
- Firewall: apenas portas necessárias expostas

## 4. Manutenibilidade

### 4.1 Código

- Type hints em funções públicas
- Docstrings em APIs públicas
- Limite de 200 linhas por função

### 4.2 Testing

- Cobertura mínima: 80%
- Testes de integração para APIs críticas

### 4.3 Monitoring

- Métricas: latência, erros, utilização
- Tracing distribuído
- Logging estruturado

## 5. Confiabilidade

### 5.1 Tratamento de Erros

- Retry automático para erros transitórios
- Circuit breaker para serviços externos
- Timeouts configuráveis

### 5.2 Consistência

- Decisões determinísticas quando há regras claras
- "Uncertain" quando há ambiguidade

### 5.3 Auditabilidade

- Todos os inputs guardados
- Todas as decisões loggadas
- Timestamps em ISO8601

## 6. Compliance

### 6.1 Legal

- Disclaimer em todas as respostas
- Nunca substituir aconselhamento profissional
- Base legal obrigatória ou "uncertain"

### 6.2 Versionamento

- Versão legal Included em responses
- Histórico de mudanças de legislação

## 7. Interoperabilidade

### 7.1 Formatos

- JSON para API
- OpenAPI 3.0 para documentação

### 7.2 Integração

- Webhook support para notificações
- Fácil integração com sistemas internos

## 8. Recursos

### 8.1 Hardware

- Recomendado: 2 vCPU, 4GB RAM
- Armazenamento: 10GB para cache e logs

### 8.2 Software

- Python 3.11+
- PostgreSQL (dados + cache)
- Redis (opcional, para cache)

## 9. Observabilidade

### 9.1 Logging

- Structured logging (JSON)
- Níveis: DEBUG, INFO, WARNING, ERROR
- Correlation IDs para tracing

### 9.2 Métricas

- Latência por endpoint
- Taxa de decisões por tipo
- Cache hit rate

### 9.3 Alertas

- Error rate > 1%
- Latência > 95th percentile por 5 min
- API ptdata indisponível