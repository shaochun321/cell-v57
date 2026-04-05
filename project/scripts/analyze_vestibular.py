from __future__ import annotations

from pathlib import Path
import sys
import os

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_ROOT / ".mplconfig"))
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from analyze_multipole import main


if __name__ == "__main__":
    main()
