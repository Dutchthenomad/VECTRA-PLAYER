# VECTRA-PLAYER Workflow Architecture

## Visual Workflow Map

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         GITHUB AUTOMATION PIPELINE                          │
└────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  DEVELOPER      │
│  LOCAL MACHINE  │
└────────┬────────┘
         │
         │ git push
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                            GITHUB REPOSITORY                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                │
│  │  MAIN BRANCH │    │  PR CREATED  │    │  VERSION TAG │                │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                │
│         │                   │                    │                         │
│         ├───────────────────┼────────────────────┤                         │
│         │                   │                    │                         │
│         ▼                   ▼                    ▼                         │
│  ┌─────────────────────────────────────────────────────────┐              │
│  │           GITHUB ACTIONS WORKFLOWS                      │              │
│  └─────────────────────────────────────────────────────────┘              │
│         │                   │                    │                         │
│         │                   │                    │                         │
└─────────┼───────────────────┼────────────────────┼─────────────────────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐
│  MAIN WORKFLOWS │  │   PR WORKFLOWS    │  │   RELEASE    │
└─────────────────┘  └──────────────────┘  └──────────────┘
```

---

## Detailed Workflow Breakdown

### 1. CI WORKFLOW (ci.yml)
```
┌──────────────────────────────────────────────────┐
│ Trigger: Push to main, PR, Manual               │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────────────┐      ┌────────────────┐    │
│  │  Python 3.11   │      │  Python 3.12   │    │
│  └────────┬───────┘      └────────┬───────┘    │
│           │                       │             │
│           ▼                       ▼             │
│    ┌─────────────┐        ┌─────────────┐      │
│    │  Install    │        │  Install    │      │
│    │  deps       │        │  deps       │      │
│    └─────┬───────┘        └─────┬───────┘      │
│          │                      │               │
│          ▼                      ▼               │
│    ┌─────────────┐        ┌─────────────┐      │
│    │  Run pytest │        │  Run pytest │      │
│    │  + coverage │        │  + coverage │      │
│    └─────┬───────┘        └─────┬───────┘      │
│          │                      │               │
│          ▼                      ▼               │
│    ┌─────────────┐        ┌─────────────┐      │
│    │  Upload     │        │  Upload     │      │
│    │  coverage   │        │  coverage   │      │
│    └─────────────┘        └─────────────┘      │
│                                                  │
│  Duration: ~3 minutes per Python version        │
│  Runs in parallel: ~3 minutes total             │
└──────────────────────────────────────────────────┘
```

### 2. QUALITY WORKFLOW (quality.yml)
```
┌──────────────────────────────────────────────────┐
│ Trigger: Push to main, PR, Manual               │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐      ┌───────────┐               │
│  │   ruff   │      │   mypy    │               │
│  │  linter  │      │   types   │               │
│  └────┬─────┘      └─────┬─────┘               │
│       │                  │                      │
│       ▼                  ▼                      │
│  ┌──────────┐      ┌───────────┐               │
│  │  Check   │      │  Check    │               │
│  │  code    │      │  types    │               │
│  │  style   │      │  (non-    │               │
│  │          │      │  blocking)│               │
│  └────┬─────┘      └─────┬─────┘               │
│       │                  │                      │
│       ▼                  ▼                      │
│  [PASS/FAIL]       [WARNING]                    │
│                                                  │
│  Duration: ~1 minute                            │
└──────────────────────────────────────────────────┘
```

### 3. SECURITY WORKFLOW (security.yml)
```
┌──────────────────────────────────────────────────┐
│ Trigger: Push, PR, Weekly, Manual               │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐      ┌──────────────┐        │
│  │   CodeQL     │      │  Dependency  │        │
│  │   Init       │      │   Review     │        │
│  └──────┬───────┘      └──────┬───────┘        │
│         │                     │                 │
│         ▼                     ▼                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │   Autobuild  │      │  Check for   │        │
│  │              │      │  vulns       │        │
│  └──────┬───────┘      └──────┬───────┘        │
│         │                     │                 │
│         ▼                     ▼                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │   Analyze    │      │  Report to   │        │
│  │   & Upload   │      │  Security    │        │
│  │   SARIF      │      │  tab         │        │
│  └──────────────┘      └──────────────┘        │
│                                                  │
│  Duration: ~5 minutes                           │
└──────────────────────────────────────────────────┘
```

### 4. CODE REVIEW WORKFLOW (code-review.yml) ⭐ NEW
```
┌──────────────────────────────────────────────────────────────┐
│ Trigger: PR opened/updated                                   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────┐ │
│  │Complexity  │  │ Coverage   │  │ Security   │  │Change│ │
│  │ Analysis   │  │ Report     │  │  Scan      │  │ Sum  │ │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └───┬──┘ │
│        │               │               │             │    │
│        ▼               ▼               ▼             ▼    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐  ┌──────┐ │
│  │  Radon   │    │  pytest  │    │  Bandit  │  │Count │ │
│  │  Lizard  │    │  --cov   │    │  Trivy   │  │files │ │
│  └─────┬────┘    └─────┬────┘    └─────┬────┘  └───┬──┘ │
│        │               │               │             │    │
│        ▼               ▼               ▼             ▼    │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           Post Comments to PR                        │ │
│  │  - Complexity metrics                                │ │
│  │  - Coverage diff                                     │ │
│  │  - Security findings                                 │ │
│  │  - Change summary                                    │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                              │
│  Duration: ~4 minutes (runs in parallel)                    │
└──────────────────────────────────────────────────────────────┘
```

### 5. PR LABELER WORKFLOW (pr-labeler.yml) ⭐ NEW
```
┌──────────────────────────────────────────────────┐
│ Trigger: PR opened/edited/synchronized          │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────────────────────────────┐       │
│  │  Analyze PR                          │       │
│  │  - Changed files                     │       │
│  │  - Line counts                       │       │
│  │  - Title keywords                    │       │
│  └──────────┬───────────────────────────┘       │
│             │                                    │
│             ▼                                    │
│  ┌──────────────────────────────────────┐       │
│  │  Apply Labels                        │       │
│  │  ├─ Area labels (core, ui, etc)     │       │
│  │  ├─ Size labels (xs, s, m, l, xl)   │       │
│  │  ├─ Type labels (bug, feat, etc)    │       │
│  │  └─ Priority labels (if urgent)     │       │
│  └──────────────────────────────────────┘       │
│                                                  │
│  Duration: ~30 seconds                          │
└──────────────────────────────────────────────────┘
```

### 6. COVERAGE WORKFLOW (coverage.yml) ⭐ NEW
```
┌──────────────────────────────────────────────────┐
│ Trigger: Push to main, PR                       │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐                               │
│  │  Run pytest  │                               │
│  │  with        │                               │
│  │  coverage    │                               │
│  └──────┬───────┘                               │
│         │                                        │
│         ▼                                        │
│  ┌──────────────────────────────────┐           │
│  │  Generate Reports                │           │
│  │  ├─ XML for Codecov              │           │
│  │  ├─ HTML for viewing             │           │
│  │  └─ Terminal output              │           │
│  └──────┬───────────────────────────┘           │
│         │                                        │
│         ▼                                        │
│  ┌──────────────┐      ┌──────────────┐        │
│  │  Upload to   │      │  Generate    │        │
│  │  Codecov     │      │  badge       │        │
│  └──────┬───────┘      └──────┬───────┘        │
│         │                     │                 │
│         ▼                     ▼                 │
│  ┌──────────────┐      ┌──────────────┐        │
│  │  Comment on  │      │  Commit      │        │
│  │  PR with     │      │  badge       │        │
│  │  summary     │      │  (main only) │        │
│  └──────────────┘      └──────────────┘        │
│                                                  │
│  Duration: ~3 minutes                           │
└──────────────────────────────────────────────────┘
```

### 7. RELEASE WORKFLOW (release.yml) ⭐ NEW
```
┌──────────────────────────────────────────────────┐
│ Trigger: Version tag (v*.*.*), Manual           │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐                               │
│  │  Checkout    │                               │
│  │  code        │                               │
│  └──────┬───────┘                               │
│         │                                        │
│         ▼                                        │
│  ┌──────────────────────────────────┐           │
│  │  Generate Changelog              │           │
│  │  - Group by PR labels            │           │
│  │  - Extract features/fixes        │           │
│  │  - Format markdown               │           │
│  └──────┬───────────────────────────┘           │
│         │                                        │
│         ▼                                        │
│  ┌──────────────┐      ┌──────────────┐        │
│  │  Create      │      │  Build       │        │
│  │  GitHub      │      │  artifacts   │        │
│  │  Release     │      │  (wheel/tar) │        │
│  └──────┬───────┘      └──────┬───────┘        │
│         │                     │                 │
│         ▼                     ▼                 │
│  ┌──────────────────────────────────┐           │
│  │  Notify                          │           │
│  │  - Create issue                  │           │
│  │  - Tag @Dutchthenomad            │           │
│  └──────────────────────────────────┘           │
│                                                  │
│  Duration: ~2 minutes                           │
└──────────────────────────────────────────────────┘
```

---

## Integration Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     COMPLETE PR LIFECYCLE                            │
└─────────────────────────────────────────────────────────────────────┘

   Developer                    GitHub                    Workflows
      │                           │                           │
      │  1. Create branch         │                           │
      ├──────────────────────────>│                           │
      │                           │                           │
      │  2. Push changes          │                           │
      ├──────────────────────────>│                           │
      │                           │                           │
      │  3. Create PR             │                           │
      ├──────────────────────────>│                           │
      │                           │                           │
      │                           │  4. Trigger workflows     │
      │                           ├──────────────────────────>│
      │                           │                           │
      │                           │       PR Labeler (~30s)   │
      │                           │       Quality Check (~1m) │
      │                           │       CI Tests (~3m)      │
      │                           │       Security (~5m)      │
      │                           │       Code Review (~4m)   │
      │                           │       Coverage (~3m)      │
      │                           │                           │
      │                           │  5. Post results         │
      │                           │<──────────────────────────│
      │                           │     - Labels applied      │
      │                           │     - Status checks       │
      │                           │     - Bot comments        │
      │                           │                           │
      │  6. View results          │                           │
      │<──────────────────────────┤                           │
      │     - Check status        │                           │
      │     - Read comments       │                           │
      │     - Review suggestions  │                           │
      │                           │                           │
      │  7. Fix issues            │                           │
      ├──────────────────────────>│                           │
      │     (push more commits)   │                           │
      │                           │                           │
      │                           │  8. Re-run workflows      │
      │                           ├──────────────────────────>│
      │                           │     (on new commits)      │
      │                           │                           │
      │  9. Request review        │                           │
      ├──────────────────────────>│                           │
      │                           │                           │
      │                           │  10. Code owner review    │
      │                           │      (@Dutchthenomad)     │
      │                           │                           │
      │  11. Merge PR             │                           │
      ├──────────────────────────>│                           │
      │                           │                           │
      │                           │  12. Main workflows       │
      │                           ├──────────────────────────>│
      │                           │      - Update coverage    │
      │                           │      - Run full tests     │
      │                           │                           │
```

