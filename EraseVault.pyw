#!/usr/bin/env pythonw
"""
Windowless GUI launcher for EraseVault on Windows (.pyw).
Launching this file with pythonw.exe opens EraseVault directly with zero console window.
"""

import sys
from main import main

if __name__ == "__main__":
    sys.exit(main())
