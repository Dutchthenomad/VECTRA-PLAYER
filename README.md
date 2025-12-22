# VECTRA-PLAYER

[![CI](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/ci.yml/badge.svg)](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/ci.yml)
[![Quality](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/quality.yml/badge.svg)](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/quality.yml)
[![Security](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/security.yml/badge.svg)](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/security.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Unified Data Architecture for Rugs.fun** - Game replay and live trading platform with DuckDB/Parquet storage and LanceDB vector search.

---

## 🚀 Features

- **📊 Unified Data Storage**: DuckDB/Parquet as canonical truth + LanceDB for vectors
- **🎮 Server-Authoritative State**: Trust server in live mode, eliminate local calculations
- **🤖 RAG Integration**: LanceDB powers `rugs-expert` agent and Protocol Explorer UI
- **🔍 WebSocket Event Capture**: Real-time event recording and replay
- **📈 Live Trading**: Monitor and interact with live game sessions
- **🧪 Testing & Quality**: Comprehensive test suite with 60%+ coverage
- **🔒 Security**: CodeQL scanning, Dependabot, and automated security reviews

---

## 📋 Quick Start

### Prerequisites

- Python 3.11 or higher
- Git
- Linux/macOS (Windows with WSL)

### Installation

```bash
# Clone the repository
git clone https://github.com/Dutchthenomad/VECTRA-PLAYER.git
cd VECTRA-PLAYER

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Set up data directory
export RUGS_DATA_DIR=~/rugs_data
mkdir -p $RUGS_DATA_DIR
```

### Running

```bash
# Launch the application
./run.sh

# Or directly
python src/main.py
```

### Testing

```bash
# Run all tests
cd src && pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test
pytest tests/test_event_store.py -v
```

---

## 🏗️ Architecture

```
~/rugs_data/                          # RUGS_DATA_DIR (env var)
├── events_parquet/                   # Canonical truth store
│   ├── doc_type=ws_event/
│   ├── doc_type=game_tick/
│   └── doc_type=player_action/
├── vectors/                          # Derived LanceDB index
│   └── events.lance/
├── exports/                          # Optional JSONL exports
└── manifests/
    └── schema_version.json
```

**Core Principle:** Parquet is canonical truth; vector indexes are derived and rebuildable.

---

## 🔧 Development

### Code Quality

```bash
# Linting and formatting
ruff check .
ruff format .

# Type checking
mypy src/

# Run pre-commit hooks
pre-commit run --all-files
```

### Project Structure

```
VECTRA-PLAYER/
├── src/
│   ├── core/              # Event bus, state management
│   ├── services/          # Event store, vector indexer
│   ├── ui/                # UI components
│   ├── bot/               # Bot/ML components
│   └── tests/             # Test suite
├── docs/                  # Documentation
│   ├── CI_CD_GUIDE.md    # CI/CD and automation guide
│   └── specs/             # Technical specifications
├── .github/
│   ├── workflows/         # GitHub Actions
│   └── CODEOWNERS        # Automatic reviewer assignment
└── pyproject.toml        # Project configuration
```

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Run tests**: `cd src && pytest tests/ -v`
5. **Run quality checks**: `ruff check --fix . && ruff format .`
6. **Commit your changes**: `git commit -m 'feat: Add amazing feature'`
7. **Push to the branch**: `git push origin feature/amazing-feature`
8. **Open a Pull Request**

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

### Pull Request Process

1. Fill out the PR template completely
2. Ensure all CI checks pass
3. Address automated review comments
4. Wait for code owner review
5. Respond to feedback
6. Merge when approved

**See [CI/CD Guide](docs/CI_CD_GUIDE.md) for detailed information on automated workflows.**

---

## 🔐 Security

Security is a top priority. We use multiple layers of protection:

- **CodeQL**: Deep semantic analysis for vulnerabilities
- **Dependabot**: Automatic dependency updates
- **Bandit**: Python-specific security linting
- **Trivy**: Container and filesystem scanning
- **Automated Security Reviews**: Every PR is scanned

### Reporting Vulnerabilities

Please report security vulnerabilities to [@Dutchthenomad](https://github.com/Dutchthenomad) directly. Do not open public issues for security concerns.

---

## 📚 Documentation

- **[CI/CD Guide](docs/CI_CD_GUIDE.md)**: Complete guide to automated workflows
- **[WebSocket Events Spec](docs/specs/WEBSOCKET_EVENTS_SPEC.md)**: Event schema documentation
- **[CLAUDE.md](CLAUDE.md)**: Claude AI development context

---

## 🔗 Related Projects

- **[claude-flow](https://github.com/Dutchthenomad/claude-flow)**: Development orchestration layer
- **[rugs-rl-bot](https://github.com/Dutchthenomad/rugs-rl-bot)**: RL training and ML models
- **REPLAYER**: Production system (predecessor)

---

## 📊 Project Status

**Current Phase:** Phase 12 - Unified Data Architecture

### Completed
- ✅ Core event capture and replay
- ✅ DuckDB/Parquet storage design
- ✅ LanceDB vector integration
- ✅ Comprehensive CI/CD pipeline
- ✅ Automated code review system

### In Progress
- 🔄 Migration from legacy storage
- 🔄 Server-authoritative state implementation
- 🔄 Protocol Explorer UI
- 🔄 RAG integration completion

### Planned
- 📋 Full production deployment
- 📋 Performance optimization
- 📋 Extended ML capabilities

---

## 🎯 Roadmap

See our [GitHub Issues](https://github.com/Dutchthenomad/VECTRA-PLAYER/issues) for detailed roadmap and feature requests.

---

## 📈 Statistics

- **Test Coverage**: 60%+ (target: 70%)
- **Code Quality**: Ruff + MyPy enforced
- **Security**: CodeQL + Dependabot enabled
- **CI/CD**: 9 automated workflows
- **Python Support**: 3.11, 3.12

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Dutchthenomad** - *Initial work* - [@Dutchthenomad](https://github.com/Dutchthenomad)

---

## 🙏 Acknowledgments

- Built with [DuckDB](https://duckdb.org/) and [LanceDB](https://lancedb.com/)
- CI/CD powered by [GitHub Actions](https://github.com/features/actions)
- Code quality by [Ruff](https://github.com/astral-sh/ruff)
- AI assistance by [Claude](https://claude.ai/) and [GitHub Copilot](https://github.com/features/copilot)

---

## 📞 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/Dutchthenomad/VECTRA-PLAYER/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Dutchthenomad/VECTRA-PLAYER/discussions)

---

**⭐ Star this repo if you find it helpful!**

---

*Last updated: December 22, 2025*