---

## Dependency Graph

```
┌────────────────────────────────────────────────────────────┐
│                  WORKFLOW DEPENDENCIES                      │
└────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │   PUSH/PR    │
                    └──────┬───────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Quality │    │    CI    │    │ Security │
    │  (ruff)  │    │ (pytest) │    │ (CodeQL) │
    └──────┬───┘    └──────┬───┘    └──────┬───┘
           │               │               │
           │               ▼               │
           │        ┌──────────┐          │
           │        │ Coverage │          │
           │        └──────────┘          │
           │                              │
           └──────────────┬───────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  All Checks │
                   │    Pass     │
                   └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ Ready to    │
                   │   Merge     │
                   └─────────────┘
```

---

## Parallel Execution

Most workflows run in parallel for speed:

```
Time ─────────────────────────────────────────────────────>

0s    │ PR Labeler ├──┤
      │
1m    │ Quality    ├────┤
      │
3m    │ CI         ├──────────┤
      │
3m    │ Coverage   ├──────────┤
      │
4m    │ Code Rev   ├────────────┤
      │
5m    │ Security   ├──────────────┤
      │
      └──────────────────────────────────────────
      0        1        2        3        4      5 (minutes)

Total time: ~5 minutes (not 17+ minutes if sequential!)
```

---

## Data Flow

```
┌─────────────┐
│   Source    │
│    Code     │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│   Git Repository     │
└──────┬───────────────┘
       │
       ├─────> CI Tests ──────> Coverage Data ──┐
       │                                         │
       ├─────> Ruff ──────────> Style Report   │
       │                                         │
       ├─────> Radon ─────────> Complexity ─────┼──> PR Comments
       │                          Metrics        │
       ├─────> Bandit ────────> Security ───────┤
       │                          Findings       │
       ├─────> CodeQL ────────> Vuln Report ────┘
       │
       └─────> Changed Files ─> Area Labels
                Line Counts ──> Size Labels
                PR Title ─────> Type Labels
```

---

*For detailed information on each workflow, see docs/CI_CD_GUIDE.md*
*For quick commands and tips, see docs/QUICK_REFERENCE.md*
