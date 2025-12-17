# Automated Workflows Setup & Activation Guide

This guide helps you activate and configure all the automated workflows that have been set up.

## 🎯 Quick Start (5 Minutes)

### Step 1: Enable Workflows
All workflows are already committed. They will automatically activate on the next:
- Push to main
- Pull request
- Scheduled time (for security scans)

**No action needed** - workflows are ready to go! ✅

### Step 2: Optional Integrations

#### Codecov (Recommended for better coverage reports)
1. Go to https://codecov.io/
2. Sign in with GitHub
3. Add VECTRA-PLAYER repository
4. Copy the token
5. Add to GitHub: Settings → Secrets → Actions → New secret
   - Name: `CODECOV_TOKEN`
   - Value: [paste token]

**Without this:** Coverage still works, but no advanced Codecov features

#### Branch Protection (Recommended)
1. Go to Settings → Branches
2. Add rule for `main` branch:
   - ☑ Require pull request reviews before merging
   - ☑ Require status checks to pass before merging
     - Select: `CI / pytest (3.11)`, `CI / pytest (3.12)`, `Quality / ruff`, `Security / codeql`
   - ☑ Require conversation resolution before merging
3. Save changes

**Without this:** PRs can be merged without reviews/checks

## 📊 Workflow Overview

### What Runs When?

```
┌─────────────────────────────────────────────────────────────┐
│ PUSH TO MAIN                                                │
├─────────────────────────────────────────────────────────────┤
│ ✓ CI (pytest)                                               │
│ ✓ Quality (ruff, mypy)                                      │
│ ✓ Security (CodeQL)                                         │
│ ✓ Coverage (with badge update)                             │
│ ✓ Guardrails                                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PULL REQUEST                                                │
├─────────────────────────────────────────────────────────────┤
│ ✓ All workflows from "Push to Main"                        │
│ ✓ PR Labeler (automatic labels)                            │
│ ✓ Code Review (complexity, coverage, security, summary)    │
│ ✓ Security / Dependency Review                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ VERSION TAG (v*.*.*)                                        │
├─────────────────────────────────────────────────────────────┤
│ ✓ Release (create release, build artifacts, changelog)     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WEEKLY SCHEDULE (Monday 3:27 AM UTC)                       │
├─────────────────────────────────────────────────────────────┤
│ ✓ Security scan                                             │
│ ✓ Dependabot checks                                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ MANUAL TRIGGER (workflow_dispatch)                         │
├─────────────────────────────────────────────────────────────┤
│ ✓ Any workflow (via Actions tab → Run workflow)            │
└─────────────────────────────────────────────────────────────┘
```

### Estimated Run Times
- **PR Labeler:** ~30 seconds
- **Quality (ruff):** ~1 minute
- **CI (pytest):** ~3 minutes per Python version
- **Security (CodeQL):** ~5 minutes
- **Code Review:** ~4 minutes
- **Coverage:** ~3 minutes
- **Total for PR:** ~10-15 minutes (runs in parallel)

## 🔍 Understanding the Automated Comments

When you create a PR, you'll receive several automated comments:

### 1. Change Summary
```markdown
## PR Change Summary

### Statistics
- **Files changed**: 5
- **Additions**: +150 lines
- **Deletions**: -20 lines
- **Net change**: 130 lines

### Areas Affected
- Services
- Tests

### Review Checklist
- ⚠️ No test changes detected: Consider adding tests
```

**Action:** Review the summary and ensure tests are included if code was changed.

### 2. Complexity Analysis
```markdown
## Code Complexity Analysis

### Cyclomatic Complexity (Radon)
src/services/event_store.py
    M 100:4 EventStore.write - B (7)
    M 200:4 EventStore._flush - D (15)  # Consider refactoring!

### Maintainability Index
Average: 75.2 (Good)
```

**Action:** If CC > 10, consider refactoring complex functions.

