# Análise: MemPalace, Claude-Mem, Graphify & GMIF

Data: 2026-04-10

---

## MemPalace (38.7k ⭐)

### Arquitetura
- **Wings** → Rooms → Halls → Closets/Drawers
- **Storage**: ChromaDB (vector) + SQLite (metadata)
- **MCP**: 19 tools
- **Benchmark**: 96.6% LongMemEval (raw mode)

### Pontos Fracos (Hostil)
1. **AAAK é marketing** — Compressão com perda: 84.2% vs raw 96.6%
2. **Estrutura exagerada** — Wings/rooms/halls overkill para maioria dos casos
3. **Auto-detecção de entidades** — Pode falhar em português
4. **Instalação longa** — 2-3 min initial setup com model download

---

## Claude-Mem (47.1k ⭐)

### Arquitetura
- **5 lifecycle hooks**: SessionStart, UserPromptSubmit, PostToolUse, Stop, SessionEnd
- **Worker service** na porta 37777
- **3-layer workflow**: search → timeline → get_observations
- **Storage**: SQLite + FTS5 + ChromaDB (hybrid)
- **MCP**: 4 tools

### Pontos Fracos (Hostil)
1. **Depende de Claude Code** — Não funciona com outros LLMs
2. **Confusão npx vs npm** — Install confusa
3. **AGPL-3.0** — Copyleft, restrições comerciais
4. **Web viewer local** — Potencial security issue

---

## Graphify (19.4k ⭐)

### Arquitetura
- **Two-pass extraction**:
  1. AST pass (tree-sitter) — deterministic, no LLM
  2. Claude pass — concepts + relationships from docs/images
- **NetworkX** para grafo + **Leiden** para clustering
- **Output**: graph.html (interactive), GRAPH_REPORT.md, graph.json

### Always-on Mechanism
- **Claude Code**: CLAUDE.md + PreToolUse hook (settings.json)
- **OpenCode**: AGENTS.md + tool.execute.before plugin
- **Outros**: AGENTS.md only

### Features Úteis
- **God nodes** — highest-degree concepts
- **Surprising connections** — ranked by composite score
- **Confidence scores** — EXTRACTED vs INFERRED edges
- **Git hooks** — auto-rebuild on commit/branch switch

### Pontos Fracos (Hostil)
1. **Tree-sitter dependency** — focado em código fonte, não em decisões
2. **Requer LLM para semantic extraction** — custos de API
3. **Visualização em HTML** — não é o nosso caso de uso

---

## GMIF (Graphical Meta-Information Framework)

### Origem
Do projeto **epistemic-memory-architecture**.

### Categorias (M1-M7)

| Código | Categoria | Descrição |
|--------|-----------|-----------|
| M1 | Primary Evidence | Multiple legal sources, high confidence |
| M2 | Contextual Condition | With assumptions needing validation |
| M3 | Partial Description | Unclassified or pending |
| M4 | Doubtful Testimony | Contradictory legal sources |
| M5 | Interpretation | Clear legal basis, no contestation |
| M6 | Derived Evidence | Derived from alignment |
| M7 | Synthesis | Final aggregated decision |

### Aplicação no nosso caso

| GMIF | Decisão Fiscal | Critério |
|------|-----------------|-----------|
| M1 | deductible (alta confiança) | ≥2 fontes legais, sem riscos |
| M2 | partially_deductible | Com suposições |
| M3 | uncertain | Não classificado |
| M4 | conflicting sources | Contradições detetadas |
| M5 | non_deductible | Base legal clara |
| M7 | decision final | Decisão agregada |

---

## Implementação Completa ✅

### Fase 1: Infraestrutura ✅
- [x] ChromaDB para semantic search
- [x] SQLite para audit logs
- [x] 4-layer progressive disclosure (L0-L3)
- [x] Auto-save hooks após decisões

### Fase 2: Knowledge Graph com GMIF ✅
- [x] `app/data/memory/graph/gmif.py` — GMIF classifier
- [x] `app/data/memory/graph/models.py` — GraphNode, GraphEdge, Contradiction
- [x] `app/data/memory/graph/builder.py` — Graph builder
- [x] `app/data/memory/graph/query.py` — Query API
- [x] Endpoints para graph queries

### Endpoints do Knowledge Graph

| Endpoint | Descrição |
|----------|-----------|
| `GET /tax/graph/stats` | Estatísticas do grafo |
| `GET /tax/graph/gmif-summary` | Resumo GMIF |
| `GET /tax/graph/decisions-by-gmif/{gmif_type}` | Decisões por tipo |
| `GET /tax/graph/contradictions` | Contradições detetadas |
| `GET /tax/graph/timeline/{entity}` | Timeline cronológica |

---

## Resumo: O que foi implementado

| Componente | Descrição |
|-----------|-----------|
| **Semantic Memory** | ChromaDB + progressive disclosure (L0-L3) |
| **Decision Hooks** | Auto-save após cada decisão |
| **Knowledge Graph** | Nodes (Decision, LegalBasis, Entity, Rule) + Edges |
| **GMIF Classification** | M1-M7 para decisões fiscais |
| **Graph Queries** | timeline, find_similar, find_contradictions |

---

## Próximas Possíveis Enhancements

- MCP tools para queries externas
- Visualização do grafo (opcional)
- Contradiction detection mais sophisticated
- Git hooks para updates (se aplicável)