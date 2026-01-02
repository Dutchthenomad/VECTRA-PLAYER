# VECTRA-PLAYER CI/CD Modernization TODO

**Status:** Repository Review Completed - Action Items Identified  
**Date:** 2026-01-02  
**Purpose:** Bring repository up to current CI/CD standards and GitHub workflow best practices

---

## 🎯 Executive Summary

The VECTRA-PLAYER repository has a solid foundation with comprehensive CI/CD workflows already in place. This TODO list focuses on maintenance tasks, incremental improvements, and addressing technical debt accumulated over the past week.

**Current State:** ✅ Strong CI/CD infrastructure exists  
**Priority:** Maintenance, optimization, and incremental improvements

---

## 📊 Repository Health Assessment

### ✅ **Strengths (Already Implemented)**
- ✅ Comprehensive CI/CD workflows (10 workflows in `.github/workflows/`)
- ✅ Quality checks: Ruff linting, pytest testing, code coverage
- ✅ Security scanning: CodeQL, dependency review
- ✅ Pre-commit hooks configured
- ✅ Clear documentation (README, CLAUDE.md, CI_CD_GUIDE.md, etc.)
- ✅ Python 3.11/3.12 testing in CI
- ✅ Modern tooling: Ruff, pytest, MyPy configuration
- ✅ Event-driven architecture with proper separation of concerns

