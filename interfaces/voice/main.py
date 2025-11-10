"""
Voice Interface - Audio Mode

Full voice interface using microphone + speaker.
This is the traditional "voice assistant" mode.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.orchestrator import AssistantOrchestrator
from utils.logger import get_logger
from utils.config import load_global_config

logger = get_logger('interfaces.voice')


def print_banner():
    """Print voice interface banner"""
    banner = """
    ╔════════════════════════════════════════╗
    ║   Voice Assistant - Voice Interface    ║
    ║   Microphone + Speaker Mode            ║
    ╚════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """Voice interface entry point"""
    try:
        print_banner()
        
        # Load config
        logger.info("Loading configuration...")
        config = load_global_config()
        
        # Initialize orchestrator with VOICE I/O
        logger.info("Initializing voice interface...")
        print("Initializing...")
        
        orchestrator = AssistantOrchestrator(
            input_mode='microphone',
            output_mode='speaker'
        )
        
        # Show status
        status = orchestrator.get_status()
        print(f"\n[OK] Ready! Say the wake word to start.")
        print(f"[INFO] Input: {status['audio_input']}")
        print(f"[INFO] Output: {status['audio_output']}")
        
        if status.get('service_stats'):
            stats = status['service_stats']
            if stats.get('memory_enabled'):
                mem = stats['memory']['sql']
                print(f"[MEMORY] {mem['total_facts']} facts, {mem['total_conversations']} conversations")
            if stats.get('rag_enabled') and 'rag' in stats:
                rag = stats['rag']
                print(f"[RAG] {rag['total_documents']} documents indexed")
        
        print("\nListening for wake word...\n")
        
        # Run main loop
        await orchestrator.run_loop()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    
    except Exception as e:
        logger.critical(f"Voice interface error: {e}", exc_info=True)
        print(f"\n💥 Error: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)