import asyncio
from app.router import process_prompt
from app.utils.speech import listen_to_user, speak, wait_for_hotword
from app.utils.logger import get_logger, log_conversation
from app.utils.config import config
from app.actions.registry import action_registry

logger = get_logger('main')

async def main():
    """Main assistant loop"""
    try:
        # Initialize
        app_name = config.get('settings.app.name', 'Voice Assistant')
        version = config.get('settings.app.version', '2.0.0')
        hotword = config.get('settings.speech.hotword', 'hey pi')
        
        logger.info(f"🚀 Starting {app_name} v{version}")
        logger.info(f"📋 Loaded {len(action_registry.list_actions())} actions")
        logger.info(f"🎤 Say '{hotword}' to activate")
        
        print(f"🎤 {app_name} initialized. Say '{hotword}' to start.")
        
        # Main loop
        while True:
            try:
                # Wait for hotword
                await wait_for_hotword()
                speak("Yes?")
                
                # Listen to user
                user_input = listen_to_user()
                if not user_input:
                    logger.debug("No input received")
                    continue
                
                logger.info(f"👂 Heard: {user_input}")
                print(f"🧠 Heard: {user_input}")
                
                # Process and respond
                result = await process_prompt(user_input)
                logger.info(f"💬 Response: {result}")
                print(f"💬 Assistant: {result}")
                
                # Log conversation
                log_conversation(user_input, result)
                
                # Speak response
                speak(result)
                
            except KeyboardInterrupt:
                logger.info("⛔ Interrupted by user")
                raise
                
            except Exception as e:
                logger.error(f"❌ Error in main loop: {str(e)}", exc_info=True)
                error_msg = "Sorry, I encountered an error. Please try again."
                print(f"❌ Error: {error_msg}")
                speak(error_msg)
                # Continue loop instead of crashing
                continue
    
    except KeyboardInterrupt:
        logger.info("👋 Shutting down gracefully")
        print("\n👋 Goodbye!")
    
    except Exception as e:
        logger.critical(f"💥 Critical error: {str(e)}", exc_info=True)
        print(f"💥 Critical error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass