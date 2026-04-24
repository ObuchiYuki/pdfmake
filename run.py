#!/usr/bin/env python3
"""
Development launcher — run pdfmake without installing the package.

Usage:
    python run.py make  dir1 dir2
    python run.py unpack  file.pdf
    python run.py compress file.pdf
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pdfmake.__main__ import main

main()
