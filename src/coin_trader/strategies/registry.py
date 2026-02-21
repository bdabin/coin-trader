"""Strategy registry with decorator-based registration."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Type

import structlog

from coin_trader.domain.strategy import Strategy

logger = structlog.get_logger()

_REGISTRY: Dict[str, Type[Strategy]] = {}


def register_strategy(template_name: str) -> Callable[[Type[Strategy]], Type[Strategy]]:
    """Decorator to register a strategy class."""
    def decorator(cls: Type[Strategy]) -> Type[Strategy]:
        _REGISTRY[template_name] = cls
        logger.debug("strategy.registered", template=template_name, cls=cls.__name__)
        return cls
    return decorator


def get_strategy_class(template_name: str) -> Optional[Type[Strategy]]:
    """Get registered strategy class by template name."""
    return _REGISTRY.get(template_name)


def list_strategies() -> List[str]:
    """List all registered strategy template names."""
    return list(_REGISTRY.keys())


def create_strategy(template_name: str, **kwargs: Any) -> Strategy:
    """Create a strategy instance from template name."""
    cls = _REGISTRY.get(template_name)
    if cls is None:
        raise ValueError(f"Unknown strategy template: {template_name}")
    return cls(**kwargs)
