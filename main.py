#!/usr/bin/env python3
"""
Voice Assistant - Phase 3 Entry Point

Routes to appropriate interface based on arguments.
Maintains backward compatibility with Phase 1 & 2.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def print_banner():
    """Print startup banner"""
    banner = """
    ╔════════════════════════════════════════════════════╗
    ║                                                    ║
    ║          Voice Assistant v3.0                      ║
    ║          Phase 3: Multiple Interfaces              ║
    ║                                                    ║
    ╚════════════════════════════════════════════════════╝
    """
    print(banner)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Voice Assistant with Multiple Interfaces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interface Selection:
  --interface cli       Text-only interface (keyboard + console)
  --interface voice     Voice interface (microphone + speaker) [DEFAULT]
  --interface api       REST API server (no I/O)

Legacy Compatibility:
  --input/--output      Phase 2 style (uses orchestrator directly)
  --mode                Phase 1 style (voice/text/headless)

Examples:
  # Voice interface (default)
  python main.py
  python main.py --interface voice
  
  # CLI interface (text-only)
  python main.py --interface cli
  
  # API server
  python main.py --interface api
  
  # Legacy Phase 2 style
  python main.py --input keyboard --output console
  
  # Legacy Phase 1 style
  python main.py --mode text
        """
    )
    
    # Phase 3: Interface selection
    parser.add_argument(
        "--interface", 
        choices=["cli", "voice", "api"],
        default=None,
        help="Interface to use (cli, voice, api)"
    )
    
    # Phase 2: I/O selection (legacy)
    parser.add_argument(
        "--input", 
        choices=["auto", "microphone", "keyboard"],
        default=None,
        help="Input mode (Phase 2 legacy)"
    )
    
    parser.add_argument(
        "--output",
        choices=["auto", "speaker", "console"],
        default=None,
        help="Output mode (Phase 2 legacy)"
    )
    
    # Phase 1: Mode selection (legacy)
    parser.add_argument(
        "--mode",
        choices=["voice", "text", "headless"],
        help="Mode (Phase 1 legacy)"
    )
    
    return parser.parse_args()


def determine_interface(args):
    """
    Determine which interface to use based on arguments.
    
    Priority:
    1. --interface (Phase 3)
    2. --input/--output (Phase 2)
    3. --mode (Phase 1)
    4. Default: voice
    
    Returns:
        ('cli'|'voice'|'api'|'orchestrator', input_mode, output_mode)
    """
    
    # Priority 1: --interface (Phase 3)
    if args.interface:
        if args.interface == "cli":
            return ('cli', None, None)
        elif args.interface == "voice":
            return ('voice', None, None)
        elif args.interface == "api":
            return ('api', None, None)
    
    # Priority 2: --input/--output (Phase 2 legacy)
    if args.input or args.output:
        input_mode = args.input or 'auto'
        output_mode = args.output or 'auto'
        return ('orchestrator', input_mode, output_mode)
    
    # Priority 3: --mode (Phase 1 legacy)
    if args.mode:
        if args.mode == "text":
            return ('orchestrator', 'keyboard', 'console')
        elif args.mode == "voice":
            return ('orchestrator', 'microphone', 'speaker')
        elif args.mode == "headless":
            return ('orchestrator', 'keyboard', 'console')
    
    # Default: voice interface
    return ('voice', None, None)


async def run_cli_interface():
    """Run CLI interface"""
    from interfaces.cli.main import main as cli_main
    return await cli_main()


async def run_voice_interface():
    """Run voice interface"""
    from interfaces.voice.main import main as voice_main
    return await voice_main()


def run_api_interface():
    """Run API server"""
    from interfaces.api.server import main as api_main
    api_main()  # Blocking call (uvicorn)
    return 0


async def run_orchestrator(input_mode, output_mode):
    """Run orchestrator directly (Phase 2 legacy)"""
    from core.orchestrator import AssistantOrchestrator
    from utils.config import load_global_config
    from utils.logger import get_logger
    
    logger = get_logger('main')
    
    try:
        print(f"Legacy Mode - Using Orchestrator Directly")
        print(f"  Input: {input_mode}")
        print(f"  Output: {output_mode}\n")
        
        # Load config
        logger.info("Loading configuration...")
        config = load_global_config()
        
        # Initialize orchestrator
        logger.info("Initializing orchestrator...")
        orchestrator = AssistantOrchestrator(
            input_mode=input_mode,
            output_mode=output_mode
        )
        
        # Show status
        status = orchestrator.get_status()
        if not (status['intent'] and status['service']):
            print("❌ Critical modules failed to load")
            return 1
        
        print(f"[OK] Ready!")
        print(f"[INFO] Input: {status['audio_input']}")
        print(f"[INFO] Output: {status['audio_output']}\n")
        
        # Run main loop
        await orchestrator.run_loop()
        
        return 0
        
    except Exception as e:
        logger.critical(f"Error: {e}", exc_info=True)
        print(f"💥 Error: {e}")
        return 1


async def main():
    """Main entry point"""
    args = parse_args()
    
    try:
        print_banner()
        
        # Determine which interface to use
        interface, input_mode, output_mode = determine_interface(args)
        
        # Route to appropriate interface
        if interface == 'cli':
            print("Starting CLI Interface...\n")
            return await run_cli_interface()
        
        elif interface == 'voice':
            print("Starting Voice Interface...\n")
            return await run_voice_interface()
        
        elif interface == 'api':
            print("Starting API Server...\n")
            asyncio.get_event_loop().stop()
            return run_api_interface()
        
        elif interface == 'orchestrator':
            print("Starting Legacy Orchestrator Mode...\n")
            return await run_orchestrator(input_mode, output_mode)
        
        else:
            print(f"❌ Unknown interface: {interface}")
            return 1
        
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        return 0
    
    except Exception as e:
        print(f"\n💥 Critical error: {e}")
        return 1


if __name__ == "__main__":
    try:
        args = parse_args()

        # Detect API mode *before* entering asyncio.run()
        if args.interface == "api":
            print_banner()
            print("Starting API Server...\n")
            run_api_interface()  # blocking call, manages its own loop
            sys.exit(0)

        # All other interfaces (CLI, voice, legacy orchestrator)
        exit_code = asyncio.run(main())
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
