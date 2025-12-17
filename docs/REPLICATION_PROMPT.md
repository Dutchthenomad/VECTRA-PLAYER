# Prompt for Setting Up GitHub Automation in Other Repositories

Copy and paste this prompt to a new GitHub Copilot agent session in another repository:

---

**PROMPT START:**

I need you to set up a comprehensive automated code review and CI/CD pipeline for this repository, similar to what was implemented in the VECTRA-PLAYER repository.

## What I Need

Implement a production-grade GitHub automation system with:

### 1. Automated Code Review Workflows
- **Complexity analysis** using Radon (catch functions with cyclomatic complexity > 10)
- **Test coverage reporting** with coverage diffs on PRs
- **Security scanning** using Bandit (Python) and Trivy (filesystem)
- **Change impact analysis** with file counts, areas affected, and warnings
- All results posted as automated PR comments within ~5 minutes

### 2. Smart PR Labeling
- **Area-based labels** from file changes (e.g., area: core, area: ui, area: tests)
- **Size labels** based on lines changed (size/xs, size/s, size/m, size/l, size/xl)
- **Type labels** from PR title keywords (bug, enhancement, documentation, security, etc.)
- **Priority labels** for urgent/hotfix items
- Large PR warnings (>1000 lines)

### 3. Test Coverage Tracking
- Coverage badge auto-update on main branch
- Coverage diff comments on PRs
- Codecov integration (optional, requires CODECOV_TOKEN secret)
- HTML coverage reports as downloadable artifacts
- Minimum thresholds: 70% green, 50% orange

### 4. Automated Release Management
- Tag-based automatic releases (e.g., `git tag v1.0.0`)
- Changelog generation from PR labels
- Build artifact creation
- Team notifications via GitHub issues
- Semantic versioning support (including alpha/beta/rc)

### 5. Security Scanning (Multi-Layer)
- **CodeQL** for semantic analysis
- **Dependabot** for dependency updates
- **Bandit** for Python-specific security issues
- **Trivy** for comprehensive vulnerability scanning
- **Dependency Review** for PR-specific dependency checks
- SARIF upload to GitHub Security tab
- Weekly scheduled security scans

### 6. Configuration Files
- **CODEOWNERS** file for automatic reviewer assignment
- **Pull request template** with structured sections (description, testing, security, etc.)
- **Labeler configuration** with glob patterns for automatic labeling
- **Release changelog configuration** for categorizing changes
- **Issue templates** for feature requests and CI/CD issues

### 7. Comprehensive Documentation
Create documentation covering:
- **README.md** with project overview and workflow badges
- **CI/CD Guide** with complete workflow reference and troubleshooting
- **Quick Reference** with command cheat sheets and common scenarios
- **Developer Onboarding** with setup checklist and first contribution workflow
- **Setup Guide** with activation steps and optional integrations
- **Workflow Architecture** with visual diagrams and execution flow
- **Implementation Summary** with deliverables list and metrics

## Technical Requirements

- All workflows should run in **parallel** where possible for speed (~5 min total)
- Use **GitHub Actions** for all automation
- Support the primary programming language(s) of this repository
- Ensure workflows are **idempotent** (can run multiple times safely)
- Follow **conventional commits** format for changelog generation
- Make workflows **extensible** and easy to customize
- Include **troubleshooting guides** in documentation

## Deliverables

1. GitHub Actions workflow files in `.github/workflows/`:
   - `code-review.yml` - Automated PR analysis
   - `pr-labeler.yml` - Automatic PR labeling
   - `coverage.yml` - Test coverage tracking
   - `release.yml` - Automated releases
   
2. Configuration files in `.github/`:
   - `CODEOWNERS` - Reviewer assignment
   - `pull_request_template.md` - PR template
   - `labeler.yml` - Labeling rules
   - `release-changelog-config.json` - Changelog config
   
3. Issue templates in `.github/ISSUE_TEMPLATE/`:
   - Enhancement/feature request template
   - CI/CD troubleshooting template
   
4. Documentation in `docs/`:
   - CI_CD_GUIDE.md
   - QUICK_REFERENCE.md
   - ONBOARDING.md
   - SETUP_GUIDE.md
   - WORKFLOW_ARCHITECTURE.md
   - IMPLEMENTATION_SUMMARY.md
   
5. Updated README.md with badges and quick start

## Success Criteria

- All workflows trigger correctly on push/PR/tag events
- Automated comments appear on PRs within 5 minutes
- PR labels are applied automatically within 30 seconds
- Documentation is clear and comprehensive (60KB+)
- No hardcoded secrets or credentials
- Workflows are customizable and well-documented
- System is ready to use immediately after merge

## Reference Implementation

The reference implementation is in the VECTRA-PLAYER repository:
https://github.com/Dutchthenomad/VECTRA-PLAYER

Key commits:
- Initial workflows and configuration
- Comprehensive documentation
- Templates and automation

You can review the `.github/` directory and `docs/` directory in that repository for examples.

## Repository-Specific Adaptations

Please adapt the following to this repository:
- Programming language(s) and tech stack
- Test framework and coverage tools
- Build system and artifact types
- Code quality tools (linters, formatters)
- Review the existing `.github/workflows/` and integrate/enhance
- Adjust CODEOWNERS for this project's maintainers
- Customize labeling rules for this project's structure

## Optional Integrations

After setup, I may want to configure:
- Codecov token for enhanced coverage reports
- Branch protection rules
- Additional code quality tools specific to this stack
- Custom labels for this project's workflow

**PROMPT END**

---

## Additional Instructions for You

When using this prompt in a new repository:

1. **Before pasting:** Review the new repository's structure, tech stack, and existing workflows
2. **After pasting:** Let the agent explore and ask clarifying questions if needed
3. **Customize:** Mention any repository-specific requirements (e.g., "This is a Node.js project" or "We use Jest for testing")
4. **Review:** Once implemented, review the workflows and documentation for accuracy
5. **Test:** Create a test PR to verify all automation works correctly

## Quick Customization Tips

For different tech stacks:
- **Node.js/TypeScript:** Replace pytest with Jest/Vitest, use ESLint instead of ruff
- **Java:** Use Maven/Gradle, Checkstyle, SpotBugs
- **Go:** Use go test, golangci-lint
- **Ruby:** Use RSpec, RuboCop
- **Rust:** Use cargo test, clippy

The agent should automatically adapt the workflows to match the repository's tech stack.
