"""
Pytest configuration for script tests.

Adds the scripts directory to sys.path so scripts can be imported
without hardcoded sys.path.insert() calls in test files.
"""

import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
