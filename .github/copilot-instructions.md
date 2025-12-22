# GitHub Copilot Instructions for VECTRA-PLAYER

This file provides guidance for GitHub Copilot coding agent when working on issues and pull requests in the VECTRA-PLAYER repository.

## 🎯 Project Overview

VECTRA-PLAYER is a unified data architecture for game replay and live trading platform focused on:
- **DuckDB/Parquet** as canonical truth storage + **LanceDB** for vector search
- **Server-authoritative state** - Trust server in live mode
- **RAG integration** - LanceDB powers AI agents and Protocol Explorer UI
- **Event-driven architecture** - EventBus with EventStore persistence

**Core Principle:** Parquet is canonical truth; vector indexes are derived and rebuildable.

## 📋 Development Setup

### Prerequisites
- Python 3.11+ (3.11 and 3.12 are tested in CI)
- Git
- Linux/macOS (Windows with WSL)

### Initial Setup
```bash
# Clone and navigate to repository
cd /home/runner/work/VECTRA-PLAYER/VECTRA-PLAYER

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Set up data directory (environment variable)
export RUGS_DATA_DIR=~/rugs_data
mkdir -p $RUGS_DATA_DIR
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests from src directory
cd src && python -m pytest tests/ -v

# Run with coverage
cd src && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

# Run specific test file
cd src && python -m pytest tests/test_event_store.py -v

# Run specific test marker
cd src && python -m pytest tests/ -m unit -v

# With display (UI tests)
xvfb-run python -m pytest tests/ -v
```

### Test Requirements
- Minimum **60% code coverage** (configured in pyproject.toml)
- All new features must include unit tests
- Use existing test patterns in `src/tests/` as examples
- Test markers: `@pytest.mark.slow`, `@pytest.mark.integration`, `@pytest.mark.ui`, `@pytest.mark.unit`

### Test Structure
```
src/tests/
├── conftest.py              # Shared fixtures
├── test_core/               # Core event bus, state management tests
├── test_services/           # Event store, vector indexer tests
├── test_models/             # Data model tests
├── test_bot/                # Bot/ML component tests
├── test_ui/                 # UI component tests
└── test_integration/        # Integration tests
```

## 🔍 Code Quality & Linting

### Linting (Ruff)
```bash
# Check code style
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Format code
ruff format .
```

### Type Checking (MyPy)
```bash
# Run type checking (currently non-blocking during migration)
mypy src/
```

### Pre-commit Hooks
Pre-commit hooks automatically run on commit:
- Ruff linting with auto-fix
- Ruff formatting
- End-of-file fixer
- Trailing whitespace removal
- YAML/TOML validation
- Merge conflict detection
- Large file check (max 1MB)

To run manually:
```bash
pre-commit run --all-files
```

## 📝 Coding Standards

### Style Guide
- **Line length:** 100 characters (enforced by Ruff)
- **Quotes:** Double quotes for strings
- **Formatting:** Ruff format (black-compatible)
- **Import order:** isort via Ruff (first-party: core, services, ui, bot, models, sources)
- **Type hints:** Gradually adding (not strictly enforced yet)

### Project-Specific Conventions
1. **Event-driven architecture:**
   - All data producers publish to EventBus
   - EventStore is the **single writer** to Parquet
   - No direct filesystem writes outside EventStore
   
2. **Data directory:**
   - Use `RUGS_DATA_DIR` environment variable
   - Never hardcode paths like `/home/nomad/...`
   - All data under `~/rugs_data/` structure
   
3. **Event schema:**
   - Follow unified event schema in `services/event_store/schema.py`
   - Common envelope: `ts`, `source`, `doc_type`, `session_id`, `seq`, `direction`, `raw_json`
   - Doc types: `ws_event`, `game_tick`, `player_action`, `server_state`, `system_event`

4. **No legacy patterns:**
   - Don't add duplicate capture directories
   - Don't write directly to filesystem except via EventStore
   - Tests should enforce EventStore as sole writer

### File Organization
```
VECTRA-PLAYER/
├── src/
│   ├── core/              # Event bus, state management
│   ├── services/          # Event store, vector indexer, WebSocket
│   ├── ui/                # UI components
│   ├── bot/               # Bot/ML components
│   ├── models/            # Data models
│   ├── sources/           # Data sources
│   ├── utils/             # Utilities
│   └── tests/             # Test suite
├── docs/                  # Documentation
├── .github/               # GitHub workflows, templates
└── pyproject.toml         # Project configuration
```

## 🔒 Security

### Security Scanning
- **CodeQL:** Deep semantic analysis (runs on push, PR, weekly)
- **Dependency Review:** Reviews dependency changes in PRs
- **Bandit:** Python security linting (included in quality checks)

### Security Requirements
- All dependencies checked with CodeQL
- No hardcoded secrets or credentials
- Sanitize user inputs
- Follow Python security best practices
- Run security workflow before merging

