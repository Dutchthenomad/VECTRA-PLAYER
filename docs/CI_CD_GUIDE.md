# CI/CD and Automated Code Review Guide

This guide explains the automated workflows, code review processes, and CI/CD pipeline configured for VECTRA-PLAYER.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Automated Workflows](#automated-workflows)
3. [Pull Request Process](#pull-request-process)
4. [Code Review Automation](#code-review-automation)
5. [Security Scanning](#security-scanning)
6. [Test Coverage](#test-coverage)
7. [Release Process](#release-process)
8. [Troubleshooting](#troubleshooting)
9. [Configuration](#configuration)

---

## Overview

VECTRA-PLAYER uses GitHub Actions for continuous integration, automated code review, security scanning, and deployment automation. Every push and pull request triggers multiple checks to ensure code quality, security, and functionality.

### Key Features

- ✅ **Automatic code review** with complexity analysis
- ✅ **Security scanning** with CodeQL, Trivy, and Bandit
- ✅ **Test coverage reporting** with Codecov integration
- ✅ **Automated PR labeling** based on changes
- ✅ **Dependency updates** via Dependabot
- ✅ **Release automation** with changelog generation
- ✅ **Pre-commit hooks** for local validation

---

## Automated Workflows

### 1. CI Workflow (`ci.yml`)

**Triggers:** Push to main, Pull requests
**Purpose:** Run tests across Python versions

```bash
# What it does:
- Runs pytest with coverage on Python 3.11 and 3.12
- Uploads coverage reports
- Fails if tests fail
```

**Status Badge:** [![CI](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/ci.yml/badge.svg)](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/ci.yml)

### 2. Quality Workflow (`quality.yml`)

**Triggers:** Push to main, Pull requests
**Purpose:** Code quality checks

```bash
# What it does:
- Runs ruff linter
- Runs ruff formatter (check mode)
- Runs mypy type checking (non-blocking during migration)
```

### 3. Security Workflow (`security.yml`)

**Triggers:** Push to main, Pull requests, Weekly schedule, Manual
**Purpose:** Security vulnerability scanning

```bash
# What it does:
- CodeQL analysis for Python
- Dependency review for PRs
- Scheduled scans for new vulnerabilities
```

### 4. Code Review Workflow (`code-review.yml`) ⭐ NEW

**Triggers:** Pull requests
**Purpose:** Automated code review with multiple analyses

```bash
# What it does:
- Complexity analysis (Radon, Lizard)
- Test coverage reporting
- Security scanning (Trivy, Bandit)
- Change summary generation
- Automatic PR comments with findings
```

### 5. Coverage Workflow (`coverage.yml`) ⭐ NEW

**Triggers:** Push to main, Pull requests
**Purpose:** Detailed test coverage reporting

```bash
# What it does:
- Generates coverage reports (XML, HTML, terminal)
- Uploads to Codecov
- Creates coverage badge
- Comments coverage summary on PRs
```

### 6. PR Labeler (`pr-labeler.yml`) ⭐ NEW

**Triggers:** PR opened, edited, synchronized
**Purpose:** Automatic PR categorization

```bash
# What it does:
- Labels by file changes (area: core, area: ui, etc.)
- Labels by PR size (size/xs, size/s, size/m, size/l, size/xl)
- Labels by PR title (bug, enhancement, documentation, etc.)
- Warns on very large PRs
```

### 7. Release Workflow (`release.yml`) ⭐ NEW

**Triggers:** Version tags (v*.*.*), Manual
**Purpose:** Automated release creation

```bash
# What it does:
- Generates changelog from PRs
- Creates GitHub release
- Builds distribution packages
- Notifies via issue
```

### 8. Guardrails Workflow (`guardrails.yml`)

**Triggers:** Pull requests
**Purpose:** Enforce project-specific rules

```bash
# What it does:
- Prevents hardcoded /home/nomad paths
- Warns on TODOs without issue references
- Future: Prevent direct file writes outside EventStore
```

### 9. Claude AI Integration (`claude.yml`)

**Triggers:** Issue/PR comments with @claude
**Purpose:** AI-assisted code review and development

---

## Pull Request Process

### Step 1: Create PR

When you create a PR, use the template that auto-populates:

1. Fill in the description
2. Select the type of change
3. Link related issues
4. Describe testing performed
5. Check all relevant boxes

### Step 2: Automatic Checks Start

Within seconds, multiple workflows begin:

```
┌─────────────────────────────────────┐
│  PR Created                         │
└──────────┬──────────────────────────┘
           │
           ├─→ PR Labeler (adds labels)
           ├─→ CI (runs tests)
           ├─→ Quality (linting, formatting)
           ├─→ Security (CodeQL, dependency review)
           ├─→ Code Review (complexity, coverage, security)
           ├─→ Coverage (detailed reports)
           └─→ Guardrails (pattern enforcement)
```

### Step 3: Review Bot Comments

Within minutes, automated comments appear:

- **📊 Change Summary**: File counts, areas affected, warnings
- **🔍 Complexity Analysis**: Cyclomatic complexity, maintainability index
- **📈 Coverage Report**: Line/branch coverage with diff
- **🔒 Security Scan**: Vulnerability findings from Bandit/Trivy

### Step 4: Address Feedback

Review the automated comments and address any issues:

```bash
# Fix linting issues
ruff check --fix .
ruff format .

# Fix type errors (if any)
mypy src/

# Run tests locally
cd src && pytest tests/ -v

# Check security locally
pip install bandit
bandit -r src/
```

### Step 5: Code Owner Review

CODEOWNERS file ensures the right people review:

- All changes: @Dutchthenomad
- Critical areas (event_store, core): Additional scrutiny
- Security files: Extra review required

### Step 6: Merge

Once all checks pass and reviews are approved:

1. ✅ All status checks pass
2. ✅ Required reviews obtained
3. ✅ No merge conflicts
4. → Merge PR (squash or merge commit)

---

## Code Review Automation

### Qodo RAG Context Enrichment 💎

**Tool:** Qodo PR Agent with RAG (Retrieval-Augmented Generation)
**Status:** Enabled for enterprise users

**What it does:**
- Enhances AI analysis by retrieving relevant code patterns from the project
- Provides context-aware insights during code reviews
- References similar code from your codebase when making suggestions

**Available Commands:**
- `/ask` - Answer questions with broader repository context
- `/compliance` - Check compliance with repository patterns
- `/implement` - Implement features following existing patterns
- `/review` - Code review with context-aware insights

**Configuration:** `.pr-agent.toml`

```toml
[rag_arguments]
enable_rag=true
```

**How it works:**
1. Qodo indexes your repository's codebase
2. During PR review, it searches for relevant code patterns
3. AI uses these patterns to provide context-aware suggestions
4. References section shows the code consulted

**Prerequisites:**
- Qodo enterprise plan with single tenant or on-premises setup
- Database setup and codebase indexing (contact Qodo support)

### Complexity Analysis

**Tool:** Radon + Lizard
**Threshold:** CC > 10 is flagged

```python
# Example report:
src/core/event_bus.py
    M 150:4 EventBus.publish - B (7)  # OK
    M 200:4 EventBus._process_queue - D (15)  # High complexity!
```

**What to do:**
- CC < 10: Good
- CC 10-20: Consider refactoring
- CC > 20: Definitely refactor

### Test Coverage

**Tool:** pytest-cov + Codecov
**Targets:**
- Green: ≥70%
- Orange: 50-70%
- Red: <50%

**What to check:**
- Overall coverage percentage
- Coverage diff (change in coverage)
- Uncovered lines in your changes

### Security Scanning

**Tools:**
- **CodeQL**: Deep semantic analysis
- **Trivy**: Dependency vulnerabilities
- **Bandit**: Python-specific security issues

**Common findings:**
- Hardcoded secrets (ban immediately)
- SQL injection risks
- Command injection
- Insecure random number generation
- Unsafe deserialization

### PR Size Guidelines

Automatic labels help manage PR size:

- **size/xs** (<10 lines): Quick review
- **size/s** (10-100 lines): Normal review
- **size/m** (100-500 lines): Thorough review needed
- **size/l** (500-1000 lines): Consider splitting
- **size/xl** (>1000 lines): Should be split into smaller PRs

---

## Security Scanning

### CodeQL

**Schedule:** Every PR + weekly scans

```yaml
# What it checks:
- SQL injection
- Cross-site scripting
- Command injection
- Path traversal
- Insecure deserialization
- Hardcoded credentials
```

**View results:** Security tab → Code scanning alerts

### Dependency Scanning

**Tool:** Dependabot + Dependency Review

```yaml
# What it monitors:
- Known CVEs in dependencies
- Security advisories
- License compliance
- Outdated packages
```

**Auto-updates:** Dependabot opens PRs for updates

### Bandit

**Type:** Python-specific security linter

```bash
# Run locally:
pip install bandit[toml]
bandit -r src/ -ll  # Only high/medium severity
```

### Trivy

**Type:** Comprehensive vulnerability scanner

```bash
# Run locally:
docker run --rm -v $(pwd):/src aquasecurity/trivy fs /src
```

---

## Test Coverage

### Local Coverage

```bash
# Generate coverage report
cd src
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### CI Coverage

Every PR gets:
1. **Coverage comment** on PR with diff
2. **Codecov report** with detailed analysis
3. **HTML report artifact** (downloadable)

### Coverage Badge

Main branch gets an auto-updated badge:

![Coverage](./coverage-badge.svg)

Add to README:
```markdown
![Coverage](https://img.shields.io/badge/coverage-XX%25-green)
```

---

## Release Process

### Semantic Versioning

Follow [SemVer](https://semver.org/):

- **Major** (v1.0.0): Breaking changes
- **Minor** (v0.1.0): New features, backward compatible
- **Patch** (v0.0.1): Bug fixes

### Creating a Release

#### Option 1: Tag-based (Recommended)

```bash
# Create and push tag
git tag -a v0.12.1 -m "Release v0.12.1"
git push origin v0.12.1

# Workflow automatically:
# 1. Generates changelog
# 2. Creates GitHub release
# 3. Builds artifacts
# 4. Notifies team
```

#### Option 2: Manual Trigger

1. Go to Actions → Release Automation
2. Click "Run workflow"
3. Enter version (e.g., v0.12.1)
4. Click "Run workflow"

### Changelog Generation

Automatic changelog from PR labels:

```markdown
## 🚀 Features
- Add vector indexing by @user in #123

## 🐛 Bug Fixes
- Fix event store race condition by @user in #124

## 📝 Documentation
- Update CI/CD guide by @user in #125
```

**Tip:** Use proper labels on PRs for better changelogs!

### Pre-release Versions

For alpha/beta/rc versions:

```bash
git tag -a v0.13.0-alpha.1 -m "Alpha release"
git push origin v0.13.0-alpha.1
```

Automatically marked as "pre-release" in GitHub.

---

## Troubleshooting

### CI Failures

#### Tests Failing

```bash
# Run tests locally first
cd src
pytest tests/ -v --tb=short

# Run specific test
pytest tests/test_event_store.py::test_write -v

# Run with xvfb for UI tests
xvfb-run pytest tests/ -v
```

#### Linting Errors

```bash
# Check what's wrong
ruff check .

# Auto-fix
ruff check --fix .
ruff format .

# Run pre-commit hooks
pre-commit run --all-files
```

#### Type Errors

```bash
# Run mypy
mypy src/

# Note: Currently non-blocking during migration
# See pyproject.toml for configuration
```

### Security Alerts

#### CodeQL Alert

1. Go to Security → Code scanning
2. Click the alert
3. Review the code path
4. Fix the vulnerability
5. Push fix → alert auto-closes

#### Dependabot Alert

1. Go to Security → Dependabot alerts
2. Review the vulnerability
3. Options:
   - Accept Dependabot PR to update
   - Update manually: `pip install --upgrade <package>`
   - Dismiss if false positive

### Coverage Drop

If coverage decreases:

```bash
# Find uncovered code
cd src
pytest tests/ --cov=. --cov-report=term-missing

# Look for lines marked with "!!!!!"
# Add tests for those lines
```

### Workflow Stuck

If a workflow hangs:

1. Check Actions tab
2. Find the running workflow
3. Cancel if stuck >30min
4. Re-run from Actions UI

### Label Issues

If PR labeler isn't working:

1. Check `.github/labeler.yml` syntax
2. Verify `GITHUB_TOKEN` has permissions
3. Check workflow logs for errors

---

## Configuration

### Pre-commit Hooks

Install locally for automatic checks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### IDE Integration

#### VS Code

```json
// .vscode/settings.json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm

1. File → Settings → Tools → External Tools
2. Add Ruff:
   - Program: `ruff`
   - Arguments: `check --fix $FilePath$`
3. Add as "Before Launch" step

### GitHub Settings

#### Branch Protection

Recommended settings for `main`:

```yaml
Protect matching branches:
  ☑ Require pull request reviews before merging
  ☑ Require status checks to pass before merging
    Required checks:
      - CI / pytest (3.11)
      - CI / pytest (3.12)
      - Quality / ruff
      - Security / codeql
  ☑ Require conversation resolution before merging
  ☑ Do not allow bypassing the above settings
```

#### Required Reviewers

Configure in CODEOWNERS:
- Edit `.github/CODEOWNERS`
- Add users/teams per path

#### Secrets

Required secrets for workflows:

| Secret | Purpose | Required For |
|--------|---------|-------------|
| `ANTHROPIC_API_KEY` | Claude AI integration | claude.yml |
| `CODECOV_TOKEN` | Coverage reporting | coverage.yml |

Add secrets: Settings → Secrets and variables → Actions

### Workflow Permissions

Some workflows need additional permissions:

```yaml
permissions:
  contents: write        # For pushing changes
  pull-requests: write   # For commenting on PRs
  security-events: write # For security scanning
  checks: write          # For status checks
```

---

## Best Practices

### For Contributors

1. **Small PRs**: Aim for <300 lines changed
2. **Descriptive titles**: Use conventional commits style
   ```
   feat: Add vector indexing support
   fix: Resolve race condition in event store
   docs: Update CI/CD documentation
   ```
3. **Link issues**: Always reference related issues
4. **Test coverage**: Add tests for new code
5. **Review feedback**: Address all automated comments
6. **Commit often**: Small, focused commits

### For Reviewers

1. **Check automation**: Review bot comments first
2. **Security first**: Pay extra attention to security findings
3. **Test locally**: For complex changes, pull and test
4. **Be constructive**: Suggest solutions, not just problems
5. **Approve when ready**: Don't block on minor nits

### For Maintainers

1. **Monitor workflows**: Check Actions tab regularly
2. **Update dependencies**: Review Dependabot PRs weekly
3. **Tune thresholds**: Adjust coverage/complexity limits as needed
4. **Document changes**: Keep this guide updated
5. **Rotate secrets**: Update API tokens periodically

---

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [CodeQL Queries](https://codeql.github.com/docs/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)

---

## Support

Need help?

1. **Check logs**: Actions tab → Failed workflow → View logs
2. **Search issues**: Look for similar problems
3. **Ask in PR**: Comment with `@Dutchthenomad` for help
4. **Update docs**: Found a solution? Update this guide!

---

*Last updated: 2025-12-17*
*Guide version: 1.0*
