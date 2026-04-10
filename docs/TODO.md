# TODO — UP Tax Intelligence Layer

## Phase 1: Core Foundation ✓

- [x] Project structure setup
- [x] Basic FastAPI application
- [x] Health check endpoint
- [x] Logging setup with audit capability
- [x] Environment configuration (.env)

## Phase 2: Data Layer ✓

- [x] ptdata MCP client integration
- [x] Legislation caching (Redis)
- [x] Legal article retrieval
- [ ] Semantic search support
- [ ] Cache invalidation strategy

## Phase 3: Reasoning Layer ✓

- [x] LLM integration (IAEDU/OpenAI/Ollama)
- [x] Strict grounding prompt
- [ ] Citation extraction
- [x] Response validation

## Phase 4: Rule Engine ✓

- [x] VAT deduction rules (CIVA)
- [x] Project-based constraints (FCT/Horizon)
- [x] Activity classification logic
- [x] Override mechanism for LLM outputs

## Phase 5: API Layer ✓

- [x] POST /tax/analyze endpoint
- [x] POST /tax/validate endpoint
- [x] GET /tax/search endpoint
- [x] GET /tax/article/{code}/{article}
- [x] Input validation
- [x] Error handling

## Phase 6: Decision Layer ✓

- [x] Decision aggregation
- [x] Confidence scoring
- [x] Risk assessment
- [x] Audit logging
- [x] Version timestamp management

## Phase 7: Integration ✓

- [x] Docker Compose setup
- [ ] Database migrations (Alembic)
- [ ] Internal system hooks
- [ ] Dashboard integration support
- [x] Deployment configuration

## Phase 8: Quality ✓

- [x] Unit tests
- [x] Integration tests
- [x] Documentation
- [ ] Performance benchmarks
- [ ] Security audit

## Priority Order

1. Data Layer (ptdata integration) ✓
2. API Layer (endpoints) ✓
3. Rule Engine (deterministic logic) ✓
4. Reasoning Layer (LLM) ✓
5. Decision Layer (aggregation) ✓
6. Integration & Deployment ✓

## Notes

- All decisions must be auditable
- Minimum 2 legal sources for high confidence
- Return "uncertain" when no clear legal basis
- Include disclaimer in all responses
