"""
Main Orchestrator - WITH MEMORY INTEGRATION

Coordinates all modules to handle user interactions.
NOW INCLUDES: Intelligent memory storage and retrieval!
"""

import sys
import time
from typing import Optional
from core.module_loader import get_module_loader
from modules.wake_word.base import WakeWordDetector
from modules.stt.base import STTProvider
from modules.tts.base import TTSProvider
from modules.intent.base import IntentDetector, IntentType
from modules.actions.registry import ActionRegistry
from utils.logger import get_logger
import asyncio

# NEW: Memory system
from modules.memory import get_memory_manager, MemoryManager

logger = get_logger('orchestrator')

class AssistantOrchestrator:
    """
    Main coordinator for the voice assistant.
    
    Manages the complete flow:
    1. Wake word detection
    2. Speech recording & transcription
    3. **[NEW] Retrieve relevant memory context**
    4. Intent detection
    5. Action execution or AI response (with context)
    6. **[NEW] Store conversation in memory**
    7. Text-to-speech response
    """
    
    def __init__(self):
        self.loader = get_module_loader()
        
        # Load modules
        self.wake_word: Optional[WakeWordDetector] = None
        self.stt: Optional[STTProvider] = None
        self.tts: Optional[TTSProvider] = None
        self.intent: Optional[IntentDetector] = None
        self.actions: Optional[ActionRegistry] = None
        
        # NEW: Memory system
        self.memory: Optional[MemoryManager] = None
        
        # Music player reference (for auto-pause)
        self.music_player = None
        
        self._initialize_modules()
    
    def _initialize_modules(self):
        """Load all modules based on configuration"""
        try:
            logger.info("Initializing modules...")
            
            # Load wake word detector
            try:
                self.wake_word = self.loader.load_module('wake_word')
                logger.info(f"Wake word: {self.wake_word.__class__.__name__}")
                print(f"[OK] Wake word: {self.wake_word.__class__.__name__}")
                sys.stdout.flush()
            except Exception as e:
                logger.warning(f"Wake word module failed: {e}")
                print(f"[WARN] Wake word detection disabled (error: {e})")
                sys.stdout.flush()
                self.wake_word = None
            
            # Load STT
            try:
                self.stt = self.loader.load_module('stt')
                logger.info(f"STT: {self.stt.__class__.__name__}")
                print(f"[OK] STT: {self.stt.__class__.__name__}")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"STT module failed: {e}")
                print(f"[FAIL] STT module failed: {e}")
                sys.stdout.flush()
                raise
            
            # Load TTS
            try:
                self.tts = self.loader.load_module('tts')
                logger.info(f"TTS: {self.tts.__class__.__name__}")
                print(f"[OK] TTS: {self.tts.__class__.__name__}")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"TTS module failed: {e}")
                print(f"[FAIL] TTS module failed: {e}")
                sys.stdout.flush()
                raise
            
            # Load intent detector
            try:
                self.intent = self.loader.load_module('intent')
                logger.info(f"Intent: {self.intent.__class__.__name__}")
                print(f"[OK] Intent: {self.intent.__class__.__name__}")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"Intent module failed: {e}")
                print(f"[FAIL] Intent module failed: {e}")
                sys.stdout.flush()
                raise
            
            # Load action registry
            try:
                from modules.actions.registry import get_action_registry
                self.actions = get_action_registry()
                logger.info(f"Actions: {len(self.actions.list_actions())} loaded")
                print(f"[OK] Actions: {len(self.actions.list_actions())} loaded")
                sys.stdout.flush()
                
                # Get music player reference for auto-pause
                self._get_music_player_reference()
                
            except Exception as e:
                logger.error(f"Actions failed: {e}")
                print(f"[FAIL] Actions failed: {e}")
                sys.stdout.flush()
                raise
            
            # NEW: Load memory system
            try:
                self.memory = get_memory_manager()
                logger.info("Memory system initialized")
                print(f"[OK] Memory: Hybrid SQL + Vector storage")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"Memory system failed: {e}")
                print(f"[WARN] Memory disabled: {e}")
                sys.stdout.flush()
                self.memory = None
            
            logger.info("All modules initialized successfully!")
            print("[OK] All modules initialized!")
            sys.stdout.flush()
            
        except Exception as e:
            logger.error(f"Module initialization failed: {e}", exc_info=True)
            print(f"[FAIL] Module initialization failed: {e}")
            sys.stdout.flush()
            raise
    
    def _get_music_player_reference(self):
        """Get reference to music player for auto-pause"""
        try:
            for action in self.actions.get_all_actions().values():
                if action.name == "MusicAction" and hasattr(action, 'player'):
                    self.music_player = action.player
                    logger.info("Music player reference obtained for auto-pause")
                    break
        except Exception as e:
            logger.debug(f"Could not get music player reference: {e}")
    
    def _pause_all_audio(self):
        """Pause all audio outputs (music, TTS, etc.)"""
        paused_something = False
        
        # Pause music if playing
        if self.music_player:
            try:
                if self.music_player.auto_pause():
                    logger.info("Auto-paused music for wake word")
                    paused_something = True
            except Exception as e:
                logger.debug(f"Music pause failed: {e}")
        
        # Stop TTS if speaking
        if self.tts and hasattr(self.tts, 'is_speaking') and self.tts.is_speaking:
            try:
                self.tts.stop()
                logger.info("Stopped TTS for wake word")
                paused_something = True
            except Exception as e:
                logger.debug(f"TTS stop failed: {e}")
        
        return paused_something
    
    def _resume_all_audio(self):
        """Resume paused audio outputs"""
        # Resume music if it was auto-paused
        if self.music_player:
            try:
                if self.music_player.auto_resume():
                    logger.info("Auto-resumed music after interaction")
            except Exception as e:
                logger.debug(f"Music resume failed: {e}")
    
    async def wait_for_wake_word(self) -> bool:
        """
        Wait for wake word detection.
        
        Returns:
            True if wake word detected
        """
        if not self.wake_word:
            logger.debug("Wake word detector not available, skipping")
            print("⚠️  Wake word detection disabled, starting immediately...")
            return True
        
        try:
            logger.debug("Listening for wake word...")
            self.wake_word.start()
            detected = self.wake_word.wait_for_wake_word()
            self.wake_word.stop()
            
            # Pause all audio when wake word detected
            if detected:
                self._pause_all_audio()
            
            return detected
        except Exception as e:
            logger.error(f"Wake word error: {e}")
            print(f"⚠️  Wake word error: {e}")
            return True  # Continue anyway
    
    def listen_to_user(self) -> str:
        """
        Record and transcribe user speech.
        
        Returns:
            Transcribed text or empty string
        """
        logger.debug("Recording user speech...")
        print("[LISTEN] Recording...")
        sys.stdout.flush()
        result = self.stt.listen()
        
        if result.is_empty():
            logger.debug("No speech recognized")
            return ""
        
        logger.info(f"Heard: {result.text}")
        print(f"[HEARD] {result.text}")
        sys.stdout.flush()
        return result.text
    
    async def detect_intent(self, text: str) -> IntentType:
        """
        Detect user intent from text.
        
        Args:
            text: User's transcribed speech
            
        Returns:
            IntentType (AI, Web, or Action)
        """
        logger.debug(f"Detecting intent for: {text}")
        print(f"[INTENT] Classifying...")
        sys.stdout.flush()
        result = await self.intent.detect(text)
        
        logger.info(
            f"Intent: {result.intent_type.value} "
            f"(confidence: {result.confidence:.2f})"
        )
        print(f"[INTENT] {result.intent_type.value} (conf: {result.confidence:.2f})")
        sys.stdout.flush()
        
        return result.intent_type
    
    async def handle_action(self, text: str) -> str:
        """
        Handle action execution.
        
        Args:
            text: User's command
            
        Returns:
            Response message
        """
        logger.debug(f"Executing action for: {text}")
        print(f"[ACTION] Finding action...")
        sys.stdout.flush()
        
        # Find matching action
        action = self.actions.find_action_for_prompt(text)
        
        if not action:
            logger.warning("No matching action found")
            print("[WARN] No matching action")
            return "I'm not sure how to do that."
        
        # Execute
        print(f"[ACTION] Executing: {action.name}")
        sys.stdout.flush()
        result = await action.execute(text)
        
        if result.success:
            logger.info(f"Action completed: {action.name}")
            print(f"[OK] Action completed")
        else:
            logger.warning(f"Action failed: {result.message}")
            print(f"[FAIL] {result.message}")
        
        sys.stdout.flush()
        return result.message
    
    async def handle_web_search(self, text: str) -> str:
        """
        Handle web search request.
        
        Args:
            text: User's query
            
        Returns:
            Search results or answer
        """
        logger.debug(f"Web search for: {text}")
        print(f"[WEB] Searching for: {text}")
        sys.stdout.flush()
        
        # Find web search action
        web_action = None
        for action in self.actions.get_all_actions().values():
            if action.name == "WebSearchAction":
                web_action = action
                break
        
        if web_action:
            result = await web_action.execute(text)
            return result.message
        
        logger.warning("Web search action not found")
        print("[WARN] Web search action not available")
        return "Web search not available yet."
    
    async def handle_conversation(self, text: str, context: str = "") -> str:
        """
        Handle general conversation.
        
        Args:
            text: User's message
            context: Memory context to inject (NEW!)
            
        Returns:
            AI response
        """
        logger.debug(f"Conversation: {text}")
        print(f"[AI] Processing: {text}")
        sys.stdout.flush()
        
        # Find conversation action
        conv_action = None
        for action in self.actions.get_all_actions().values():
            if action.name == "AIChatAction":
                conv_action = action
                break
        
        if conv_action:
            # NEW: Pass context via params
            params = {}
            if context:
                params['memory_context'] = context
                logger.info(f"Injecting memory context ({len(context)} chars)")
                print(f"[MEMORY] Using {len(context)} chars of context")
            
            result = await conv_action.execute(text, params=params)
            return result.message
        
        logger.warning("AI chat action not found")
        return "I'm not sure how to respond to that."
    
    def speak(self, text: str):
        """
        Speak text to user.
        
        Args:
            text: Text to speak
        """
        logger.debug(f"Speaking: {text[:50]}...")
        print(f"[SPEAK] {text[:80]}...")
        sys.stdout.flush()
        
        # Use streaming if enabled
        config = self.tts.config
        if config.streaming_enabled:
            self.tts.stream_speak(text)
        else:
            self.tts.speak(text)
    
    async def process_user_input(self, user_input: str) -> str:
        """
        Process user input through the full pipeline WITH MEMORY.
        
        Args:
            user_input: User's transcribed speech
            
        Returns:
            Response message
        """
        start_time = time.time()
        
        try:
            # NEW: Step 1 - Retrieve memory context BEFORE processing
            context = ""
            if self.memory:
                try:
                    print(f"[MEMORY] Retrieving context...")
                    context_results = await self.memory.retrieve_context(
                        query=user_input,
                        max_results=5,
                        include_recent=True
                    )
                    
                    if context_results:
                        context = self.memory.format_context_for_prompt(
                            context_results,
                            max_length=500
                        )
                        logger.info(f"Retrieved {len(context_results)} memory items")
                        print(f"[MEMORY] Found {len(context_results)} relevant memories")
                except Exception as e:
                    logger.error(f"Memory retrieval error: {e}")
                    print(f"[WARN] Memory retrieval failed: {e}")
            
            # Step 2 - Detect intent
            intent_type = await self.detect_intent(user_input)
            
            # Step 3 - Route based on intent (with context)
            if intent_type == IntentType.ACTION:
                response = await self.handle_action(user_input)
            elif intent_type == IntentType.WEB:
                response = await self.handle_web_search(user_input)
            else:  # AI/Conversation
                response = await self.handle_conversation(user_input, context)
            
            # Calculate processing time
            duration_ms = (time.time() - start_time) * 1000
            
            # NEW: Step 4 - Store conversation in memory AFTER getting response
            if self.memory:
                try:
                    print(f"[MEMORY] Storing conversation...")
                    classification = await self.memory.process_conversation(
                        user_input=user_input,
                        assistant_response=response,
                        intent_type=intent_type.value,
                        duration_ms=duration_ms,
                        prompt_tokens=0,  # TODO: Track from AI calls
                        completion_tokens=0
                    )
                    
                    logger.info(
                        f"Memory: {classification.category.value} "
                        f"(importance: {classification.importance_score:.2f})"
                    )
                    print(f"[MEMORY] Stored as {classification.category.value}")
                    
                except Exception as e:
                    logger.error(f"Memory storage error: {e}")
                    print(f"[WARN] Memory storage failed: {e}")
            
            # Log the conversation (legacy logging)
            from utils.logger import log_conversation
            log_conversation(user_input, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            error_response = "Sorry, I encountered an error processing your request."
            
            # Log error conversation too
            from utils.logger import log_conversation
            log_conversation(user_input, error_response)
            
            return error_response
        
    async def run_loop(self):
        """
        Main assistant loop (voice input, voice output).
        
        Flow:
        1. Wait for wake word
        2. Listen to user
        3. **[NEW] Retrieve memory context**
        4. Process input
        5. **[NEW] Store conversation**
        6. Speak response
        7. Resume audio
        8. Repeat
        """
        logger.info("Starting assistant loop...")
        print("[START] Assistant loop starting...")
        sys.stdout.flush()
        
        # NEW: Display memory stats at startup
        if self.memory:
            stats = self.memory.get_stats()
            print(f"[MEMORY] Loaded: {stats['sql']['total_facts']} facts, "
                  f"{stats['sql']['total_conversations']} conversations")
        
        while True:
            try:
                # Wait for wake word (pauses audio automatically)
                if not await self.wait_for_wake_word():
                    continue
                
                # Acknowledge
                self.speak("Yes?")
                
                # Listen
                user_input = self.listen_to_user()
                if not user_input:
                    # Resume audio if no input
                    self._resume_all_audio()
                    continue
                
                # Process (includes memory retrieval and storage)
                response = await self.process_user_input(user_input)
                
                # Respond
                logger.info(f"Response: {response}")
                print(f"[RESPONSE] {response[:80]}...")
                sys.stdout.flush()
                self.speak(response)
                
                # Resume paused audio after response
                self._resume_all_audio()
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                print(f"[ERROR] {e}")
                sys.stdout.flush()
                self.speak("Sorry, something went wrong.")
                self._resume_all_audio()
                continue
    
    async def run_text_loop(self):
        """Interactive console mode (text input, text output)"""
        print("Text mode. Type 'exit' to quit.")
        
        # NEW: Show memory stats
        if self.memory:
            stats = self.memory.get_stats()
            print(f"Memory: {stats['sql']['total_facts']} facts loaded\n")
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def get_input():
            try:
                return input("> ")
            except EOFError:
                return None
        
        with ThreadPoolExecutor() as executor:
            while True:
                try:
                    # Get input asynchronously
                    user_input = await asyncio.get_event_loop().run_in_executor(executor, get_input)
                    
                    if user_input is None or user_input.lower() == 'exit':
                        break
                    
                    if not user_input.strip():
                        continue
                    
                    # NEW: Special memory commands
                    if user_input.lower().startswith("memory:"):
                        await self._handle_memory_command(user_input[7:].strip())
                        continue
                        
                    # Process with memory
                    response = await self.process_user_input(user_input)
                    print(f"\nAssistant: {response}\n")
                    
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    break
                except Exception as e:
                    print(f"\nError: {e}\n")
    
    async def _handle_memory_command(self, command: str):
        """Handle special memory commands"""
        if not self.memory:
            print("Memory system not available")
            return
        
        command_lower = command.lower()
        
        if command_lower in ["stats", "status"]:
            stats = self.memory.get_stats()
            print(f"\n📊 Memory Stats:")
            print(f"  Conversations: {stats['sql']['total_conversations']}")
            print(f"  Facts: {stats['sql']['total_facts']}")
            print(f"  Tokens: {stats['sql']['total_tokens']:,}")
            print(f"  Cost: ${stats['sql']['estimated_cost_usd']:.4f}")
            if 'vector' in stats:
                print(f"  Embeddings: {stats['vector']['total_embeddings']}")
        
        elif command_lower.startswith("search "):
            query = command[7:].strip()
            results = await self.memory.retrieve_context(query, max_results=5)
            print(f"\n🔍 Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. [{result.relevance_score:.2f}] {result.content[:100]}...")
        
        elif command_lower == "facts":
            facts = self.memory.get_user_facts(limit=20)
            print(f"\n📚 User Facts ({len(facts)}):")
            for fact in facts:
                print(f"  • [{fact.category.value if fact.category else 'unknown'}] {fact.content}")
        
        else:
            print("Memory commands: stats, search <query>, facts")
    
    async def run_voice_to_text_loop(self):
        """Voice input, text output mode"""
        logger.info("Starting voice-to-text loop...")
        print("[START] Voice-to-text mode...")
        sys.stdout.flush()
        
        while True:
            try:
                # Wait for wake word (pauses audio)
                if not await self.wait_for_wake_word():
                    continue
                
                # Acknowledge (text only)
                print("\n[ASSISTANT] Listening...")
                sys.stdout.flush()
                
                # Listen
                user_input = self.listen_to_user()
                if not user_input:
                    self._resume_all_audio()
                    continue
                
                # Process (with memory)
                response = await self.process_user_input(user_input)
                
                # Respond with text only (no TTS)
                logger.info(f"Response: {response}")
                print(f"\n[ASSISTANT] {response}\n")
                sys.stdout.flush()
                
                # Resume audio
                self._resume_all_audio()
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in voice-to-text loop: {e}", exc_info=True)
                print(f"[ERROR] {e}")
                sys.stdout.flush()
                self._resume_all_audio()
                continue
    
    async def run_text_to_voice_loop(self):
        """Text input, voice output mode"""
        print("Text-to-voice mode. Type 'exit' to quit.\n")
        
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def get_input():
            try:
                return input("> ")
            except EOFError:
                return None
        
        with ThreadPoolExecutor() as executor:
            while True:
                try:
                    # Get input asynchronously
                    user_input = await asyncio.get_event_loop().run_in_executor(executor, get_input)
                    
                    if user_input is None or user_input.lower() == 'exit':
                        break
                    
                    if not user_input.strip():
                        continue
                    
                    # Pause any playing audio
                    self._pause_all_audio()
                    
                    # Process (with memory)
                    response = await self.process_user_input(user_input)
                    
                    # Speak response
                    logger.info(f"Response: {response}")
                    self.speak(response)
                    
                    # Resume audio
                    self._resume_all_audio()
                    
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    break
                except Exception as e:
                    print(f"\nError: {e}\n")
                    self._resume_all_audio()
    
    def get_status(self) -> dict:
        """Get status of all modules"""
        status = {
            'wake_word': self.wake_word is not None,
            'stt': self.stt is not None,
            'tts': self.tts is not None,
            'intent': self.intent is not None,
            'actions': len(self.actions.list_actions()) if self.actions else 0,
            'memory': self.memory is not None  # NEW
        }
        
        # NEW: Add memory stats if available
        if self.memory:
            memory_stats = self.memory.get_stats()
            status['memory_stats'] = memory_stats
        
        return status
    
    async def run_headless(self):
        """Headless mode for automation/API"""
        # Initialize only required modules (no STT/TTS)
        logger.info("Headless mode - minimal initialization")
        print("[INFO] Headless mode ready for API/automation")
        
        # Keep running for API access
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Headless mode stopped")