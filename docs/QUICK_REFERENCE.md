# GitHub Automation Quick Reference

## 🚀 Quick Commands

### Local Development
```bash
# Run all quality checks
ruff check --fix . && ruff format . && mypy src/

# Run tests with coverage
cd src && pytest tests/ --cov=. --cov-report=html -v

# Install pre-commit hooks
pre-commit install && pre-commit run --all-files

# Check security locally
pip install bandit && bandit -r src/ -ll
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/your-feature

# Commit with conventional commits
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
git commit -m "docs: update documentation"

# Push and create PR
git push origin feature/your-feature
# Then create PR on GitHub
```

## 📋 Workflows Cheat Sheet

| Workflow | Trigger | What It Does | Time |
|----------|---------|--------------|------|
| **CI** | Push, PR | Run tests on Py 3.11 & 3.12 | ~3 min |
| **Quality** | Push, PR | Lint (ruff), format, type check (mypy) | ~1 min |
| **Security** | Push, PR, Weekly | CodeQL, dependency review | ~5 min |
| **Code Review** | PR | Complexity, coverage, security analysis | ~4 min |
| **Coverage** | Push, PR | Detailed coverage report + badge | ~3 min |
| **PR Labeler** | PR | Auto-label by changes and title | ~30 sec |
| **Guardrails** | PR | Pattern enforcement (hardcoded paths) | ~30 sec |
| **Release** | Tag v*.*.* | Create release with changelog | ~2 min |
| **Claude** | @claude mention | AI code assistance | Variable |

## 🏷️ PR Labels Reference

### Automatic Labels (by file changes)
- `area: core` - Changes to src/core/
- `area: services` - Changes to src/services/
- `area: ui` - Changes to src/ui/
- `area: tests` - Changes to src/tests/
- `area: ci/cd` - Changes to .github/workflows/
- `documentation` - Changes to docs/ or .md files
- `dependencies` - Changes to requirements or pyproject.toml

### Size Labels
- `size/xs` - < 10 lines
- `size/s` - 10-100 lines
- `size/m` - 100-500 lines
- `size/l` - 500-1000 lines
- `size/xl` - > 1000 lines (consider splitting!)

### Type Labels (by PR title)
- `bug` - Title contains "fix" or "bug"
- `enhancement` - Title contains "feat" or "feature"
- `documentation` - Title contains "docs"
- `testing` - Title contains "test"
- `refactoring` - Title contains "refactor"
- `performance` - Title contains "perf"
- `security` - Title contains "security"
- `breaking-change` - Title contains "breaking"

## 🔍 Status Checks Required

### Must Pass (blocking)
- ✅ CI / pytest (3.11)
- ✅ CI / pytest (3.12)
- ✅ Quality / ruff
- ✅ Security / codeql

### Non-blocking (informational)
- ℹ️ Quality / mypy (during migration)
- ℹ️ Code Review / complexity
- ℹ️ Code Review / coverage
- ℹ️ Code Review / security scan

## 🎯 Common Scenarios

### Scenario 1: Create a new feature
```bash
1. git checkout -b feature/vector-search
2. # Make changes
3. cd src && pytest tests/ -v  # Test locally
4. ruff check --fix . && ruff format .  # Format
5. git commit -m "feat: add vector search capability"
6. git push origin feature/vector-search
7. # Create PR on GitHub
8. # Wait for automated reviews
9. # Address feedback
10. # Get approval & merge
```

### Scenario 2: Fix a bug
```bash
1. git checkout -b fix/event-store-race-condition
2. # Make fixes
3. cd src && pytest tests/test_event_store.py -v
4. git commit -m "fix: resolve race condition in event store"
5. git push origin fix/event-store-race-condition
6. # Create PR with "Closes #123" in description
```

### Scenario 3: Update documentation
```bash
1. git checkout -b docs/update-ci-guide
2. # Edit docs/
3. git commit -m "docs: clarify CI/CD workflow steps"
4. git push origin docs/update-ci-guide
5. # PR will auto-label as "documentation"
6. # No tests required, quick review
```