### Running Security Checks
Security checks run automatically in CI, but for local verification:
```bash
# Install bandit
pip install bandit

# Run bandit security check
bandit -r src/ -ll
```

## 🚀 Building and Running

### Running the Application
```bash
# Launch via script
./run.sh

# Or directly
python src/main.py
```

### Environment Variables
- `RUGS_DATA_DIR`: Data directory path (default: `~/rugs_data`)
- Export in shell or add to `.env` file

## 🔄 Pull Request Process

### Before Creating PR
1. **Run tests locally:** `cd src && pytest tests/ -v`
2. **Check linting:** `ruff check . && ruff format --check .`
3. **Run pre-commit:** `pre-commit run --all-files`
4. **Verify coverage:** Ensure new code has tests

### CI/CD Checks
All PRs must pass:
- ✅ **CI (pytest):** Tests on Python 3.11 and 3.12
- ✅ **Quality (ruff):** Linting and formatting
- ✅ **Security (CodeQL):** Security scanning
- ✅ **Coverage:** Minimum 60% code coverage
- ✅ **PR Labeler:** Automatic labels based on changes

### Commit Convention
Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks
- `ci:` CI/CD changes
- `perf:` Performance improvements

Examples:
```bash
git commit -m "feat: add DuckDB query optimization"
git commit -m "fix: resolve EventStore race condition"
git commit -m "test: add vector indexer unit tests"
git commit -m "docs: update WebSocket events spec"
```

## 🐛 Common Issues and Solutions

### Issue: Tests fail with `ModuleNotFoundError`
**Solution:** Ensure you're in the `src/` directory when running pytest:
```bash
cd src && pytest tests/ -v
```

### Issue: Pre-commit hooks fail
**Solution:** Run auto-fixes, then commit:
```bash
pre-commit run --all-files
git add .
git commit
```

### Issue: Type errors with MyPy
**Solution:** MyPy is currently non-blocking during migration. Type errors are warnings, not failures.

### Issue: Coverage too low
**Solution:** Add tests for new code. Check coverage report:
```bash
cd src && pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Issue: Import errors or path issues
**Solution:** 
- Use absolute imports from src directory
- pythonpath is set to `["src"]` in pyproject.toml
- Install in editable mode: `pip install -e ".[dev]"`

## 📚 Key Documentation

- **[README.md](../README.md):** Project overview and quick start
- **[CLAUDE.md](../CLAUDE.md):** AI assistant development context
- **[CI_CD_GUIDE.md](../docs/CI_CD_GUIDE.md):** Detailed CI/CD documentation
- **[ONBOARDING.md](../docs/ONBOARDING.md):** Developer onboarding checklist
- **[WEBSOCKET_EVENTS_SPEC.md](../docs/specs/WEBSOCKET_EVENTS_SPEC.md):** Event schema reference

## 🎯 Task Priorities

When working on issues:

1. **Understand the context:** Review related code and documentation
2. **Write tests first:** TDD approach preferred
3. **Make minimal changes:** Surgical, focused modifications
4. **Follow conventions:** Match existing code style and patterns
5. **Update documentation:** Keep docs in sync with code changes
6. **Run all checks:** Tests, linting, security before PR
7. **Clear commit messages:** Use conventional commits format

## ⚠️ Things to Avoid

- ❌ Don't hardcode paths like `/home/nomad/...`
- ❌ Don't write directly to filesystem except via EventStore
- ❌ Don't create duplicate capture directories
- ❌ Don't skip writing tests for new features
- ❌ Don't ignore linting errors
- ❌ Don't commit secrets or credentials
- ❌ Don't modify code in `deprecated/` or `external/` directories
- ❌ Don't remove or disable existing tests without good reason
- ❌ Don't make breaking changes without discussing first

## 🔧 Advanced Topics

### Vector Indexing (LanceDB)
```bash
# Rebuild vector index from Parquet
vectra-player index build --full

# Incremental index update
vectra-player index build --incremental

# Query the index
vectra-player index query "What fields are in playerUpdate?"
```

### DuckDB Queries
```python
import duckdb
conn = duckdb.connect()
df = conn.execute("""
    SELECT * FROM '~/rugs_data/events_parquet/**/*.parquet'
    WHERE doc_type = 'ws_event'
    LIMIT 10
""").df()
```

### EventStore Usage
```python
from services.event_store.writer import EventStoreWriter
from services.event_store.schema import WSEvent

# Publish events via EventBus
event_bus.publish(Events.WS_RAW_EVENT, event_data)

# EventStore subscribes and persists automatically
```

## 🤝 Need Help?

- **Documentation:** Check `docs/` directory
- **Issues:** [GitHub Issues](https://github.com/Dutchthenomad/VECTRA-PLAYER/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Dutchthenomad/VECTRA-PLAYER/discussions)
- **Code Owner:** @Dutchthenomad

---

**Remember:** Make small, focused changes. Test thoroughly. Follow existing patterns. Keep documentation updated.
