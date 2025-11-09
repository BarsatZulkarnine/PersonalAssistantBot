"""
Main Orchestrator - REFACTORED WITH SERVICE + WEB SEARCH FIX

Coordinates modules but business logic moved to ConversationService.
Now acts as "glue code" between I/O and business logic.

FIXED: Web searches now have memory context and are stored in sessions.
"""
from pathlib import Path
import sys
import time
from typing import Optional
from core.module_loader import get_module_loader
from modules.wake_word.base import WakeWordDetector
from modules.stt.base import STTProvider
from modules.tts.base import TTSProvider
from modules.intent.base import IntentDetector
from modules.actions.registry import ActionRegistry
from utils.logger import get_logger
import asyncio

# NEW: Import the service
from core.services.conversation_service import ConversationService

# Memory system
from modules.memory import get_memory_manager, MemoryManager

# RAG system
from modules.rag import get_retriever, HybridRetriever

logger = get_logger('orchestrator')

class AssistantOrchestrator:
    """
    Main coordinator for the voice assistant.
    
    SIMPLIFIED (Refactored):
    - I/O handling (wake word, STT, TTS)
    - Service initialization
    - Mode routing (voice, text, headless)
    
    Business logic moved to ConversationService.
    
    FIXED: All interactions (web, action, AI) are now stored in sessions.
    """
    
    def __init__(self):
        self.loader = get_module_loader()
        
        # Load modules (I/O components)
        self.wake_word: Optional[WakeWordDetector] = None
        self.stt: Optional[STTProvider] = None
        self.tts: Optional[TTSProvider] = None
        self.intent: Optional[IntentDetector] = None
        self.actions: Optional[ActionRegistry] = None
        
        # Memory system
        self.memory: Optional[MemoryManager] = None
        
        # RAG system
        self.rag: Optional[HybridRetriever] = None
        
        # NEW: The business logic service (handles web search memory fix)
        self.conversation_service: Optional[ConversationService] = None
        
        # Music player reference (for auto-pause)
        self.music_player = None
        
        self._initialize_modules()
    
    def _initialize_modules(self):
        """Load all modules and initialize service"""
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
            
            # Load memory system
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
            
            # Load RAG system
            try:
                self.rag = get_retriever()
                logger.info("RAG system initialized")
                print(f"[OK] RAG: Document search enabled")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"RAG system failed: {e}")
                print(f"[WARN] RAG disabled: {e}")
                sys.stdout.flush()
                self.rag = None
            
            # NEW: Initialize ConversationService (handles web search memory fix)
            try:
                self.conversation_service = ConversationService(
                    intent_detector=self.intent,
                    action_registry=self.actions,
                    memory_manager=self.memory,
                    rag_retriever=self.rag
                )
                logger.info("ConversationService initialized (web search memory enabled)")
                print(f"[OK] ConversationService: Business logic ready (web+memory fixed)")
                sys.stdout.flush()
            except Exception as e:
                logger.error(f"ConversationService failed: {e}")
                print(f"[FAIL] ConversationService failed: {e}")
                sys.stdout.flush()
                raise
            
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
        if self.music_player:
            try:
                if self.music_player.auto_resume():
                    logger.info("Auto-resumed music after interaction")
            except Exception as e:
                logger.debug(f"Music resume failed: {e}")
    
    async def wait_for_wake_word(self) -> bool:
        """Wait for wake word detection"""
        if not self.wake_word:
            logger.debug("Wake word detector not available, skipping")
            print("⚠️  Wake word detection disabled, starting immediately...")
            return True
        
        try:
            logger.debug("Listening for wake word...")
            self.wake_word.start()
            detected = self.wake_word.wait_for_wake_word()
            self.wake_word.stop()
            
            if detected:
                self._pause_all_audio()
            
            return detected
        except Exception as e:
            logger.error(f"Wake word error: {e}")
            print(f"⚠️  Wake word error: {e}")
            return True
    
    def listen_to_user(self) -> str:
        """Record and transcribe user speech"""
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
    
    def speak(self, text: str):
        """Speak text to user"""
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
        Process user input through the service.
        
        SIMPLIFIED: Just calls the service and returns response.
        Service handles memory retrieval, intent detection, routing, and storage.
        
        FIXED: Service now passes memory to web searches and stores ALL turns.
        
        Args:
            user_input: User's transcribed speech
            
        Returns:
            Response message
        """
        try:
            # Call the service (handles everything including web search fix)
            result = await self.conversation_service.process_input(user_input)
            
            # Log performance and metadata
            logger.info(
                f"Processed in {result['duration_ms']:.0f}ms "
                f"(intent: {result['intent']}, "
                f"memory: {result['memory_stored']}, "
                f"category: {result['memory_category']}, "
                f"rag: {result['rag_used']})"
            )
            
            # Print status for debugging
            print(
                f"[PROCESSED] {result['duration_ms']:.0f}ms | "
                f"Intent: {result['intent']} | "
                f"Memory: {'✓' if result['memory_stored'] else '✗'} "
                f"({result['memory_category']})"
            )
            sys.stdout.flush()
            
            return result['response']
            
        except Exception as e:
            logger.error(f"Error in process_user_input: {e}", exc_info=True)
            print(f"[ERROR] {e}")
            sys.stdout.flush()
            return "Sorry, I encountered an error processing your request."
    
    async def run_loop(self):
        """Main assistant loop (voice input, voice output)"""
        logger.info("Starting assistant loop...")
        print("[START] Assistant loop starting...")
        sys.stdout.flush()
        
        # Display system stats at startup
        if self.conversation_service:
            stats = self.conversation_service.get_stats()
            if stats.get('memory_enabled'):
                mem_stats = stats['memory']['sql']
                print(f"[MEMORY] Loaded: {mem_stats['total_facts']} facts, "
                      f"{mem_stats['total_conversations']} conversations")
            
            if stats.get('rag_enabled') and 'rag' in stats:
                rag_stats = stats['rag']
                print(f"[RAG] Indexed: {rag_stats['total_documents']} documents, "
                      f"{rag_stats['total_chunks']} chunks")
            
            print("[INFO] Web searches now use memory context and are stored in sessions")
        
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
                    self._resume_all_audio()
                    continue
                
                # Process via service (handles web search memory fix automatically)
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
        print("Special commands: 'memory: <cmd>', 'rag: <cmd>'\n")
        
        # Show stats
        if self.conversation_service:
            stats = self.conversation_service.get_stats()
            if stats.get('memory_enabled'):
                mem_stats = stats['memory']['sql']
                print(f"Memory: {mem_stats['total_facts']} facts loaded")
            
            if stats.get('rag_enabled') and 'rag' in stats:
                rag_stats = stats['rag']
                print(f"RAG: {rag_stats['total_documents']} documents indexed")
            
            print("Info: Web searches now use memory and are stored in sessions\n")
        
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
                    
                    # Special memory commands
                    if user_input.lower().startswith("memory:"):
                        await self._handle_memory_command(user_input[7:].strip())
                        continue
                    
                    # Special RAG commands
                    if user_input.lower().startswith("rag:"):
                        await self._handle_rag_command(user_input[4:].strip())
                        continue
                    
                    # Process with service (handles web search memory automatically)
                    response = await self.process_user_input(user_input)
                    print(f"\nAssistant: {response}\n")
                    
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    break
                except Exception as e:
                    print(f"\nError: {e}\n")
    
    # ... (keep all other methods: _handle_memory_command, _handle_rag_command, 
    #      run_voice_to_text_loop, run_text_to_voice_loop, get_status, run_headless)
    #      unchanged from your original version
    
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
        
        elif command_lower == "session":
            # NEW: Show current session history
            convs = self.memory.get_conversation_history(limit=10)
            print(f"\n💬 Current Session ({len(convs)} turns):")
            for conv in convs:
                print(f"\n  Turn {conv.turn_no} [{conv.intent_type}]:")
                print(f"  User: {conv.user_input}")
                print(f"  Assistant: {conv.assistant_response[:100]}...")
        
        else:
            print("Memory commands: stats, search <query>, facts, session")
    
    async def _handle_rag_command(self, command: str):
        """Handle special RAG commands"""
        if not self.rag:
            print("RAG system not available")
            return
        
        command_lower = command.lower()
        
        if command_lower in ["stats", "status"]:
            from modules.rag import get_indexer
            indexer = get_indexer()
            stats = indexer.get_stats()
            print(f"\n📊 RAG Stats:")
            print(f"  Documents: {stats.total_documents}")
            print(f"  Chunks: {stats.total_chunks}")
            print(f"  Size: {stats.total_size_bytes:,} bytes")
            print(f"  By type: {stats.documents_by_type}")
            if stats.last_indexed:
                print(f"  Last indexed: {stats.last_indexed}")
        
        elif command_lower.startswith("search "):
            query = command[7:].strip()
            results = await self.rag.retrieve(query, top_k=5)
            print(f"\n🔍 Found {len(results)} documents:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. [{result.relevance_score:.2f}] {result.document_name}")
                print(f"     {result.content[:100]}...")
        
        elif command_lower.startswith("index "):
            path = command[6:].strip()
            from modules.rag import get_indexer
            indexer = get_indexer()
            try:
                if Path(path).is_file():
                    doc = indexer.index_document(path)
                    print(f"✅ Indexed: {doc.file_name} ({doc.num_chunks} chunks)")
                else:
                    docs = indexer.index_directory(path)
                    print(f"✅ Indexed {len(docs)} documents")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        else:
            print("RAG commands: stats, search <query>, index <path>")
    
    async def run_voice_to_text_loop(self):
        """Voice input, text output mode"""
        logger.info("Starting voice-to-text loop...")
        print("[START] Voice-to-text mode...")
        sys.stdout.flush()
        
        while True:
            try:
                if not await self.wait_for_wake_word():
                    continue
                
                print("\n[ASSISTANT] Listening...")
                sys.stdout.flush()
                
                user_input = self.listen_to_user()
                if not user_input:
                    self._resume_all_audio()
                    continue
                
                # Process via service
                response = await self.process_user_input(user_input)
                
                logger.info(f"Response: {response}")
                print(f"\n[ASSISTANT] {response}\n")
                sys.stdout.flush()
                
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
                    user_input = await asyncio.get_event_loop().run_in_executor(executor, get_input)
                    
                    if user_input is None or user_input.lower() == 'exit':
                        break
                    
                    if not user_input.strip():
                        continue
                    
                    self._pause_all_audio()
                    
                    # Process via service
                    response = await self.process_user_input(user_input)
                    
                    logger.info(f"Response: {response}")
                    self.speak(response)
                    
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
            'memory': self.memory is not None,
            'rag': self.rag is not None,
            'service': self.conversation_service is not None
        }
        
        # Add service stats if available
        if self.conversation_service:
            service_stats = self.conversation_service.get_stats()
            status['service_stats'] = service_stats
        
        return status
    
    async def run_headless(self):
        """Headless mode for automation/API"""
        logger.info("Headless mode - minimal initialization")
        print("[INFO] Headless mode ready for API/automation")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Headless mode stopped")