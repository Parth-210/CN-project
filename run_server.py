"""
Entry point — RDP Server
"""

import sys
import os

# Ensure the project root is importable regardless of CWD
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from server.server_app import main

if __name__ == "__main__":
    main()
