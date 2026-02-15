# Chrome Profile Configuration for VECTRA-PLAYER

## ⚠️ IMPORTANT: USE ONLY THE `rugs_bot` PROFILE

**DO NOT use the Default Chrome profile.** It has CDP binding issues.

```
REQUIRED PROFILE: rugs_bot
PROFILE PATH:     ~/.gamebot/chrome_profiles/rugs_bot/
CONFIG DEFAULT:   CHROME_PROFILE=rugs_bot (in src/config.py)
```

---

## Current Setup (January 2, 2026)

The `rugs_bot` profile is fully configured with:
- ✅ Phantom wallet extension installed
- ✅ Wallet connected to rugs.fun
- ✅ CDP (Chrome DevTools Protocol) works correctly

**This is the ONLY profile that should be used for VECTRA-PLAYER.**

---

## Overview

VECTRA-PLAYER uses Chrome DevTools Protocol (CDP) to:
1. Connect to a running Chrome instance
2. Intercept WebSocket traffic from rugs.fun
3. Automate trading button clicks

---

## How It Works

1. **VECTRA-PLAYER starts** → checks if Chrome is running on CDP port 9222
2. **Launches Chrome** with `--remote-debugging-port=9222` using rugs_bot profile
3. **Connects via CDP** using Playwright
4. **Navigates to rugs.fun** and waits for Phantom wallet to inject
5. **Intercepts WebSocket traffic** for game state updates
6. **Clicks buttons** in the browser when you click in the GUI

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_PROFILE` | `rugs_bot` | **DO NOT CHANGE** |
| `CDP_PORT` | `9222` | Chrome DevTools Protocol port |
| `CHROME_BINARY` | (auto-detect) | Path to Chrome binary |

---

## If You Need to Reinstall Phantom

If the profile gets corrupted or you need to set up on a new machine:

```bash
# 1. Close all Chrome windows
pkill -f chrome

# 2. Launch Chrome with the rugs_bot profile manually
google-chrome --user-data-dir="$HOME/.gamebot/chrome_profiles/rugs_bot" --no-first-run

# 3. Install Phantom extension from Chrome Web Store
#    https://chrome.google.com/webstore/detail/phantom/bfnaelmomeimhlpmgjnjophhpkkoljpa

# 4. Import/connect your wallet in Phantom

# 5. Navigate to rugs.fun and verify wallet connects

# 6. Close Chrome completely

# 7. Now VECTRA-PLAYER will use this profile
```

---

## Troubleshooting

### "Wallet extensions not available"

1. **Check profile has Phantom installed:**
   ```bash
   ls ~/.gamebot/chrome_profiles/rugs_bot/Default/Extensions/bfnaelmomeimhlpmgjnjophhpkkoljpa
   # Should show version directories
   ```

2. **Reinstall Phantom** using the steps above

### "CDP connection failed"

1. **Kill ALL Chrome processes first:**
   ```bash
   pkill -9 -f chrome
   ```

2. **Check nothing is using port 9222:**
   ```bash
   ss -tlnp | grep 9222
   ```

3. **Try again** - the browser manager cleans up stale lock files automatically

### "Opening in existing browser session"

This means Chrome is already running. Close ALL Chrome windows or:
```bash
pkill -9 -f chrome
```

---

## File Locations

| Item | Path |
|------|------|
| Profile directory | `~/.gamebot/chrome_profiles/rugs_bot/` |
| Extensions | `~/.gamebot/chrome_profiles/rugs_bot/Default/Extensions/` |
| Phantom extension | `~/.gamebot/chrome_profiles/rugs_bot/Default/Extensions/bfnaelmomeimhlpmgjnjophhpkkoljpa/` |

## Phantom Extension ID

`bfnaelmomeimhlpmgjnjophhpkkoljpa`

---

## Why Not Use the Default Profile?

The Default Chrome profile (`~/.config/google-chrome/`) has CDP binding issues on this machine. When Chrome is launched with `--remote-debugging-port=9222`, the port never starts listening. The exact cause is unknown, but the `rugs_bot` dedicated profile works correctly.

**Do not attempt to "fix" this by switching to the Default profile.**
