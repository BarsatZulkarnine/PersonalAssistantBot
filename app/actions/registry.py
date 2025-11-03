import inspect
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Type
from app.actions.base import Action, ActionResult, ActionError
from app.utils.logger import get_logger

logger = get_logger('action_registry')

class ActionRegistry:
    """
    Registry for all action plugins.
    Auto-discovers and manages actions.
    """
    
    _instance = None
    _actions: Dict[str, Action] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ActionRegistry, cls).__new__(cls)
            cls._instance._discover_actions()
        return cls._instance
    
    def _discover_actions(self):
        """Auto-discover action plugins"""
        logger.info("🔍 Discovering action plugins...")
        
        actions_dir = Path(__file__).parent
        action_files = [f for f in actions_dir.glob("*.py") 
                       if f.name not in ['__init__.py', 'base.py', 'registry.py']]
        
        for action_file in action_files:
            try:
                module_name = f"app.actions.{action_file.stem}"
                module = importlib.import_module(module_name)
                
                # Find Action subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Action) and obj != Action:
                        self.register(obj)
                        
            except Exception as e:
                logger.error(f"❌ Failed to load action from {action_file}: {e}")
    
    def register(self, action_class: Type[Action]):
        """Register an action plugin"""
        try:
            action_instance = action_class()
            action_name = action_instance.name
            
            if not action_instance.is_enabled():
                logger.info(f"⏭️  Skipping disabled action: {action_name}")
                return
            
            self._actions[action_name] = action_instance
            logger.info(f"✅ Registered action: {action_name} (intents: {len(action_instance.get_intents())})")
            
        except Exception as e:
            logger.error(f"❌ Failed to register action {action_class.__name__}: {e}")
    
    def get_action(self, name: str) -> Optional[Action]:
        """Get action by name"""
        return self._actions.get(name)
    
    def find_action_for_prompt(self, prompt: str) -> Optional[Action]:
        """Find best matching action for a prompt"""
        prompt_lower = prompt.lower()
        
        # Try exact intent matching first
        for action in self._actions.values():
            if action.matches_intent(prompt_lower):
                logger.debug(f"🎯 Matched action: {action.name}")
                return action
        
        logger.debug(f"❓ No action matched for: {prompt}")
        return None
    
    def get_all_actions(self) -> Dict[str, Action]:
        """Get all registered actions"""
        return self._actions
    
    def list_actions(self) -> List[str]:
        """List all action names"""
        return list(self._actions.keys())
    
    async def execute_action(
        self, 
        action_name: str, 
        prompt: str, 
        params: Optional[Dict] = None
    ) -> ActionResult:
        """Execute an action by name"""
        action = self.get_action(action_name)
        
        if not action:
            raise ActionError(f"Action not found: {action_name}")
        
        try:
            # Validate before execution
            if not await action.validate(params):
                return ActionResult(
                    success=False,
                    message=f"Validation failed for {action_name}"
                )
            
            # Check if confirmation needed
            if action.requires_confirmation():
                confirmation_prompt = await action.get_confirmation_prompt(params)
                return ActionResult(
                    success=False,
                    message="Confirmation required",
                    requires_confirmation=True,
                    confirmation_prompt=confirmation_prompt
                )
            
            # Execute action
            logger.info(f"⚡ Executing action: {action_name}")
            result = await action.execute(prompt, params)
            
            if result.success:
                logger.info(f"✅ Action completed: {action_name}")
            else:
                logger.warning(f"⚠️  Action failed: {action_name} - {result.message}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Action execution error: {action_name} - {str(e)}")
            raise ActionError(str(e), action_name)

# Singleton instance
action_registry = ActionRegistry()