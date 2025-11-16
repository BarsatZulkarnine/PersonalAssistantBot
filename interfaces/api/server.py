"""
API Interface - Redirect to main API
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import and run the main API
from api.main import app

def main():
    import uvicorn
    print("[OK] Starting API server from api/main.py")
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()