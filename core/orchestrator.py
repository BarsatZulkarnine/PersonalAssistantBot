"""
Main Orchestrator - PHASE 2: WITH I/O ABSTRACTION

Now uses abstract I/O interfaces instead of direct STT/TTS.
Can easily swap input (mic/keyboard) and output (speaker/console).
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

# Service
from core.services.conversation_service import ConversationService

# Memory and RAG
from modules.memory import get_memory_manager, MemoryManager
from modules.rag import get_retriever, HybridRetriever

# NEW: I/O Abstraction
from core.io import AudioInput, AudioOutput, IOFactory
from core.io.output.speaker_output import SpeakerOutput  # FIXED: Added import
from core.io.output.console_output import ConsoleOutput  # FIXED: Added import

logger = get_logger('orchestrator')

class AssistantOrchestrator:
    """
    Main coordinator - PHASE 2 with I/O Abstraction.
    
    Changes:
    - Uses AudioInput instead of direct STT
    - Uses AudioOutput instead of direct TTS
    - I/O is swappable via factory
    """
    
    def __init__(
        self,
        input_mode: str = 'auto',
        output_mode: str = 'auto'
    ):
        """
        Initialize orchestrator.
        
        Args:
            input_mode: 'auto', 'microphone', 'keyboard'
            output_mode: 'auto', 'speaker', 'console'
        """
        self.input_mode = input_mode
        self.output_mode = output_mode
        
        self.loader = get_module_loader()
        
        # Hardware modules (for I/O factory)
        self.wake_word: Optional[WakeWordDetector] = None
        self.stt: Optional[STTProvider] = None
        self.tts: Optional[TTSProvider] = None
        
        # Business logic modules
        self.intent: Optional[IntentDetector] = None
        self.actions: Optional[ActionRegistry] = None
        self.memory: Optional[MemoryManager] = None
        self.rag: Optional[HybridRetriever] = None
        self.conversation_service: Optional[ConversationService] = None
        
        # NEW: Abstract I/O interfaces
        self.audio_input: Optional[AudioInput] = None
        self.audio_output: Optional[AudioOutput] = None
        
        # Music player reference
        self.music_player = None
        
        self._initialize_modules()
    
    def _initialize_modules(self):
        """Load all modules and initialize I/O"""
        try:
            logger.info("Initializing modules...")
            
            # Load wake word detector
            try:
                self.wake_word = self.loader.load_module('wake_word')
                logger.info(f"Wake word: {self.wake_word.__class__.__name__}")
                print(f"[OK] Wake word: {self.wake_word.__class__.__name__}")
            except Exception as e:
                logger.warning(f"Wake word module failed: {e}")
                print(f"[WARN] Wake word detection disabled")
                self.wake_word = None
            
            # Load STT (needed for microphone input)
            try:
                self.stt = self.loader.load_module('stt')
                logger.info(f"STT: {self.stt.__class__.__name__}")
                print(f"[OK] STT: {self.stt.__class__.__name__}")
            except Exception as e:
                logger.error(f"STT module failed: {e}")
                print(f"[FAIL] STT module failed: {e}")
                # Don't raise - might use keyboard input
                self.stt = None
            
            # Load TTS (needed for speaker output)
            try:
                self.tts = self.loader.load_module('tts')
                logger.info(f"TTS: {self.tts.__class__.__name__}")
                print(f"[OK] TTS: {self.tts.__class__.__name__}")
            except Exception as e:
                logger.error(f"TTS module failed: {e}")
                print(f"[FAIL] TTS module failed: {e}")
                # Don't raise - might use console output
                self.tts = None
            
            # Load intent detector
            try:
                self.intent = self.loader.load_module('intent')
                logger.info(f"Intent: {self.intent.__class__.__name__}")
                print(f"[OK] Intent: {self.intent.__class__.__name__}")
            except Exception as e:
                logger.error(f"Intent module failed: {e}")
                print(f"[FAIL] Intent module failed: {e}")
                raise
            
            # Load action registry
            try:
                from modules.actions.registry import get_action_registry
                self.actions = get_action_registry()
                logger.info(f"Actions: {len(self.actions.list_actions())} loaded")
                print(f"[OK] Actions: {len(self.actions.list_actions())} loaded")
                self._get_music_player_reference()
            except Exception as e:
                logger.error(f"Actions failed: {e}")
                print(f"[FAIL] Actions failed: {e}")
                raise
            
            # Load memory system
            try:
                self.memory = get_memory_manager()
                logger.info("Memory system initialized")
                print(f"[OK] Memory: Hybrid SQL + Vector storage")
            except Exception as e:
                logger.error(f"Memory system failed: {e}")
                print(f"[WARN] Memory disabled: {e}")
                self.memory = None
            
            # Load RAG system
            try:
                self.rag = get_retriever()
                logger.info("RAG system initialized")
                print(f"[OK] RAG: Document search enabled")
            except Exception as e:
                logger.error(f"RAG system failed: {e}")
                print(f"[WARN] RAG disabled: {e}")
                self.rag = None
            
            # Initialize ConversationService
            try:
                self.conversation_service = ConversationService(
                    intent_detector=self.intent,
                    action_registry=self.actions,
                    memory_manager=self.memory,
                    rag_retriever=self.rag
                )
                logger.info("ConversationService initialized")
                print(f"[OK] ConversationService: Business logic ready")
            except Exception as e:
                logger.error(f"ConversationService failed: {e}")
                print(f"[FAIL] ConversationService failed: {e}")
                raise
            
            # NEW: Initialize I/O via factory
            try:
                self.audio_input, self.audio_output = IOFactory.create_io_pair(
                    input_mode=self.input_mode,
                    output_mode=self.output_mode,
                    stt_provider=self.stt,
                    tts_provider=self.tts,
                    fallback=True  # Auto-fallback if hardware unavailable
                )
                
                # Log I/O configuration
                input_caps = self.audio_input.get_capabilities()
                output_caps = self.audio_output.get_capabilities()
                
                logger.info(
                    f"I/O initialized: "
                    f"input={self.audio_input.__class__.__name__} ({input_caps.input_type}), "
                    f"output={self.audio_output.__class__.__name__} ({output_caps.output_type})"
                )
                
                print(f"[OK] Input: {self.audio_input.__class__.__name__} ({input_caps.input_type})")
                print(f"[OK] Output: {self.audio_output.__class__.__name__} ({output_caps.output_type})")
                
            except Exception as e:
                logger.error(f"I/O initialization failed: {e}")
                print(f"[FAIL] I/O initialization failed: {e}")
                raise
            
            logger.info("All modules initialized successfully!")
            print("[OK] All modules initialized with I/O abstraction!")
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
                    logger.info("Music player reference obtained")
                    break
        except Exception as e:
            logger.debug(f"Could not get music player reference: {e}")
    
    def _pause_all_audio(self):
        """Pause all audio outputs"""
        if self.music_player:
            try:
                if self.music_player.auto_pause():
                    logger.info("Auto-paused music for wake word")
            except Exception as e:
                logger.debug(f"Music pause failed: {e}")
        
        # Stop TTS if available
        if self.tts and hasattr(self.tts, 'is_speaking') and self.tts.is_speaking:
            try:
                self.tts.stop()
                logger.info("Stopped TTS for wake word")
            except Exception as e:
                logger.debug(f"TTS stop failed: {e}")
    
    def _resume_all_audio(self):
        """Resume paused audio"""
        if self.music_player:
            try:
                if self.music_player.auto_resume():
                    logger.info("Auto-resumed music")
            except Exception as e:
                logger.debug(f"Music resume failed: {e}")
    
    async def wait_for_wake_word(self) -> bool:
        """Wait for wake word detection"""
        if not self.wake_word:
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
            return True
    
    async def process_user_input(self, user_input: str) -> str:
        """
        Process user input through the service.
        
        Args:
            user_input: User's text input
            
        Returns:
            Response message
        """
        try:
            result = await self.conversation_service.process_input(user_input)
            
            logger.info(
                f"Processed in {result['duration_ms']:.0f}ms "
                f"(intent: {result['intent']}, "
                f"memory: {result['memory_stored']} [{result['memory_category']}])"
            )
            
            print(
                f"[PROCESSED] {result['duration_ms']:.0f}ms | "
                f"Intent: {result['intent']} | "
                f"Memory: {'✓' if result['memory_stored'] else '✗'} "
                f"({result['memory_category']})"
            )
            sys.stdout.flush()
            
            return result['response']
            
        except Exception as e:
            logger.error(f"Error processing input: {e}", exc_info=True)
            return "Sorry, I encountered an error."
    
    async def run_loop(self):
        """
        Main assistant loop - USING I/O ABSTRACTION
        
        Now hardware-agnostic!
        """
        logger.info("Starting assistant loop...")
        print("[START] Assistant loop starting...")
        print(f"[INFO] Input: {self.audio_input.__class__.__name__}")
        print(f"[INFO] Output: {self.audio_output.__class__.__name__}")
        sys.stdout.flush()
        
        # Display stats
        if self.conversation_service:
            stats = self.conversation_service.get_stats()
            if stats.get('memory_enabled'):
                mem = stats['memory']['sql']
                print(f"[MEMORY] {mem['total_facts']} facts, {mem['total_conversations']} conversations")
            if stats.get('rag_enabled') and 'rag' in stats:
                rag = stats['rag']
                print(f"[RAG] {rag['total_documents']} documents, {rag['total_chunks']} chunks")
        
        while True:
            try:
                # Wait for wake word
                if not await self.wait_for_wake_word():
                    continue
                
                # Acknowledge (only if using speaker)
                if isinstance(self.audio_output, SpeakerOutput):
                    self.audio_output.output("Yes?")
                
                # Listen (NEW: via abstraction)
                logger.debug("Waiting for input...")
                print("[LISTEN] Waiting for input...")
                sys.stdout.flush()
                
                input_result = self.audio_input.listen()
                
                if input_result.is_empty():
                    self._resume_all_audio()
                    continue
                
                user_input = input_result.text
                logger.info(f"Input received: {user_input}")
                print(f"[INPUT] {user_input}")
                sys.stdout.flush()
                
                # Process
                response = await self.process_user_input(user_input)
                
                # Output (NEW: via abstraction)
                logger.info(f"Response: {response}")
                print(f"[RESPONSE] {response[:80]}...")
                sys.stdout.flush()
                
                self.audio_output.output(response)
                
                # Resume audio
                self._resume_all_audio()
                
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                print(f"[ERROR] {e}")
                sys.stdout.flush()
                self.audio_output.output("Sorry, something went wrong.")
                self._resume_all_audio()
                continue
    
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
            'service': self.conversation_service is not None,
            'audio_input': self.audio_input.__class__.__name__ if self.audio_input else None,
            'audio_output': self.audio_output.__class__.__name__ if self.audio_output else None
        }
        
        if self.conversation_service:
            status['service_stats'] = self.conversation_service.get_stats()
        
        return status
    
    # Keep all other methods (memory commands, RAG commands, etc.)
    # from your current orchestrator unchanged