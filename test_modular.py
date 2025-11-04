#!/usr/bin/env python3
"""
Apply Final Fixes

Checks which fixes need to be applied.
"""

from pathlib import Path

def check_file(path: str, check_for: str, description: str) -> bool:
    """Check if a fix has been applied"""
    file_path = Path(path)
    
    if not file_path.exists():
        print(f"[MISSING] {path}")
        return False
    
    content = file_path.read_text(encoding='utf-8', errors='ignore')
    
    if check_for in content:
        print(f"[OK] {description}: {path}")
        return True
    else:
        print(f"[NEEDS FIX] {description}: {path}")
        return False

def main():
    print("="*60)
    print("Checking Final Fixes")
    print("="*60)
    print()
    
    fixes_needed = []
    
    # Check 1: main.py buffering fix
    if not check_file(
        "main.py",
        "sys.stdout.reconfigure(line_buffering=True)",
        "Buffering fix"
    ):
        fixes_needed.append("main.py - Add buffering fix")
    
    # Check 2: orchestrator sys import
    if not check_file(
        "core/orchestrator.py",
        "import sys",
        "sys import"
    ):
        fixes_needed.append("core/orchestrator.py - Add 'import sys'")
    
    # Check 3: orchestrator flush calls
    if not check_file(
        "core/orchestrator.py",
        "sys.stdout.flush()",
        "Flush calls"
    ):
        fixes_needed.append("core/orchestrator.py - Add sys.stdout.flush() calls")
    
    # Check 4: Intent class name
    if not check_file(
        "modules/intent/simple_ai.py",
        "class SimpleAiIntent",
        "Intent class name"
    ):
        fixes_needed.append("modules/intent/simple_ai.py - Fix class name to SimpleAiIntent")
    
    # Check 5: Web search fix
    if not check_file(
        "core/orchestrator.py",
        'if action.name == "WebSearchAction"',
        "Web search fix"
    ):
        fixes_needed.append("core/orchestrator.py - Fix web search action lookup")
    
    # Check 6: No emojis in orchestrator
    if not check_file(
        "core/orchestrator.py",
        "[OK]",
        "ASCII output"
    ):
        fixes_needed.append("core/orchestrator.py - Replace emojis with ASCII")
    
    print()
    print("="*60)
    
    if fixes_needed:
        print(f"[ACTION NEEDED] {len(fixes_needed)} fixes to apply:")
        print()
        for fix in fixes_needed:
            print(f"  - {fix}")
        print()
        print("Copy the updated files from the artifacts above.")
    else:
        print("[SUCCESS] All fixes applied!")
        print()
        print("You can now run: python main.py")
    
    print("="*60)

if __name__ == "__main__":
    main()