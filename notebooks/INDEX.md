# Bayesian Sidebet Optimization - Complete Package

## Quick Navigation

| File | Purpose | Read Time |
|------|---------|-----------|
| **DELIVERABLE_SUMMARY.md** | START HERE - Executive summary | 5 min |
| **QUICK_REFERENCE.md** | Code snippets and formulas | 3 min |
| **README.md** | Full documentation | 15 min |
| **PROBABILISTIC_REASONING.md** | Mathematical theory | 20 min |
| `bayesian_sidebet_analysis.py` | Core analysis module | - |
| `sidebet_optimization.ipynb` | Interactive Jupyter notebook | 30 min |

## Choose Your Path

### I want to understand the strategy
→ Read **DELIVERABLE_SUMMARY.md** first, then **QUICK_REFERENCE.md**

### I want to run the analysis
→ Open **sidebet_optimization.ipynb** in Jupyter

### I want to integrate into code
→ Use **bayesian_sidebet_analysis.py** directly

### I want to understand the math
→ Read **PROBABILISTIC_REASONING.md**

### I want everything
→ Start with **README.md**, then explore Jupyter notebook

## What Each File Provides

### DELIVERABLE_SUMMARY.md
- What you asked for vs what you got
- Key findings (timing, features, EV)
- Practical implementation examples
- RL integration roadmap
- Production checklist

### QUICK_REFERENCE.md
- TL;DR strategy (one-page)
- Code snippets for live trading
- Formula cheatsheet
- Feature importance rankings
- Common pitfalls

### README.md
- Comprehensive documentation
- All analysis components explained
- Function reference
- Key findings
- WebSocket integration guide
- Output file descriptions

### PROBABILISTIC_REASONING.md
- Bayesian survival analysis derivation
- Feature importance (information gain)
- Expected value proofs
- Kelly criterion derivation
- Model validation strategies
- Advanced topics (GP, RL, causal inference)

### bayesian_sidebet_analysis.py
- 541 lines of production code
- BayesianSurvivalModel class
- Feature engineering functions
- EV and Kelly calculations
- Conditional probability analysis
- Standalone executable (run with `python`)

### sidebet_optimization.ipynb
- Interactive Jupyter notebook
- 8 analysis sections with visualizations
- Step-by-step walkthrough
- Code + explanations + plots
- Generates 6 PNG visualizations

## Quick Start

### 1-Minute Test
```bash
python notebooks/bayesian_sidebet_analysis.py
```

### 5-Minute Analysis
```bash
jupyter notebook notebooks/sidebet_optimization.ipynb
# Run all cells (Cell → Run All)
```

### 30-Minute Deep Dive
1. Read DELIVERABLE_SUMMARY.md
2. Run Jupyter notebook
3. Review visualizations in ~/rugs_data/analysis/
4. Read PROBABILISTIC_REASONING.md

## Key Takeaways

**Optimal Timing**: Ticks 200-500 (19.9% win rate ≈ break-even)

**Best Features**: age, ticks_since_peak, distance_from_peak, volatility_10

**Breakeven**: 16.67% win probability for 5x payout

**Current Performance**: 17.4% overall → slightly positive EV

**Improvement Potential**: 22-25% win rate with feature filtering

**Bet Sizing**: 1-2% of bankroll (1/4 Kelly)

---

**Created**: January 7, 2026  
**Author**: rugs-expert (Claude Code Agent)  
**License**: Proprietary (VECTRA-PLAYER project)
