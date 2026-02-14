"""
Pytest configuration for script tests.

Adds the scripts directory to sys.path so scripts can be imported
without hardcoded sys.path.insert() calls in test files.
"""

import sys
from pathlib import Path

# Add project root to path so 'from scripts.module import ...' works
# Path: conftest.py -> test_scripts -> tests -> src -> VECTRA-BOILERPLATE (project root)
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
