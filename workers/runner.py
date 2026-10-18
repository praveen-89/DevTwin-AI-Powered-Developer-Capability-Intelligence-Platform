"""
DevTwin — Worker Runner Root Entrypoint
"""

import sys
from pathlib import Path

# Add backend directory to sys.path so app modules are resolvable
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.workers.runner import main

if __name__ == "__main__":
    main()
