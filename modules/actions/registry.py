"""
Action Registry

Discovers and manages all action plugins organized by category.
"""

import inspect
import importlib
from pathlib import Path
from typing import Dict, List, Optional
from modules.actions.base import Action, ActionCategory
from utils.logger import get_logger

logger = get_logger('action_registry')

class ActionRegistry:
    """
    Registry for action plugins organized by category.
    Auto-discovers actions from categorized folders.
    """
    
    def __init__(self):
        self._actions: Dict[str, Action] = {}
        self._categories: Dict[ActionCategory, List[Action]] = {}
        self._discover_actions()
    
    def _discover_actions(self):
        """Auto-discover action plugins from all categories"""
        logger.info("Discovering actions...")
        
        actions_dir = Path(__file__).parent
        
        # Discover from each category folder
        categories = ['home_automation', 'productivity', 'system', 'conversation']
        
        for category in categories:
            category_dir = actions_dir / category
            
            if not category_dir.exists():
                logger.debug(f"Category folder not found: {category}")
                continue
            
            # Find all Python files (except __init__.py)
            action_files = [f for f in category_dir.glob("*.py") 
                          if f.name != '__init__.py']
            
            for action_file in action_files:
                try:
                    # Import module
                    module_path = f"modules.actions.{category}.{action_file.stem}"
                    module = importlib.import_module(module_path)
                    
                    # Find Action subclasses
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, Action) and obj != Action:
                            self._register(obj)
                            
                except Exception as e:
                    logger.error(f"Failed to load {action_file}: {e}")
        
        logger.info(f"Discovered {len(self._actions)} actions across {len(self._categories)} categories")
    
    def _register(self, action_class):
        """Register an action"""
        try:
            instance = action_class()
            
            if not instance.enabled:
                logger.debug(f"Skipping disabled: {instance.name}")
                return
            
            # Register by name
            self._actions[instance.name] = instance
            
            # Register by category
            category = instance.get_category()
            if category not in self._categories:
                self._categories[category] = []
            self._categories[category].append(instance)
            
            logger.info(
                f"Registered: {instance.name} "
                f"({category.value}, {len(instance.get_intents())} intents)"
            )
            
        except Exception as e:
            logger.error(f"Failed to register {action_class.__name__}: {e}")
    
    def find_action_for_prompt(self, prompt: str) -> Optional[Action]:
        """
        Find best matching action for a prompt.
        
        Args:
            prompt: User's input
            
        Returns:
            Matching Action or None
        """
        prompt_lower = prompt.lower()
        
        # Try exact matches first
        for action in self._actions.values():
            if action.matches(prompt_lower):
                logger.debug(f"Matched: {action.name}")
                return action
        
        logger.debug(f"No action matched: {prompt}")
        return None
    
    def get_action(self, name: str) -> Optional[Action]:
        """Get action by name"""
        return self._actions.get(name)
    
    def get_actions_by_category(self, category: ActionCategory) -> List[Action]:
        """Get all actions in a category"""
        return self._categories.get(category, [])
    
    def get_action_by_category(self, category_name: str) -> Optional[Action]:
        """
        Get first action in a category by name.
        Useful for getting web search, conversation, etc.
        """
        category_name_lower = category_name.lower()
        
        for category, actions in self._categories.items():
            if category.value.lower() == category_name_lower:
                return actions[0] if actions else None
        
        return None
    
    def list_actions(self) -> List[str]:
        """List all action names"""
        return list(self._actions.keys())
    
    def list_categories(self) -> List[ActionCategory]:
        """List all categories with actions"""
        return list(self._categories.keys())
    
    def get_all_actions(self) -> Dict[str, Action]:
        """Get all registered actions"""
        return self._actions
    
    async def execute_action(
        self,
        action_name: str,
        prompt: str,
        params: Optional[dict] = None
    ):
        """
        Execute an action by name.
        
        Args:
            action_name: Name of action
            prompt: Original prompt
            params: Optional parameters
            
        Returns:
            ActionResult
        """
        action = self.get_action(action_name)
        
        if not action:
            from modules.actions.base import ActionResult
            return ActionResult(
                success=False,
                message=f"Action not found: {action_name}"
            )
        
        # Validate
        if not await action.validate(params):
            from modules.actions.base import ActionResult
            return ActionResult(
                success=False,
                message="Validation failed"
            )
        
        # Check confirmation
        if action.requires_confirmation():
            from modules.security.confirmation import get_confirmation_manager
            confirmation_mgr = get_confirmation_manager()
            
            if confirmation_mgr.requires_confirmation(action.name):
                from modules.actions.base import ActionResult
                prompt_text = confirmation_mgr.get_confirmation_prompt(
                    action.name,
                    params
                )
                return ActionResult(
                    success=False,
                    message="Confirmation required",
                    requires_confirmation=True,
                    confirmation_prompt=prompt_text
                )
        
        # Execute
        logger.info(f"Executing: {action.name}")
        result = await action.execute(prompt, params)
        
        if result.success:
            logger.info(f"Success: {action.name}")
        else:
            logger.warning(f"Failed: {action.name} - {result.message}")
        
        return result

# Global instance
_registry = None

def get_action_registry() -> ActionRegistry:
    """Get global action registry"""
    global _registry
    if _registry is None:
        _registry = ActionRegistry()
    return _registry