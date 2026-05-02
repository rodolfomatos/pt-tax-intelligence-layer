#!/usr/bin/env python3
"""
Documentation generator for PT Tax Intelligence Layer.

Extracts endpoints, models, and updates documentation from code.
Run with: python scripts/generate_docs.py
"""

import re
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
APP_DIR = ROOT / "app"
API_DIR = APP_DIR
MODELS_DIR = APP_DIR / "models"
SERVICES_DIR = APP_DIR / "services"


def extract_endpoints() -> list[dict]:
    """Extract endpoint definitions from main.py."""
    endpoints = []
    
    main_file = API_DIR / "main.py"
    if not main_file.exists():
        return endpoints
    
    content = main_file.read_text()
    
    # Find @app decorators
    for match in re.finditer(r'@(app\.(post|get|put|delete))\(["\']([^"\']+)["\']', content):
        method = match.group(1)
        path = match.group(3)
        endpoints.append({
            "method": method.upper(),
            "path": f"/{path}",
            "file": "app/main.py"
        })
    
    return endpoints


def extract_models() -> list[dict]:
    """Extract Pydantic model definitions."""
    models = []
    
    if not MODELS_DIR.exists():
        return models
    
    for py_file in MODELS_DIR.rglob("*.py"):
        content = py_file.read_text()
        
        # Find class definitions extending BaseModel
        for match in re.finditer(r'class (\w+)\(.*?BaseModel\):', content):
            model_name = match.group(1)
            models.append({
                "name": model_name,
                "file": str(py_file.relative_to(ROOT))
            })
    
    return models


def extract_rules() -> list[dict]:
    """Extract rule engine definitions."""
    rules = []
    
    rules_dir = SERVICES_DIR / "rules"
    if not rules_dir.exists():
        return rules
    
    for py_file in rules_dir.rglob("*.py"):
        content = py_file.read_text()
        
        # Find rule functions
        for match in re.finditer(r'def (check_\w+|validate_\w+|apply_\w+|_check_\w+)', content):
            rule_name = match.group(1)
            rules.append({
                "name": rule_name,
                "file": str(py_file.relative_to(ROOT))
            })
    
    return rules


def update_api_spec():
    """Update API specification from code."""
    endpoints = extract_endpoints()
    models = extract_models()
    
    spec_path = DOCS / "api-spec.md"
    if not spec_path.exists():
        return
    
    # Check if endpoints were found
    if endpoints:
        print(f"Found {len(endpoints)} endpoints")
        for ep in endpoints:
            print(f"  - {ep['method']} /{ep['path']}")
    
    if models:
        print(f"Found {len(models)} models")
        for m in models:
            print(f"  - {m['name']}")


def update_architecture():
    """Update architecture doc with component list."""
    components = []
    
    # Check for service directories
    services = APP_DIR / "services"
    if services.exists():
        for d in services.iterdir():
            if d.is_dir():
                components.append(f"- `{d.name}/` - {d.name.replace('_', ' ').title()}")
    
    if components:
        print(f"Components: {len(components)}")


def update_todo():
    """Update TODO based on existing code."""
    todo_path = DOCS / "TODO.md"
    if not todo_path.exists():
        return
    
    content = todo_path.read_text()
    
    # Check what exists and update checkboxes
    checks = {
        "Project structure setup": APP_DIR,
        "Basic FastAPI application": APP_DIR / "main.py",
        "Health check endpoint": APP_DIR / "main.py",
    }
    
    for item, path in checks.items():
        if path.exists():
            content = re.sub(
                rf'- \[ \] {re.escape(item)}',
                f'- [x] {item}',
                content
            )
    
    todo_path.write_text(content)
    print(f"Updated {todo_path}")


def generate_readme_stats():
    """Generate quick stats for README."""
    endpoints = extract_endpoints()
    models = extract_models()
    rules = extract_rules()
    
    stats = {
        "endpoints": len(endpoints),
        "models": len(models),
        "rules": len(rules),
    }
    
    stats_file = DOCS / "stats.json"
    stats_file.write_text(json.dumps(stats, indent=2))
    print(f"Generated {stats_file}: {stats}")


def main():
    """Main documentation generation."""
    print("Generating documentation...")
    
    update_api_spec()
    update_architecture()
    update_todo()
    generate_readme_stats()
    
    print("Documentation generation complete.")


if __name__ == "__main__":
    main()