### Scenario 4: Release new version
```bash
1. # Ensure main branch is ready
2. git tag -a v0.13.0 -m "Release v0.13.0"
3. git push origin v0.13.0
4. # Workflow auto-creates release with changelog
5. # Download artifacts from Actions tab
```

## ⚠️ Troubleshooting Quick Fixes

### Tests Failing
```bash
# Run specific test
cd src && pytest tests/test_file.py::test_function -v

# Run with verbose output
pytest tests/ -vv --tb=long

# Run with UI tests
xvfb-run pytest tests/ -v
```

### Linting Errors
```bash
# Auto-fix most issues
ruff check --fix .

# Format code
ruff format .

# Check what's wrong
ruff check . --show-fixes
```

### Type Errors
```bash
# Check types
mypy src/

# Note: Currently non-blocking
# See TODO(#1) in pyproject.toml
```

### Coverage Too Low
```bash
# See what's not covered
cd src && pytest tests/ --cov=. --cov-report=term-missing

# Focus on your changes
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

### Security Alert
```bash
# Check locally with Bandit
pip install bandit
bandit -r src/ -ll

# Fix or dismiss in GitHub Security tab
```

### Merge Conflicts
```bash
# Update your branch
git fetch origin
git rebase origin/main

# Resolve conflicts
# git add <resolved-files>
# git rebase --continue

# Force push (if needed)
git push --force-with-lease
```

## 🔐 Required Secrets

Configure in: Settings → Secrets and variables → Actions

| Secret | Purpose | Optional? |
|--------|---------|-----------|
| `ANTHROPIC_API_KEY` | Claude AI integration | Yes |
| `CODECOV_TOKEN` | Coverage reporting | Yes |

## 📊 Metrics Targets

| Metric | Target | Current |
|--------|--------|---------|
| Test Coverage | ≥70% | ~60% |
| Cyclomatic Complexity | <10 per function | Varies |
| PR Review Time | <24 hours | - |
| CI/CD Duration | <10 minutes | ~5 min |

## 🎨 Conventional Commit Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat: add ChromaDB integration` |
| `fix` | Bug fix | `fix: resolve memory leak` |
| `docs` | Documentation | `docs: update API reference` |
| `style` | Formatting | `style: fix indentation` |
| `refactor` | Code restructuring | `refactor: simplify event bus` |
| `perf` | Performance | `perf: optimize query speed` |
| `test` | Tests | `test: add event store tests` |
| `chore` | Maintenance | `chore: update dependencies` |
| `ci` | CI/CD changes | `ci: add coverage workflow` |
| `build` | Build system | `build: update pyproject.toml` |

### With Scope
```bash
feat(core): add event filtering
fix(ui): resolve layout issue
docs(ci): update workflow guide
```

### Breaking Changes
```bash
feat!: change event schema (breaking)
# Or
feat(api)!: redesign REST endpoints
```

## 🔗 Useful Links

- **Actions**: https://github.com/Dutchthenomad/VECTRA-PLAYER/actions
- **Security**: https://github.com/Dutchthenomad/VECTRA-PLAYER/security
- **Issues**: https://github.com/Dutchthenomad/VECTRA-PLAYER/issues
- **PRs**: https://github.com/Dutchthenomad/VECTRA-PLAYER/pulls

## 💡 Pro Tips

1. **Use draft PRs** for work-in-progress
2. **Link issues** with "Closes #123" in PR description
3. **Small commits** are easier to review
4. **Test locally** before pushing
5. **Run pre-commit** hooks before committing
6. **Check Actions** tab for failures
7. **Read bot comments** - they're helpful!
8. **Ask for help** with @Dutchthenomad
9. **Update docs** when changing workflows
10. **Celebrate** when CI passes! 🎉

---

*For detailed information, see [CI_CD_GUIDE.md](CI_CD_GUIDE.md)*