### 3. Coverage Report
```markdown
## Coverage Report

**Coverage:** 65.2% (+2.3% from base)

### Files with coverage changes:
- src/services/event_store.py: 85% (+10%)
- src/core/event_bus.py: 90% (unchanged)

### Uncovered lines in changes:
- src/services/event_store.py: lines 145-148
```

**Action:** Aim to cover the uncovered lines with tests.

### 4. Security Scan
```markdown
## Security Scan Results

### Security Issues Found
- **MEDIUM**: Use of insecure MD5 hash function
  - File: `src/utils/hash.py:42`

✅ No security issues found by Bandit
```

**Action:** Address any HIGH or CRITICAL issues before merging.

## 🏷️ How PR Labeling Works

Labels are automatically added based on:

### File Changes
| Changed Files | Label Added |
|---------------|-------------|
| `src/core/**` | `area: core` |
| `src/services/**` | `area: services` |
| `src/ui/**` | `area: ui` |
| `src/tests/**` | `area: tests` |
| `.github/workflows/**` | `area: ci/cd` |
| `docs/**` or `*.md` | `documentation` |

### PR Size
| Lines Changed | Label |
|---------------|-------|
| < 10 | `size/xs` |
| 10-100 | `size/s` |
| 100-500 | `size/m` |
| 500-1000 | `size/l` |
| > 1000 | `size/xl` + warning |

### PR Title Keywords
| Title Contains | Label Added |
|----------------|-------------|
| "fix", "bug" | `bug` |
| "feat", "feature" | `enhancement` |
| "docs" | `documentation` |
| "test" | `testing` |
| "refactor" | `refactoring` |
| "perf" | `performance` |
| "security" | `security` |
| "breaking" | `breaking-change` |

## 🚀 Release Process

### Automatic Release on Tag
```bash
# Ensure main is ready
git checkout main
git pull

# Create and push tag
git tag -a v0.13.0 -m "Release v0.13.0: Feature description"
git push origin v0.13.0

# Workflow automatically:
# 1. Generates changelog from PR labels
# 2. Creates GitHub release
# 3. Builds distribution packages
# 4. Creates notification issue
```

### Manual Release Trigger
1. Go to Actions → Release Automation
2. Click "Run workflow"
3. Enter version (e.g., v0.13.0)
4. Click "Run workflow"

### Changelog Format
The changelog is generated from PR titles and labels:

```markdown
## 🚀 Features
- Add vector indexing by @user in #123

## 🐛 Bug Fixes
- Fix race condition by @user in #124

## 📝 Documentation
- Update CI guide by @user in #125
```

**Tip:** Use proper labels on PRs for better changelogs!

## 🔧 Customization

### Adjust Complexity Thresholds
Edit `.github/workflows/code-review.yml`:
```yaml
# Change radon arguments
radon cc src/ -a -s -n B  # Only show B+ complexity
```

### Modify Coverage Targets
Edit `.github/workflows/coverage.yml`:
```yaml
MINIMUM_GREEN: 80   # Change from 70
MINIMUM_ORANGE: 60  # Change from 50
```

### Add/Remove Auto-Labels
Edit `.github/labeler.yml`:
```yaml
# Add new area label
'area: ml':
  - changed-files:
    - any-glob-to-any-file: 'src/ml/**/*'
```

### Customize PR Template
Edit `.github/pull_request_template.md` to match your needs.

### Update CODEOWNERS
Edit `.github/CODEOWNERS` to assign different reviewers:
```
# Example: Add team as owner
/src/services/ @Dutchthenomad @your-team
```

## 📈 Monitoring Workflows

### View All Workflows
1. Go to repository → Actions tab
2. See all workflow runs
3. Filter by workflow name, branch, or status

### Check Specific Run
1. Click on a workflow run
2. View all jobs
3. Click job to see detailed logs

### Download Artifacts
1. Go to completed workflow run
2. Scroll to "Artifacts" section
3. Download (e.g., coverage reports)

### Workflow Badges
Add to README.md:
```markdown
[![CI](https://github.com/Dutchthenomad/VECTRA-PLAYER/actions/workflows/ci.yml/badge.svg)](...)
```

Already added to README! ✅

