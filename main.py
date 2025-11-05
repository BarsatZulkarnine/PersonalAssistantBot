#!/usr/bin/env python3
"""
Voice Assistant - Modular Architecture

Entry point for the voice assistant.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Force unbuffered output so prints show immediately
sys.stdout.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.orchestrator import AssistantOrchestrator
from utils.logger import get_logger
from utils.config import load_global_config

logger = get_logger('main')

def print_banner():
    """Print startup banner"""
    banner = """
    ================================================
                                          
            Voice Assistant v3.0          
            Modular Architecture              
                                          
    ================================================
    """
    print(banner)

def print_module_status(orchestrator: AssistantOrchestrator):
    """Print status of all modules"""
    status = orchestrator.get_status()
    
    print("\nModule Status:")
    print(f"   {'[OK]' if status['wake_word'] else '[FAIL]'} Wake Word Detection")
    print(f"   {'[OK]' if status['stt'] else '[FAIL]'} Speech-to-Text")
    print(f"   {'[OK]' if status['tts'] else '[FAIL]'} Text-to-Speech")
    print(f"   {'[OK]' if status['intent'] else '[FAIL]'} Intent Detection")
    print(f"   {'[OK]' if status['actions'] > 0 else '[FAIL]'} Actions ({status['actions']} loaded)")
    print()

def parse_args():
    parser = argparse.ArgumentParser(description="Voice Assistant")
    parser.add_argument("--mode", choices=["voice", "text", "headless"], 
                       default=None, help="Operation mode")
    parser.add_argument("--input", choices=["voice", "text"],
                       default=None, help="Input method")
    parser.add_argument("--output", choices=["voice", "text"],
                       default=None, help="Output method")
    return parser.parse_args()

def determine_mode(args):
    """Determine operation mode from arguments"""
    # If --mode is explicitly set, use it
    if args.mode:
        return args.mode
    
    # Otherwise, infer from --input and --output
    if args.input == "text" and args.output == "text":
        return "text"
    elif args.input == "text" and args.output == "voice":
        return "text_to_voice"  # Text input, voice output
    elif args.input == "voice" and args.output == "text":
        return "voice_to_text"  # Voice input, text output
    else:
        # Default to voice mode
        return "voice"

async def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        # Print banner
        print_banner()
        sys.stdout.flush()
        
        # Determine mode
        mode = determine_mode(args)
        print(f"Mode: {mode}")
        print(f"  Input: {args.input or 'voice'}")
        print(f"  Output: {args.output or 'voice'}")
        sys.stdout.flush()
        
        # Load global config
        logger.info("Loading configuration...")
        print("Loading configuration...")
        sys.stdout.flush()
        config = load_global_config()
        
        # Initialize orchestrator
        logger.info("Initializing orchestrator...")
        print("Initializing orchestrator...")
        sys.stdout.flush()
        orchestrator = AssistantOrchestrator()
        
        # Print module status
        print_module_status(orchestrator)
        sys.stdout.flush()
        
        # Check if all critical modules loaded
        status = orchestrator.get_status()
        if not (status['stt'] and status['tts'] and status['intent']):
            logger.error("Critical modules failed to load")
            return 1
        
        # Run appropriate mode
        if mode == "voice":
            # Regular voice mode (voice input, voice output)
            print("Assistant ready! Say the wake word to start.\n")
            sys.stdout.flush()
            await orchestrator.run_loop()
            
        elif mode == "text":
            # Text mode (text input, text output)
            print("Assistant ready! Type your commands.\n")
            sys.stdout.flush()
            await orchestrator.run_text_loop()
            
        elif mode == "voice_to_text":
            # Voice input, text output
            print("Assistant ready! Say the wake word to start.\n")
            print("Responses will be shown as text only.\n")
            sys.stdout.flush()
            await orchestrator.run_voice_to_text_loop()
            
        elif mode == "text_to_voice":
            # Text input, voice output
            print("Assistant ready! Type your commands.\n")
            print("Responses will be spoken.\n")
            sys.stdout.flush()
            await orchestrator.run_text_to_voice_loop()
            
        elif mode == "headless":
            # Headless mode for automation/API
            print("Assistant running in headless mode.\n")
            sys.stdout.flush()
            await orchestrator.run_headless()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        print("\n👋 Goodbye!")
        return 0
    
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        print(f"\n💥 Critical error: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)