### ⚠️ **Areas for Improvement**
- ⚠️ Type checking (MyPy) disabled in pre-commit due to errors
- ⚠️ Large number of temporarily ignored Ruff rules (TODO #1 markers)
- ⚠️ 60% code coverage threshold (could be higher)
- ⚠️ Some legacy code patterns flagged in pyproject.toml

---

## 🔧 Priority 1: Immediate Maintenance Tasks

### 1.1 Clean Up Temporary/Debug Files
- [ ] **Remove or document `a.out` file** in root directory (C/C++ compiled output?)
  - Action: Delete if unused, or add to `.gitignore` if build artifact
  - Command: `git rm a.out` or add `a.out` to `.gitignore`

- [ ] **Review and organize debugging scripts**
  - Files: `apply_conflict_fix.sh`, `start_debugging.sh`, `setup_pyright_lsp.sh`
  - Action: Move to `scripts/debug/` or document purpose in README
  - Consider: Are these still needed or can they be removed?

### 1.2 Verify CI/CD Pipeline Health
- [ ] **Check recent workflow runs on GitHub**
  - Visit: https://github.com/Dutchthenomad/VECTRA-PLAYER/actions
  - Verify: All workflows passing on main branch
  - Action: Fix any failing workflows

- [ ] **Review and update workflow versions**
  - Check: GitHub Actions versions in `.github/workflows/*.yml`
  - Update: Any deprecated action versions (e.g., `actions/checkout@v3` → `@v4`)

- [ ] **Test pre-commit hooks locally**
  - Command: `pre-commit run --all-files`
  - Fix: Any issues that arise
  - Verify: All hooks pass before committing

### 1.3 Dependency Maintenance
- [ ] **Update dependencies to latest compatible versions**
  - Review: `pyproject.toml` dependencies
  - Check: Security advisories via `pip-audit` or Dependabot
  - Test: After updates to ensure compatibility

- [ ] **Run security audit**
  - Command: `pip install pip-audit && pip-audit`
  - Or: Check GitHub Security tab for Dependabot alerts
  - Fix: Any critical or high severity vulnerabilities

---

## 🎨 Priority 2: Code Quality Improvements

### 2.1 Incremental Ruff Rule Enablement (TODO #1)
The codebase has many temporarily ignored rules. Enable them incrementally:

**Phase 1: Low-hanging fruit (Quick wins)**
- [ ] Enable `RUF010` - explicit-f-string-type-conversion (~small fixes)
- [ ] Enable `RUF022` - unsorted-dunder-all
- [ ] Enable `C401` - unnecessary-generator-set
- [ ] Enable `C416` - unnecessary-comprehension
- [ ] Enable `SIM210` - if-expr-with-true-false

**Phase 2: Naming conventions**
- [ ] Enable `N806` - non-lowercase-variable-in-function
- [ ] Enable `N803` - invalid-argument-name
- [ ] Enable `N802` - invalid-function-name
- [ ] Enable `N815` - mixed-case-variable-in-class-scope (93 issues - batch fix)

**Phase 3: Error handling**
- [ ] Enable `B904` - raise-without-from-inside-except
- [ ] Enable `B905` - zip-without-explicit-strict

**Phase 4: Simplification**
- [ ] Enable `SIM102` - collapsible-if (22 issues)
- [ ] Enable `SIM105` - use-contextlib-suppress (15 issues)
- [ ] Enable `SIM115` - open-file-with-context-handler

**Phase 5: Modern Python (pyupgrade)**
- [ ] Enable `UP007` - non-pep604-annotation-union (use `X | Y` instead of `Union[X, Y]`)
- [ ] Enable `UP017` - datetime-timezone-utc

**Phase 6: Type checking improvements**
- [ ] Enable `TCH` - typing-only imports (requires refactoring)
- [ ] Enable `RUF013` - implicit-optional (12 issues)

### 2.2 Type Checking (MyPy)
- [ ] **Re-enable MyPy in pre-commit hooks**
  - Current: Commented out in `.pre-commit-config.yaml`
  - Action: Fix type errors incrementally, then uncomment
  - Start: `mypy src/ --show-error-codes` to see current state

- [ ] **Fix critical type errors first**
  - Focus: Core modules (event_store, event_bus)
  - Then: Services, models, UI components

- [ ] **Add type hints to untyped functions**
  - Use: `mypy --disallow-untyped-defs` progressively
  - Target: 80%+ type coverage

### 2.3 Test Coverage Improvements
- [ ] **Increase coverage from 60% to 70%+**
  - Run: `pytest --cov=. --cov-report=html`
  - Identify: Uncovered critical paths
  - Add: Unit tests for uncovered code

- [ ] **Add integration tests**
  - Focus: Event flow (EventBus → EventStore → Parquet)
  - Test: WebSocket connection and data capture
  - Test: Vector indexing workflow

### 2.4 Documentation Updates
- [ ] **Update CLAUDE.md with recent changes**
  - Add: Any new patterns or conventions discovered
  - Update: Any outdated information

- [ ] **Review and update README.md**
  - Verify: All quickstart commands work
  - Update: Screenshots if UI changed
  - Add: Troubleshooting section if needed

- [ ] **Create/update CHANGELOG.md**
  - Document: Changes from last week
  - Follow: Keep a Changelog format
  - Link: To GitHub releases

---

## 🚀 Priority 3: Feature Enhancements

### 3.1 CI/CD Enhancements
- [ ] **Add workflow caching**
  - Cache: `pip` dependencies in CI workflows
  - Cache: Pre-commit environments
  - Benefit: Faster CI runs

- [ ] **Add workflow summaries**
  - Use: `$GITHUB_STEP_SUMMARY` for better output
  - Show: Test results, coverage metrics
  - Example: https://github.blog/2022-05-09-supercharging-github-actions-with-job-summaries/

- [ ] **Add performance benchmarks**
  - Tool: `pytest-benchmark`
  - Track: Critical path performance over time
  - Alert: On regression

### 3.2 Development Experience
- [ ] **Add VS Code devcontainer**
  - File: `.devcontainer/devcontainer.json`
  - Benefit: Consistent development environment
  - Include: All dev dependencies pre-installed

- [ ] **Add Makefile for common tasks**
  - Commands: `make test`, `make lint`, `make format`, `make install`
  - Benefit: Standardized commands across team

- [ ] **Improve local development setup**
  - Script: `scripts/setup_dev_env.sh`
  - Action: One-command setup for new contributors
  - Include: Virtual env, deps, pre-commit, data dir

### 3.3 Monitoring and Observability
- [ ] **Add structured logging**
  - Replace: Print statements with proper logging
  - Use: Python `logging` module with JSON format
  - Benefit: Better debugging in production

- [ ] **Add metrics collection**
  - Track: Event processing rate
  - Track: Parquet write performance
  - Track: Vector indexing time
  - Tool: Prometheus/Grafana or simple CSV logging

---

## 🔒 Priority 4: Security Hardening

### 4.1 Dependency Security
- [ ] **Enable Dependabot**
  - File: `.github/dependabot.yml`
  - Check: Python dependencies weekly
  - Check: GitHub Actions monthly

- [ ] **Add SBOM generation**
  - Tool: `pip-licenses` or `cyclonedx-bom`
  - Purpose: Software Bill of Materials
  - Include: In releases

### 4.2 Code Security
- [ ] **Review CodeQL findings**
  - Check: GitHub Security tab
  - Fix: Any open alerts
  - Document: False positives

- [ ] **Add security policy**
  - File: `SECURITY.md`
  - Include: Reporting process
  - Include: Supported versions

- [ ] **Scan for secrets**
  - Tool: `gitleaks` or `trufflehog`
  - Check: No hardcoded credentials
  - Add: Pre-commit hook for secret detection

---

## 📦 Priority 5: Architecture Improvements

### 5.1 Event Store Optimization
- [ ] **Add event batching**
  - Current: One-by-one writes to Parquet
  - Improvement: Batch writes for performance
  - Benefit: 10-100x faster writes

- [ ] **Add event compression**
  - Use: Parquet built-in compression (snappy/zstd)
  - Benefit: Smaller storage footprint

- [ ] **Add event retention policy**
  - Config: Max age or max size
  - Action: Auto-cleanup old events
  - Benefit: Prevent unbounded growth

### 5.2 Vector Indexing Improvements
- [ ] **Add incremental indexing**
  - Current: Full rebuild each time
  - Improvement: Only index new events
  - Benefit: Faster index updates

- [ ] **Add index versioning**
  - Track: Index schema version
  - Support: Migration between versions
  - Benefit: Safe upgrades

### 5.3 Code Organization
- [ ] **Refactor large modules**
  - Target: Files > 500 lines
  - Action: Split into smaller, focused modules
  - Benefit: Better maintainability

- [ ] **Remove deprecated code**
  - Directory: `deprecated/`
  - Action: Delete if truly unused
  - Or: Document why kept

---

## 🧪 Priority 6: Testing Infrastructure

### 6.1 Test Quality
- [ ] **Add property-based tests**
  - Tool: `hypothesis`
  - Target: Data models, event schemas
  - Benefit: Catch edge cases

- [ ] **Add mutation testing**
  - Tool: `mutmut`
  - Purpose: Verify test effectiveness
  - Target: 80%+ mutation score

- [ ] **Add snapshot testing**
  - Tool: `pytest-snapshot`
  - Use: For UI components
  - Benefit: Catch visual regressions

### 6.2 Test Performance
- [ ] **Parallelize tests**
  - Tool: `pytest-xdist`
  - Command: `pytest -n auto`
  - Benefit: Faster test runs

- [ ] **Add test markers**
  - Mark: `@pytest.mark.fast` vs `@pytest.mark.slow`
  - CI: Run fast tests on every commit
  - CI: Run slow tests nightly

---

## 📝 Priority 7: Process Improvements

### 7.1 Issue/PR Templates
- [ ] **Review issue templates**
  - Location: `.github/ISSUE_TEMPLATE/`
  - Ensure: Bug, feature, documentation templates
  - Update: If outdated

- [ ] **Review PR template**
  - Location: `.github/pull_request_template.md`
  - Include: Checklist for contributors
  - Include: Testing requirements

### 7.2 Contributing Guidelines
- [ ] **Update CONTRIBUTING.md**
  - Include: Step-by-step contribution process
  - Include: Code review expectations
  - Include: Release process

- [ ] **Add CODE_OF_CONDUCT.md**
  - Use: Contributor Covenant
  - Benefit: Welcoming community

### 7.3 Release Process
- [ ] **Document release process**
  - File: `docs/RELEASING.md`
  - Include: Version bumping
  - Include: Changelog generation
  - Include: GitHub release creation

- [ ] **Automate releases**
  - Tool: `semantic-release` or manual workflow
  - Trigger: On version tag push
  - Action: Build, test, publish

---

## 🎯 Quick Wins (Do First!)

These can be done quickly and provide immediate value:

1. [ ] Remove `a.out` file from repository
2. [ ] Run `pre-commit run --all-files` and fix issues
3. [ ] Update `.github/workflows/` action versions to latest
4. [ ] Add `.venv/` to `.gitignore` if not present
5. [ ] Run `ruff check --fix .` to auto-fix simple issues
6. [ ] Check GitHub Actions dashboard for any failing workflows
7. [ ] Review and close stale issues/PRs
8. [ ] Add missing docstrings to public functions
9. [ ] Update copyright year to 2026 if needed
10. [ ] Run security scan: `pip install pip-audit && pip-audit`

---

## 📅 Suggested Implementation Timeline

### Week 1: Maintenance & Quick Wins
- Complete all Priority 1 tasks
- Complete Quick Wins section
- Review CI/CD pipeline health

### Week 2-3: Code Quality
- Tackle Priority 2 tasks incrementally
- Enable Ruff rules in phases (1-2 per day)
- Begin MyPy re-enablement

### Week 4-5: Features & Architecture
- Implement Priority 3 & 5 tasks
- Focus on high-impact improvements
- Add monitoring/observability

### Week 6+: Testing & Process
- Complete Priority 6 & 7 tasks
- Improve test coverage
- Document processes

---

## 📊 Success Metrics

Track these metrics to measure improvement:

- [ ] **CI/CD Health:** All workflows passing ✅
- [ ] **Code Coverage:** ≥70% (currently 60%)
- [ ] **Type Coverage:** ≥80% (MyPy re-enabled)
- [ ] **Ruff Compliance:** 100% (no ignored rules)
- [ ] **Security:** Zero high/critical vulnerabilities
- [ ] **Documentation:** All commands in docs work
- [ ] **Test Speed:** <5 minutes for full suite
- [ ] **PR Cycle Time:** <24 hours from open to merge

---

## 🔗 Related Resources

- **GitHub Actions Dashboard:** https://github.com/Dutchthenomad/VECTRA-PLAYER/actions
- **GitHub Security Advisories:** https://github.com/Dutchthenomad/VECTRA-PLAYER/security
- **Issues:** https://github.com/Dutchthenomad/VECTRA-PLAYER/issues
- **Discussions:** https://github.com/Dutchthenomad/VECTRA-PLAYER/discussions
- **CI/CD Guide:** `docs/CI_CD_GUIDE.md`
- **Architecture Docs:** `docs/ASCII-FLOWCHART.md`

---

## Notes

- This TODO list is based on repository review as of 2026-01-02
- Priorities may shift based on team bandwidth and business needs
- Items marked TODO(#1) in pyproject.toml align with Priority 2.1
- All improvements should maintain backward compatibility
- Focus on incremental progress rather than big-bang changes

**Remember:** Make small, focused PRs. Test thoroughly. Keep documentation updated.

---

_Generated by GitHub Copilot Agent - Repository Review Task_
