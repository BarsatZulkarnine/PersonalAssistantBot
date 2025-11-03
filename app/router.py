from typing import Optional, Dict, Any
from app.actions.registry import action_registry
from app.actions.base import ActionError
from app.utils.logger import get_logger
from app.utils.config import config

logger = get_logger('router')

async def process_prompt(prompt: str) -> str:
    """
    Main router - processes user prompts and executes appropriate actions.
    
    Args:
        prompt: User's spoken input
        
    Returns:
        Response message to speak back to user
    """
    try:
        logger.info(f"📨 Processing: {prompt}")
        
        # Find matching action
        action = action_registry.find_action_for_prompt(prompt)
        
        if not action:
            # Fallback to conversation action
            logger.info("💬 No specific action found, using conversation")
            action = action_registry.get_action("ConversationAction")
            
            if not action:
                return "I'm not sure how to help with that."
        
        # Execute action
        try:
            result = await action_registry.execute_action(
                action.name,
                prompt,
                params=None  # TODO: Add parameter extraction
            )
            
            if result.requires_confirmation:
                # TODO: Implement confirmation flow
                logger.info(f"⚠️  Action requires confirmation: {result.confirmation_prompt}")
                return f"{result.confirmation_prompt} (Confirmation not yet implemented)"
            
            logger.info(f"✅ Action result: {result.success}")
            return result.message
            
        except ActionError as e:
            logger.error(f"❌ Action error: {e.message}")
            return f"Sorry, I couldn't complete that action: {e.message}"
    
    except Exception as e:
        logger.error(f"❌ Router error: {str(e)}", exc_info=True)
        return "Sorry, something went wrong. Please try again."

async def process_prompt_with_params(
    prompt: str, 
    params: Optional[Dict[str, Any]] = None
) -> str:
    """
    Process prompt with pre-extracted parameters.
    Useful when intent classifier has already extracted params.
    """
    # TODO: Implement intent classification with parameter extraction
    return await process_prompt(prompt)