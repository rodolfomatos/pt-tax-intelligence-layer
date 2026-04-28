"""
Hooks para lifecycle de decisões.

Inspirado em Claude-Mem:
- PostToolUse → auto-save decisão
- Stop → emergency save
- SessionEnd → final save
"""

import logging
from typing import Callable
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# Hook registry
_hooks = {
    "on_decision_created": [],
    "on_decision_validated": [],
    "on_search_executed": [],
    "on_error": [],
}


def register_hook(hook_type: str, func: Callable):
    """Registar um hook."""
    if hook_type not in _hooks:
        _hooks[hook_type] = []
    _hooks[hook_type].append(func)
    logger.info(f"Registered hook: {hook_type} -> {func.__name__}")


def trigger_hook(hook_type: str, **kwargs):
    """Disparar hooks registados."""
    if hook_type not in _hooks:
        return
    
    for func in _hooks[hook_type]:
        try:
            func(**kwargs)
        except Exception as e:
            logger.warning(f"Hook {func.__name__} failed: {e}")


class DecisionHooks:
    """Classe para gerir hooks de decisões."""
    
    @staticmethod
    def on_decision(decision_id: str, input_data: dict, output_data: dict):
        """Disparado quando uma decisão é criada."""
        trigger_hook(
            "on_decision_created",
            decision_id=decision_id,
            input_data=input_data,
            output_data=output_data,
            timestamp=datetime.utcnow().isoformat(),
        )
        logger.info(f"Decision hook triggered: {decision_id}")
    
    @staticmethod
    def on_validation(validation_id: str, is_valid: bool, notes: list):
        """Disparado quando uma validação ocorre."""
        trigger_hook(
            "on_decision_validated",
            validation_id=validation_id,
            is_valid=is_valid,
            notes=notes,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    @staticmethod
    def on_search(query: str, results_count: int):
        """Disparado quando uma pesquisa é executada."""
        trigger_hook(
            "on_search_executed",
            query=query,
            results_count=results_count,
            timestamp=datetime.utcnow().isoformat(),
        )
    
    @staticmethod
    def on_error(error_type: str, error_message: str, context: dict):
        """Disparado quando ocorre um erro."""
        trigger_hook(
            "on_error",
            error_type=error_type,
            error_message=error_message,
            context=context,
            timestamp=datetime.utcnow().isoformat(),
        )


def auto_save_hook(func):
    """Decorator para auto-save de decisões."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        # Trigger decision created hook
        if hasattr(result, "decision"):
            DecisionHooks.on_decision(
                decision_id=str(id(result)),
                input_data=kwargs.get("input", {}),
                output_data=result.model_dump() if hasattr(result, "model_dump") else {},
            )
        
        return result
    return wrapper


def create_file_write_hook(file_path: str):
    """Cria um hook que escreve para um ficheiro."""
    def hook(decision_id: str, input_data: dict, output_data: dict, timestamp: str, **kwargs):
        try:
            import json
            with open(file_path, "a") as f:
                f.write(json.dumps({
                    "decision_id": decision_id,
                    "timestamp": timestamp,
                    "input": input_data,
                    "output": output_data,
                }) + "\n")
        except Exception as e:
            logger.error(f"File write hook failed: {e}")
    
    return hook


def create_memory_save_hook(memory_layers):
    """Cria um hook que salva para memória semântica."""
    def hook(decision_id: str, input_data: dict, output_data: dict, **kwargs):
        try:
            from app.data.memory.layers import get_memory_layers
            
            memory = get_memory_layers()
            memory.save_to_memory(
                decision_id=decision_id,
                description=input_data.get("description", ""),
                decision=output_data.get("decision", ""),
                explanation=output_data.get("explanation", ""),
                legal_basis=output_data.get("legal_basis", []),
                metadata={
                    "operation_type": input_data.get("operation_type", ""),
                    "entity_type": input_data.get("entity_type", ""),
                    "project_type": input_data.get("context", {}).get("project_type", ""),
                }
            )
        except Exception as e:
            logger.error(f"Memory save hook failed: {e}")
    
    return hook


# Register default hooks
def init_default_hooks():
    """Inicializa hooks padrão."""
    # Register semantic memory hook
    from app.data.memory.layers import get_memory_layers
    memory = get_memory_layers()
    
    register_hook(
        "on_decision_created",
        create_memory_save_hook(memory)
    )
    logger.info("Default hooks initialized")