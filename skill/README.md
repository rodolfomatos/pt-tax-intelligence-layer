# UP Tax Intelligence Skill

Command shims for the UP Tax Intelligence Layer API.

## Installation

```bash
# Clone to your Claude Code skills directory
git clone https://github.com/rodolfomatos/up-tax-intelligence-skill.git ~/.claude/skills/up-tax-intelligence

# Or create a symlink to this repo
ln -s /path/to/pt-tax-intelligence-layer/skill ~/.claude/skills/up-tax-intelligence
```

## Requirements

- Python 3.10+
- UP Tax Intelligence API running (http://localhost:8000)
- Dependencies: `pip install -r requirements.txt`

## Configuration

Set environment variable to override API URL:

```bash
export PT_TAX_API_URL=http://your-server:8000
```

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `tax-analyze` | Analyze tax operation | `echo '{...}' \| tax-analyze` |
| `tax-validate` | Validate decision | `echo '{...}' \| tax-validate` |
| `tax-search` | Search legislation | `echo '{"q":"IVA"}' \| tax-search` |
| `tax-decisions` | List decisions | `echo '{"limit":10}' \| tax-decisions` |
| `dashboard-summary` | Dashboard stats | `dashboard-summary` |

## Usage

### Direct

```bash
# Analyze an expense
echo '{
  "operation_type": "expense",
  "description": "Office supplies for department",
  "amount": 150.00,
  "currency": "EUR",
  "entity_type": "department",
  "context": {
    "project_type": "internal",
    "activity_type": "taxable",
    "location": "PT"
  }
}' | tax-analyze

# Search legislation
echo '{"q": "IVA deduction", "code": "CIVA", "limit": 5}' | tax-search

# Get dashboard
dashboard-summary
```

### Via Claude Code

The skill will be triggered when you mention tax analysis.

## API Endpoints Used

- `POST /tax/analyze`
- `POST /tax/validate`
- `GET /tax/search`
- `GET /tax/decisions`
- `GET /dashboard/summary`

## Troubleshooting

### "API not running"

```bash
# Start the API
cd pt-tax-intelligence-layer
make docker-up
```

### Connection refused

Check `PT_TAX_API_URL` environment variable matches your API server.

## License

MIT