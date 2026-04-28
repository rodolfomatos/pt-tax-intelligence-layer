# TODO — PT Tax Intelligence Layer

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
- [x] Semantic search support
- [x] Cache invalidation strategy

## Phase 3: Reasoning Layer ✓

- [x] LLM integration (IAEDU/OpenAI/Ollama)
- [x] Strict grounding prompt
- [x] Citation extraction
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
- [x] GET /dashboard/summary
- [x] GET /dashboard/trends
- [x] GET /internal/benchmark
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
- [x] Database migrations (Alembic)
- [x] Internal system hooks
- [x] Dashboard integration support
- [x] Deployment configuration

## Phase 8: Quality ✓

- [x] Unit tests
- [x] Integration tests
- [x] Documentation
- [x] Performance benchmarks
- [x] Security audit

## Phase 9: Advanced Features ✅

- [x] Batch endpoint (`/tax/analyze/batch`)
- [x] Webhook activation for high-risk decisions
- [x] Historical changes tracking (`/tax/history/{id}`)
- [x] CSV/Excel export (`/tax/export`)
- [x] Refactor main.py into routers
- [x] Integration tests with real DB (Docker)
- [x] Fix singleton pattern consistency
- [x] Add type hints to functions

## Notes

- All decisions must be auditable
- Minimum 2 legal sources for high confidence
- Return "uncertain" when no clear legal basis
- Include disclaimer in all responses
