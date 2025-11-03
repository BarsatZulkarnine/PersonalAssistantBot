"""
Action plugins for the voice assistant.
Each action is auto-discovered and registered by the ActionRegistry.
"""

from app.actions.base import Action, ActionResult, SecurityLevel, ActionError
from app.actions.registry import action_registry

__all__ = [
    'Action',
    'ActionResult', 
    'SecurityLevel',
    'ActionError',
    'action_registry'
]