## 🐛 Troubleshooting

### Workflow Not Running
**Problem:** Workflow doesn't trigger on PR/push

**Solutions:**
1. Check `.github/workflows/` files are in main branch
2. Verify YAML syntax: `yamllint .github/workflows/`
3. Check Actions tab for errors
4. Ensure repository has Actions enabled: Settings → Actions → Allow all actions

### Permission Errors
**Problem:** Workflow fails with "Resource not accessible by integration"

**Solutions:**
1. Check workflow `permissions:` section
2. Go to Settings → Actions → General → Workflow permissions
3. Select "Read and write permissions"
4. Re-run workflow

### Bot Not Commenting
**Problem:** No automated comments on PR

**Solutions:**
1. Check workflow logs for errors
2. Verify PR number is correct
3. Check GITHUB_TOKEN permissions
4. Look for rate limit errors (GitHub API)

### CodeQL Failures
**Problem:** CodeQL analysis fails

**Solutions:**
1. Check if Python files have syntax errors
2. Look at CodeQL logs in Actions tab
3. May need to add CodeQL config if complex setup
4. Temporary: Add `continue-on-error: true` to job

### Coverage Upload Fails
**Problem:** Codecov upload fails

**Solutions:**
1. Verify CODECOV_TOKEN is set (if using Codecov)
2. Check if coverage.xml was generated
3. Review coverage.yml workflow logs
4. Codecov is optional - local coverage still works!

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] **Create a test PR**
  ```bash
  git checkout -b test/verify-workflows
  echo "# Test" >> docs/test.md
  git add docs/test.md
  git commit -m "test: verify CI/CD workflows"
  git push origin test/verify-workflows
  ```

- [ ] **Check PR Labels**
  - Size label applied (size/xs)
  - Area label applied (documentation)
  - Type label from title (testing)

- [ ] **Verify Bot Comments**
  - Change summary comment appears (~1 min)
  - Complexity analysis comment (~2 min)
  - Coverage report comment (~3 min)
  - Security scan comment (~4 min)

- [ ] **Check Workflow Status**
  - All workflows pass or show expected status
  - Green checkmarks on PR
  - No unexpected failures

- [ ] **Test CODEOWNERS**
  - You are automatically added as reviewer
  - Notification received

- [ ] **Review PR Template**
  - Template auto-fills on PR creation
  - All sections present and clear

- [ ] **Close Test PR**
  - Clean up test branch

## 🎓 Learning Resources

### GitHub Actions
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow syntax](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)

### Code Quality Tools
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Radon Documentation](https://radon.readthedocs.io/)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [Bandit Documentation](https://bandit.readthedocs.io/)

### Best Practices
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [GitHub Flow](https://guides.github.com/introduction/flow/)

## 📞 Support

### Need Help?
1. Check this guide first
2. Review [CI_CD_GUIDE.md](CI_CD_GUIDE.md) for detailed info
3. Search existing GitHub issues
4. Create issue with "ci/cd" label
5. Tag @Dutchthenomad in PR comments

### Found a Bug?
Use the CI/CD Issue template:
1. Go to Issues → New issue
2. Select "CI/CD Issue" template
3. Fill out all sections
4. Include workflow logs

### Want to Improve?
1. Workflows can be customized
2. Documentation can be enhanced
3. Submit PRs with improvements
4. Share your feedback!

## 🎉 You're All Set!

The automated code review and CI/CD pipeline is now fully configured and ready to use!

### What Happens Next?
1. **Every PR** gets automatic reviews
2. **Code quality** is enforced by CI
3. **Security** is continuously monitored
4. **Releases** are automated
5. **Development** is more efficient!

### Key Benefits
- ✅ Catch bugs earlier
- ✅ Maintain code quality
- ✅ Enforce best practices
- ✅ Improve security
- ✅ Speed up reviews
- ✅ Reduce manual work
- ✅ Better documentation
- ✅ Consistent process

---

*Setup guide version: 1.0*
*Last updated: 2025-12-17*

**Happy automating! 🚀**
