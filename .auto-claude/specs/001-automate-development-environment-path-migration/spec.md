# Specification: Automated Development Environment Path Migration

## Overview

This task creates a fully automated Python migration script to replace all hardcoded absolute paths from `/home/nomad` to `/home/devops` across the VECTRA-PLAYER codebase. The script will systematically update 63 path references across 22 files (documentation, scripts, configuration, and knowledge files), while providing comprehensive safety mechanisms including pre-flight validation, automatic backups, verification checks, rollback capability, and detailed audit logging.

## Workflow Type

**Type**: feature

**Rationale**: This is a new feature implementation (migration automation script) that adds a reusable tool to the project. While it performs a refactoring operation, the task itself is creating new automation infrastructure with safety mechanisms, verification logic, and rollback capabilities that don't currently exist.

## Task Scope

### Services Involved
- **main** (primary) - Python project requiring path migration across all directories

### This Task Will:
- [ ] Create automated migration script (`scripts/migrate_paths.py`)
- [ ] Implement pre-flight directory structure validation (`/home/devops` existence check)
- [ ] Build backup mechanism with timestamped copies of all 22 affected files
- [ ] Replace all 63 occurrences of `/home/nomad` with `/home/devops` across:
  - Documentation files (CLAUDE.md, docs/*.md)
  - Python scripts (scripts/*.py, src/*.sh)
  - Configuration files (.github/workflows/*.yml)
  - Knowledge files (docs/rag/*.jsonl)
- [ ] Implement post-migration verification checks
- [ ] Create rollback capability to restore from backups
- [ ] Add comprehensive logging system with audit trail
- [ ] Provide dry-run mode for safe testing

### Out of Scope:
- Modifying actual directory structures on disk (only path references in files)
- Changing environment variable values (config.py already uses dynamic paths)
- Updating external repositories (claude-flow, rugs-rl-bot, REPLAYER)
- Interactive prompts (fully automated execution required)

## Service Context

### main

**Tech Stack:**
- Language: Python 3.12
- Framework: None (standalone application)
- Key directories: src/, docs/, scripts/, .github/
- Package Manager: pip
- Testing: pytest
- Linting: Ruff
- Git Hooks: pre-commit

**Entry Point:** `run.sh` (for application), `scripts/migrate_paths.py` (for migration)

**How to Run:**
```bash
# Application
./run.sh

# Tests
cd src && ../.venv/bin/python -m pytest tests/ -v --tb=short

# Migration script (to be created)
python scripts/migrate_paths.py --dry-run
python scripts/migrate_paths.py --execute
python scripts/migrate_paths.py --rollback
```

**Port:** N/A (no server component)

## Files to Modify

| File | Service | What to Change |
|------|---------|---------------|
| **NEW:** `scripts/migrate_paths.py` | main | Create migration automation script |
| `CLAUDE.md` | main | Update path references (6 occurrences) |
| `scripts/capture_gamehistory.py` | main | Update path references |
| `docs/ML_RL_SYSTEM_OVERVIEW_AND_RESEARCH_PROMPT.md` | main | Update path references |
| `.claude/scratchpad.md` | main | Update path references |
| `docs/plans/GLOBAL-DEVELOPMENT-PLAN.md` | main | Update path references |
| `setup_pyright_lsp.sh` | main | Update path references |
| `docs/reports/TRADING-ARCHITECTURE-REFACTOR-AND-UI-SIMPLIFICATION-HANDOFF-2025-12-28.md` | main | Update path references |
| `docs/plans/PIPELINE-D-VALIDATION-PROMPT.md` | main | Update path references |
| `docs/plans/2025-12-28-pipeline-d-training-data-implementation.md` | main | Update path references |
| `scripts/FLOW-CHARTS/observation-space-design.md` | main | Update path references |
| `docs/DEVELOPMENT-PLAN-DASHBOARD.html` | main | Update path references |
| `docs/DEBUGGING_GUIDE.md` | main | Update path references |
| `start_debugging.sh` | main | Update path references |
| `docs/CROSS_REPO_COORDINATION.md` | main | Update path references |
| `scripts/vectra_index.py` | main | Update claude-flow path import (line 21) |
| `.github/copilot-instructions.md` | main | Update path references |
| `src/bot/code-audit-bot-folder` | main | Update path references |
| `scripts/schema_inventory.py` | main | Update path references |
| `docs/rag/socket_kb.jsonl` | main | Update path references |
| `docs/CI_CD_GUIDE.md` | main | Update path references |
| `.github/workflows/guardrails.yml` | main | Update path references |
| `src/verify_tests.sh` | main | Update path references |

## Files to Reference

These files show patterns to follow:

| File | Pattern to Copy |
|------|----------------|
| `src/config.py` | Environment-based path configuration (uses `Path.home()` and env vars) |
| `scripts/vectra_index.py` | CLI argument parsing with argparse, Path manipulation |
| `.github/workflows/*.yml` | GitHub Actions workflow structure for CI |

## Patterns to Follow

### Pattern 1: Path Handling with pathlib

From `scripts/vectra_index.py`:

```python
from pathlib import Path
import os

def get_data_dir() -> Path:
    """Get data directory from env or default."""
    return Path(os.getenv("RUGS_DATA_DIR", str(Path.home() / "rugs_data")))

# Good: Using pathlib for cross-platform compatibility
src_dir = Path(__file__).resolve().parent.parent / "src"
```

**Key Points:**
- Use `pathlib.Path` for all path operations
- Use `Path.home()` for user directory references
- Avoid string concatenation for paths

### Pattern 2: CLI with Argparse

From `scripts/vectra_index.py`:

```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="Vector index management")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--execute", action="store_true", help="Execute migration")
    args = parser.parse_args()
```

**Key Points:**
- Use argparse for command-line interface
- Provide clear help text for all arguments
- Support boolean flags with `action="store_true"`

### Pattern 3: File Modification Safety

**Best Practice Pattern:**

```python
import shutil
from datetime import datetime

def create_backup(file_path: Path, backup_dir: Path) -> Path:
    """Create timestamped backup of file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{file_path.name}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    return backup_path

def replace_in_file(file_path: Path, old_text: str, new_text: str) -> int:
    """Replace text in file, return count of replacements."""
    content = file_path.read_text()
    new_content = content.replace(old_text, new_text)
    count = content.count(old_text)

    if count > 0:
        file_path.write_text(new_content)

    return count
```

**Key Points:**
- Always backup before modification
- Use atomic write operations where possible
- Track and report replacement counts
- Preserve file metadata with `shutil.copy2`

### Pattern 4: Comprehensive Logging

**Best Practice Pattern:**

```python
import logging
from datetime import datetime

def setup_logging(log_dir: Path) -> logging.Logger:
    """Setup logging with file and console handlers."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
```

**Key Points:**
- Log to both file and console
- Use timestamped log files
- Include timestamps in log entries
- Log all operations for audit trail

## Requirements

### Functional Requirements

1. **Pre-Flight Validation**
   - Description: Verify target directory `/home/devops` exists before any modifications
   - Acceptance: Script exits with clear error message if `/home/devops` not found

2. **Automated Backup Creation**
   - Description: Create timestamped backups of all 22 files before modification
   - Acceptance: Backup directory created with format `backups_YYYYMMDD_HHMMSS/`, all files copied with metadata preserved

3. **Path Replacement Engine**
   - Description: Replace all 63 occurrences of `/home/nomad` with `/home/devops` across all file types
   - Acceptance: All files updated correctly, replacement count matches expected 63 occurrences

4. **Post-Migration Verification**
   - Description: Verify no `/home/nomad` paths remain after migration
   - Acceptance: Grep search returns 0 matches, verification report shows success

5. **Rollback Capability**
   - Description: Restore all files from most recent backup
   - Acceptance: `--rollback` flag restores all files to pre-migration state

6. **Comprehensive Audit Logging**
   - Description: Log all operations to timestamped log file and console
   - Acceptance: Log file contains: files processed, replacements made, errors, verification results

7. **Dry-Run Mode**
   - Description: Preview all changes without modifying files
   - Acceptance: `--dry-run` flag shows what would be changed without executing

### Non-Functional Requirements

1. **Idempotency**
   - Description: Script can be run multiple times safely
   - Acceptance: Running script twice produces same result, no duplicate replacements

2. **Error Handling**
   - Description: Graceful handling of file I/O errors, permission issues
   - Acceptance: Script catches exceptions, logs errors, exits cleanly

3. **Atomicity**
   - Description: Either all files succeed or none are modified (on critical errors)
   - Acceptance: If critical error occurs mid-migration, rollback is triggered automatically

### Edge Cases

1. **Binary Files** - Skip files that cannot be decoded as text (e.g., if any exist in matched list)
2. **Symlinks** - Handle symbolic links by following them or skipping based on safety
3. **File Permissions** - Check write permissions before attempting modifications
4. **Disk Space** - Verify sufficient disk space for backups before starting
5. **Concurrent Execution** - Prevent multiple simultaneous migrations with lock file
6. **Partial Matches** - Only replace `/home/nomad` as complete path component, not as substring in other contexts

## Implementation Notes

### DO
- Use `pathlib.Path` for all path operations (follow pattern in `scripts/vectra_index.py`)
- Create timestamped backups in dedicated directory (e.g., `.backups/migration_20260103_153045/`)
- Log every file operation with INFO level
- Use `shutil.copy2` to preserve file metadata in backups
- Implement dry-run mode that shows exactly what would change
- Count and report replacements per file
- Use argparse for clean CLI (follow pattern in `scripts/vectra_index.py`)
- Return non-zero exit code on errors
- Create summary report at end showing: files processed, total replacements, verification status

### DON'T
- Use string concatenation for paths (use `Path` / operator)
- Modify files without backups
- Suppress errors silently
- Hard-code the old/new paths (use variables/constants)
- Skip verification checks
- Assume files are text-readable (handle encoding errors)
- Modify files outside the project directory

## Development Environment

### Start Services

```bash
# No services to start - standalone migration script

# Activate virtual environment
source .venv/bin/activate

# Run migration (dry-run first)
python scripts/migrate_paths.py --dry-run

# Execute migration
python scripts/migrate_paths.py --execute

# Rollback if needed
python scripts/migrate_paths.py --rollback
```

### Service URLs
- N/A (no web services)

### Required Environment Variables
- None required (script operates on file paths only)
- Optional: `RUGS_DATA_DIR` (for testing path configuration, but not needed for migration itself)

## Success Criteria

The task is complete when:

1. [ ] Migration script created at `scripts/migrate_paths.py`
2. [ ] Script successfully runs in dry-run mode showing all 63 planned replacements
3. [ ] Pre-flight checks validate directory structure
4. [ ] Backups created for all 22 files before modification
5. [ ] All 63 path references updated from `/home/nomad` to `/home/devops`
6. [ ] Post-migration verification confirms zero `/home/nomad` references remain
7. [ ] Rollback functionality tested and confirmed working
8. [ ] Comprehensive log file generated with audit trail
9. [ ] Script handles edge cases gracefully (permissions, encoding, etc.)
10. [ ] Documentation added to script with usage examples
11. [ ] No existing tests break (run pytest to verify)
12. [ ] Script follows project conventions (Ruff linting passes)

## QA Acceptance Criteria

**CRITICAL**: These criteria must be verified by the QA Agent before sign-off.

### Unit Tests
| Test | File | What to Verify |
|------|------|----------------|
| test_create_backup | `tests/test_migration.py` | Backup creation with timestamp |
| test_replace_in_file | `tests/test_migration.py` | Text replacement counting |
| test_verify_no_old_paths | `tests/test_migration.py` | Verification logic |
| test_rollback_restore | `tests/test_migration.py` | Rollback functionality |
| test_dry_run_mode | `tests/test_migration.py` | Dry-run doesn't modify files |

### Integration Tests
| Test | Services | What to Verify |
|------|----------|----------------|
| test_full_migration_workflow | main | Complete migration cycle: backup → replace → verify |
| test_rollback_workflow | main | Complete rollback cycle: detect backup → restore → verify |
| test_idempotency | main | Running migration twice produces same result |

### End-to-End Tests
| Flow | Steps | Expected Outcome |
|------|-------|------------------|
| Dry-run preview | 1. Run `--dry-run` 2. Check logs | Preview shows 63 replacements, no files modified |
| Full migration | 1. Run `--execute` 2. Verify files | All 22 files updated, backups created, logs complete |
| Rollback recovery | 1. Run `--rollback` 2. Verify files | All files restored to original state |

### Manual Verification
| Check | Command | Expected |
|-------|---------|----------|
| No old paths remain | `grep -r "/home/nomad" . --exclude-dir=.backups --exclude-dir=.git` | Zero matches (or only in backups) |
| Backup exists | `ls -la .backups/` | Directory with timestamped backup set |
| Log file created | `ls -la logs/` | Migration log with operations audit trail |
| Script executable | `python scripts/migrate_paths.py --help` | Help text displays correctly |

### Regression Testing
| Area | Test Command | Expected |
|------|--------------|----------|
| Existing tests pass | `cd src && ../.venv/bin/python -m pytest tests/ -v` | All existing tests remain passing |
| Linting passes | `ruff check scripts/migrate_paths.py` | No linting errors |
| Scripts still work | `python scripts/vectra_index.py --help` | Scripts function with new paths |

### QA Sign-off Requirements
- [ ] All unit tests pass (5 new tests for migration logic)
- [ ] All integration tests pass (3 workflow tests)
- [ ] All E2E tests pass (3 complete flows verified)
- [ ] Manual verification complete (grep confirms no old paths)
- [ ] Backup mechanism verified (files preserved correctly)
- [ ] Rollback mechanism verified (restore works correctly)
- [ ] Logs are comprehensive and clear
- [ ] Dry-run mode works without side effects
- [ ] No regressions in existing functionality (pytest suite passes)
- [ ] Code follows project conventions (Ruff linting passes)
- [ ] Script handles errors gracefully (tested with permission errors, invalid paths)
- [ ] Documentation in script is clear and complete

### Safety Verification
- [ ] Script never modifies files outside project directory
- [ ] Script never deletes files (only creates backups and replaces content)
- [ ] Script validates paths before operations
- [ ] Script provides clear error messages on failures
- [ ] Script exits cleanly on errors without partial state

---

**Generated**: 2026-01-03
**Spec Version**: 1.0
**Workflow Type**: feature
**Estimated Complexity**: Medium (single script with comprehensive safety mechanisms)
