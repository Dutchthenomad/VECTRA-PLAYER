# PRNG / Server Treasury Pattern Exploration

**Date:** January 10, 2026
**Status:** EXPLORATORY - Not for v1 model
**Purpose:** Document patterns for future investigation

---

## Major Discovery: The 0.02 Ceiling

### Finding
**NO games end with a final price above 0.02.** This appears to be a server-side liquidation floor.

### The Two Game Types

| Type | Count | Final Price | Avg Duration | Avg Peak | Decay Rate |
|------|-------|-------------|--------------|----------|------------|
| Ceiling | 130 (15%) | = 0.02 | 137 ticks | 8.36x | 1.29/tick |
| Normal | 746 (85%) | < 0.02 | 214 ticks | 4.75x | 0.45/tick |

### Statistical Significance

| Feature | t-statistic | p-value | Significant? |
|---------|-------------|---------|--------------|
| Duration | -4.21 | 0.0000 | *** |
| Ticks after peak | -5.20 | 0.0000 | *** |
| Decay rate | +3.31 | 0.0010 | *** |
| Peak | +1.85 | 0.0640 | marginal |

### Pattern Description

```
CEILING GAMES ("Fast Mooners"):
  - High peak (8.36x avg)
  - Short duration (137 ticks)
  - Rapid decay (1.29 per tick)
  - Hit 0.02 floor → forced liquidation

NORMAL GAMES ("Slow Grinders"):
  - Lower peak (4.75x avg)
  - Longer duration (214 ticks)
  - Gradual decay (0.45 per tick)
  - End below 0.02 → natural decay
```

### Decay Rate → Ceiling Probability

| Decay Rate | Games | % Hit Ceiling |
|------------|-------|---------------|
| 0.00-0.01 | 98 | 0.0% |
| 0.01-0.05 | 267 | 3.7% |
| 0.05-0.10 | 114 | 16.7% |
| 0.10-0.50 | 215 | 25.1% |
| 0.50-1.00 | 100 | 25.0% |
| 1.00+ | 71 | 25.4% |

---

## Cross-Game Correlation Analysis

### Hypothesis
Long/high games → short following games (server treasury balancing)

### Findings
**Weak to no correlation detected in this dataset:**

| Correlation | Value | p-value |
|-------------|-------|---------|
| Prev duration → Current duration | +0.039 | 0.25 |
| Prev peak → Current duration | -0.002 | 0.96 |
| Prev peak → Current peak | -0.011 | n/a |

### After Long Games (>285 ticks)
- Next game avg: 217 ticks
- % short (<55 ticks): 17.6%

### After Short Games (<55 ticks)
- Next game avg: 195 ticks
- % long (>285 ticks): 23.6%

**Conclusion:** No strong evidence of treasury-balancing cross-game correlation in this sample. May need larger dataset or different time window.

---

## Final Price Remainder Patterns

### Distribution
- Mean: 0.0135
- Median: 0.0143
- Range: 0.00036 - 0.02000 (hard ceiling)
- Std: 0.0056

### Bucket Analysis
| Range | Games | % |
|-------|-------|---|
| < 0.001 | 6 | 0.7% |
| 0.001-0.01 | 241 | 27.1% |
| 0.01-0.02 | 641 | 72.2% |
| > 0.02 | 0 | 0.0% |

### Linear Regression (Normal Games)
```
final_price ~ peak + duration + ticks_after_peak

R² = 0.30 (moderate fit)

Coefficients:
  peak:             +0.000050
  duration:         -0.000005
  ticks_after_peak: -0.000017
  intercept:        +0.014544
```

---

## Implications for Strategy

### For Sidebets
1. **Ceiling games are unpredictable** - fast mooners can rug anytime
2. **Normal games give more time** - more betting windows
3. **Early detection possible?** - high initial volatility may predict ceiling game

### For Trading
1. **Ceiling games = risky holds** - fast rug after peak
2. **Normal games = safer 2x exits** - more time to exit profitably
3. **Peak detection matters** - exit before rapid decay

### Potential Features for Future Models
- `is_ceiling_candidate`: Based on early volatility/price action
- `decay_rate_estimate`: Rolling estimate of current decay
- `peak_detection`: Has price started declining from peak?

---

## Unanswered Questions

1. **What triggers the 0.02 ceiling?**
   - Is it a fixed floor?
   - Is it based on aggregate player positions?
   - Is it related to server seed?

2. **Can ceiling games be predicted early?**
   - First 10-20 ticks pattern?
   - Volatility signature?

3. **Is there a time-of-day pattern?**
   - More ceiling games at certain hours?
   - Weekday vs weekend?

4. **Provably fair verification**
   - Can we correlate server seed to game type?
   - Is the PRNG truly random or structured?

---

## Data Locations

```
Training data: /home/devops/Desktop/VECTRA-PLAYER/Machine Learning/training_data/
Raw data:      ~/rugs_data/events_parquet/doc_type=complete_game/
```

---

## Next Steps (NOT FOR V1 MODEL)

1. Collect more games for statistical power
2. Analyze provably fair hashes for patterns
3. Study time-of-day effects
4. Build ceiling prediction model (separate from sidebet model)

---

*This exploration is documented for future reference.*
*V1 sidebet model will NOT use these patterns to ensure proper learning.*
