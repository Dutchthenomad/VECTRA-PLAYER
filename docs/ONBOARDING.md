# Developer Onboarding Checklist

Welcome to VECTRA-PLAYER! This checklist will help you get set up and productive quickly.

## 🎯 Getting Started

### Environment Setup
- [ ] **Fork and clone the repository**
  ```bash
  git clone https://github.com/YOUR_USERNAME/VECTRA-PLAYER.git
  cd VECTRA-PLAYER
  ```

- [ ] **Set up Python virtual environment**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate  # Windows: .venv\Scripts\activate
  ```

- [ ] **Install dependencies**
  ```bash
  pip install -e ".[dev]"
  ```

- [ ] **Configure data directory**
  ```bash
  export RUGS_DATA_DIR=~/rugs_data
  mkdir -p $RUGS_DATA_DIR
  # Add to ~/.bashrc or ~/.zshrc for persistence
  ```

- [ ] **Install pre-commit hooks**
  ```bash
  pre-commit install
  ```

- [ ] **Verify installation**
  ```bash
  python src/main.py --help
  ```

### IDE Setup
- [ ] **Install recommended extensions**
  - VS Code: Ruff, Python, GitHub Pull Requests
  - PyCharm: Configure Ruff as external tool

- [ ] **Configure formatting on save**
  - VS Code: See docs/CI_CD_GUIDE.md
  - PyCharm: Settings → Tools → External Tools

- [ ] **Set up debugging**
  - Create launch configuration for src/main.py
  - Configure breakpoints

## 📚 Learning the Codebase

### Documentation Review
- [ ] **Read README.md** - Project overview and quick start
- [ ] **Read CLAUDE.md** - Project architecture and philosophy
- [ ] **Read docs/CI_CD_GUIDE.md** - CI/CD workflows and automation
- [ ] **Read docs/QUICK_REFERENCE.md** - Quick commands and tips
- [ ] **Browse docs/specs/** - Technical specifications

### Code Exploration
- [ ] **Understand project structure**
  ```
  src/
  ├── core/        # Event bus, state management
  ├── services/    # Event store, vector indexer  
  ├── ui/          # UI components
  ├── bot/         # Bot/ML components
  └── tests/       # Test suite
  ```

- [ ] **Run the application**
  ```bash
  ./run.sh
  # Explore the UI and features
  ```

- [ ] **Run tests**
  ```bash
  cd src
  pytest tests/ -v
  ```

- [ ] **Review key files**
  - [ ] `src/core/event_bus.py` - Event system
  - [ ] `src/services/event_store/` - Data persistence
  - [ ] `pyproject.toml` - Configuration and dependencies
  - [ ] `.github/workflows/` - CI/CD pipelines

## 🧪 Testing Your Setup

### Run Quality Checks
- [ ] **Linting**
  ```bash
  ruff check .
  ```

- [ ] **Formatting**
  ```bash
  ruff format .
  ```

- [ ] **Type checking**
  ```bash
  mypy src/
  ```

- [ ] **Pre-commit hooks**
  ```bash
  pre-commit run --all-files
  ```

### Run Tests
- [ ] **Unit tests**
  ```bash
  cd src
  pytest tests/ -v -m unit
  ```

- [ ] **Integration tests**
  ```bash
  pytest tests/ -v -m integration
  ```

- [ ] **Coverage report**
  ```bash
  pytest tests/ --cov=. --cov-report=html
  open htmlcov/index.html
  ```

### Test CI/CD Locally
- [ ] **Create a test branch**
  ```bash
  git checkout -b test/setup-verification
  ```

- [ ] **Make a trivial change**
  ```bash
  echo "# Test" >> docs/test.md
  git add docs/test.md
  git commit -m "test: verify CI/CD setup"
  ```

- [ ] **Push and create draft PR**
  ```bash
  git push origin test/setup-verification
  # Create draft PR on GitHub
  ```

- [ ] **Verify all workflows run**
  - Check Actions tab
  - Verify automated labels are applied
  - Review bot comments

- [ ] **Close test PR**

## 🤝 Making Your First Contribution

### Choose an Issue
- [ ] **Browse issues labeled "good first issue"**
- [ ] **Comment on issue to claim it**
- [ ] **Ask questions if anything is unclear**

### Development Workflow
- [ ] **Create feature branch**
  ```bash
  git checkout -b feature/your-feature-name
  ```

- [ ] **Make changes**
  - Write code
  - Add tests
  - Update documentation

- [ ] **Test locally**
  ```bash
  cd src && pytest tests/ -v
  ruff check --fix .
  ruff format .
  ```

- [ ] **Commit with conventional commits**
  ```bash
  git commit -m "feat: add your feature"
  # or
  git commit -m "fix: resolve issue"
  ```

- [ ] **Push and create PR**
  ```bash
  git push origin feature/your-feature-name
  # Create PR on GitHub
  ```

### PR Process
- [ ] **Fill out PR template completely**
- [ ] **Link related issues**
- [ ] **Wait for automated checks**
- [ ] **Address feedback from bots**
- [ ] **Request review from @Dutchthenomad**
- [ ] **Respond to review comments**
- [ ] **Merge when approved**

## 🎓 Advanced Topics

### Vector Indexing
- [ ] **Learn LanceDB basics**
  - Read docs/specs/WEBSOCKET_EVENTS_SPEC.md
  - Understand vector embedding process

- [ ] **Test vector queries**
  ```bash
  vectra-player index query "test query"
  ```

### Event Store
- [ ] **Understand Parquet schema**
  - Review src/services/event_store/schema.py
  - Query with DuckDB

- [ ] **Test event capture**
  ```bash
  # Start capture in UI
  # Generate some events
  # Verify in ~/rugs_data/events_parquet/
  ```

### Bot/ML Components
- [ ] **Review RL bot integration**
  - See related rugs-rl-bot repository
  - Understand model interfaces

## 🔧 Troubleshooting

### Common Issues

**Import errors:**
```bash
# Reinstall in editable mode
pip install -e ".[dev]"
```

**Tkinter errors:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-tk

# macOS
brew install python-tk
```

**Test failures:**
```bash
# Run with xvfb for UI tests
xvfb-run pytest tests/ -v
```

**Permission errors:**
```bash
# Ensure data directory is writable
chmod -R 755 ~/rugs_data
```

## 📞 Getting Help

- [ ] **Join discussions on GitHub**
- [ ] **Review existing issues and PRs**
- [ ] **Ask in PR comments with @Dutchthenomad**
- [ ] **Check docs/ directory for detailed guides**

## ✅ Completion

Once you've completed this checklist:

- [ ] **You understand the project architecture**
- [ ] **You can run and test the application**
- [ ] **You can make contributions following the workflow**
- [ ] **You know where to find documentation and help**
- [ ] **You're ready to tackle your first issue!**

## 🎉 Next Steps

- Browse issues for areas that interest you
- Join discussions to share ideas
- Help improve documentation
- Consider adding tests or examples
- Share your experience to help improve this onboarding

---

**Welcome to the team! Happy coding! 🚀**

If you have suggestions for improving this checklist, please submit a PR!
