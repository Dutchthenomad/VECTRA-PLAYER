# Seed Bruteforce Analysis Tool

Analyzes game seeds from recorded data to detect patterns that could indicate predictable seeding.

## Features

### Hex64 Format Verification
- Validates all seeds are proper SHA-256 hex format (64 characters)
- Detects any seeds with invalid length or characters

### Timestamp Correlation Analysis
- Checks if game timestamps appear in seed values
- Calculates Pearson correlation between timestamps and seed prefixes
- Low correlation (~0) indicates no direct timestamp seeding

### Sequential Pattern Detection
- Sorts games by timestamp and compares consecutive seed prefixes
- Detects if seeds increment predictably between games
- Sequential patterns could indicate weak PRNG

### Entropy Analysis
- Calculates Shannon entropy for each seed
- Expected entropy for random hex: ~4.0 bits/character
- Flags seeds with suspiciously low entropy (<3.5)

## Usage

1. Load the games dataset:
   - Click the upload area or drag-drop `games_dataset.jsonl`
   - Located at: `src/rugs_recordings/PRNG CRAK/games_dataset.jsonl`

2. Select analysis type via radio buttons

3. Click "Run Analysis" to execute

4. Review results in the table and summary sections

## Data Format

Input JSONL format (one JSON object per line):

```json
{
    "game_id": "20251221-343db32e1016412e",
    "timestamp_ms": 1766354408423,
    "server_seed": "e9cdaf558aada61213b2ef434ec4e811c3af7ccde29a2f66b50df0f07b2a0b6d",
    "server_seed_hash": "8cc2bab9e7fa24d16fce964233a25ac2d2372923b80435c36c6441053bdae2e0",
    "peak_multiplier": 1.117959540398272,
    "final_price": 0.00344246121039787,
    "tick_duration": 436,
    "rugged": true
}
```

## Interpretation Guide

### Good Signs (Hard to Predict)
- All seeds valid hex64 format ✓
- Timestamp correlation near 0 ✓
- No sequential patterns ✓
- Average entropy ~4.0 bits/char ✓

### Warning Signs (Potentially Predictable)
- Timestamp correlation > 0.5 ⚠️
- Multiple sequential patterns ⚠️
- Low entropy seeds (<3.5) ⚠️
- Invalid seed formats ⚠️

## Live Mode

When connected to Foundation Service, the tool also captures live game IDs for comparison with historical patterns.

## Related Files

- `src/rugs_recordings/PRNG CRAK/HAIKU-CRITICAL-FINDINGS.md` - Prediction algorithms
- `src/rugs_recordings/PRNG CRAK/prediction_engine/` - Python implementations
- `src/rugs_recordings/PRNG CRAK/games_dataset.jsonl` - Historical game data
