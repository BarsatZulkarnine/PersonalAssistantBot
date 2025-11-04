#!/usr/bin/env python3
"""
Voice Assistant - Modular Architecture

Entry point for the voice assistant.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import AssistantOrchestrator
from utils.logger import get_logger
from utils.config import load_global_config

logger = get_logger('main')

def print_banner():
    """Print startup banner"""
    banner = """
    ╔══════════════════════════════════════════╗
    ║                                          ║
    ║        🎤 Voice Assistant v3.0          ║
    ║        Modular Architecture              ║
    ║                                          ║
    ╚══════════════════════════════════════════╝
    """
    print(banner)

def print_module_status(orchestrator: AssistantOrchestrator):
    """Print status of all modules"""
    status = orchestrator.get_status()
    
    print("\n📦 Module Status:")
    print(f"   {'✅' if status['wake_word'] else '❌'} Wake Word Detection")
    print(f"   {'✅' if status['stt'] else '❌'} Speech-to-Text")
    print(f"   {'✅' if status['tts'] else '❌'} Text-to-Speech")
    print(f"   {'✅' if status['intent'] else '❌'} Intent Detection")
    print(f"   {'✅' if status['actions'] > 0 else '❌'} Actions ({status['actions']} loaded)")
    print()

async def main():
    """Main entry point"""
    try:
        # Print banner
        print_banner()
        
        # Load global config
        logger.info("Loading configuration...")
        config = load_global_config()
        
        # Initialize orchestrator
        logger.info("Initializing orchestrator...")
        orchestrator = AssistantOrchestrator()
        
        # Print module status
        print_module_status(orchestrator)
        
        # Check if all critical modules loaded
        status = orchestrator.get_status()
        if not (status['stt'] and status['tts'] and status['intent']):
            logger.error("Critical modules failed to load")
            return 1
        
        # Start main loop
        print("🎤 Assistant ready! Say the wake word to start.\n")
        await orchestrator.run_loop()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        print("\nGoodbye!")
        return 0
    
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        print(f"\nCritical error: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)