# UP Tax Intelligence MCP Server

MCP (Model Context Protocol) server for Portuguese tax analysis.

## What This Is

An MCP server that exposes UP Tax Intelligence tools to AI agents via the MCP protocol. Works with:
- Claude Desktop
- Claude Code
- Cursor
- Any MCP-compatible client

## Installation

```bash
# Install via pip
pip install .

# Or from source
git clone https://github.com/rodolfomatos/up-tax-intelligence-mcp.git
cd up-tax-intelligence-mcp
pip install -e .
```

## Usage

### As stdio server

```bash
# Just run (for MCP client to connect)
python src/server.py
```

### In Claude Desktop

Add to your `claude_desktop_mcp_servers` config:

```json
{
  "up-tax-intelligence": {
    "command": "python",
    "args": ["-m", "src.server"],
    "env": {
      "UP_TAX_API_URL": "http://localhost:8000"
    },
    "workingDirectory": "/path/to/up-tax-intelligence-mcp"
  }
}
```

### In Claude Code

Add to your settings (settings.json):

```json
{
  "mcpServers": {
    "up-tax": {
      "command": "python",
      "args": ["src/server.py"],
      "env": {
        "UP_TAX_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Configuration

Environment variable:
- `UP_TAX_API_URL` - URL of the UP Tax Intelligence API (default: http://localhost:8000)

## Available Tools

| Tool | Description |
|------|-------------|
| `tax_analyze` | Analyze tax operation |
| `tax_validate` | Validate existing decision |
| `tax_search` | Search legislation |
| `tax_decisions` | List past decisions |
| `dashboard_summary` | Dashboard statistics |
| `health_check` | Check API health |

## Examples

### tax_analyze

```json
{
  "operation_type": "expense",
  "description": "Conference lodging in Lisbon",
  "amount": 150,
  "currency": "EUR",
  "entity_type": "researcher",
  "context": {
    "project_type": "FCT",
    "activity_type": "taxable",
    "location": "PT"
  }
}
```

### tax_search

```json
{
  "q": "IVA deduction project",
  "code": "CIVA",
  "limit": 5
}
```

## Requirements

- Python 3.10+
- UP Tax Intelligence API running
- MCP-compatible client

## Troubleshooting

### Connection refused

API not running:

```bash
cd up-tax-intelligence-layer
make docker-up
```

### Import errors

Install dependencies:

```bash
pip install -r requirements.txt
```

## License

MIT