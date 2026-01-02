#!/bin/bash
# Setup script for Pyright LSP with Claude Code
# Run this in a separate terminal, then restart Claude Code

echo "=========================================="
echo "Pyright LSP Setup for Claude Code"
echo "=========================================="

# 1. Verify pyright is installed
echo ""
echo "[1/4] Checking pyright installation..."
if command -v pyright &> /dev/null; then
    echo "  ✅ pyright found: $(which pyright)"
    echo "  ✅ version: $(pyright --version)"
else
    echo "  ❌ pyright not found. Installing..."
    npm install -g pyright
fi

# 2. Verify pyright-langserver
echo ""
echo "[2/4] Checking pyright-langserver..."
if command -v pyright-langserver &> /dev/null; then
    echo "  ✅ pyright-langserver found: $(which pyright-langserver)"
else
    echo "  ❌ pyright-langserver not found"
    echo "  Installing pyright globally should include it"
    npm install -g pyright
fi

# 3. Test pyright on the project
echo ""
echo "[3/4] Testing pyright on VECTRA-PLAYER..."
cd /home/nomad/Desktop/VECTRA-PLAYER
pyright --version
echo "  Running quick check on src/config.py..."
pyright src/config.py 2>&1 | head -20

# 4. Instructions for Claude Code
echo ""
echo "[4/4] Claude Code Setup Instructions"
echo "=========================================="
echo ""
echo "The ENABLE_LSP_TOOLS environment variable may help."
echo "To start Claude Code with LSP enabled:"
echo ""
echo "  ENABLE_LSP_TOOLS=1 claude"
echo ""
echo "Or add to your ~/.bashrc or ~/.zshrc:"
echo ""
echo "  export ENABLE_LSP_TOOLS=1"
echo ""
echo "After making changes, RESTART Claude Code to detect the LSP server."
echo ""
echo "=========================================="
echo "To test in Claude Code, ask Claude to:"
echo "  'Use LSP hover on src/config.py line 1 character 10'"
echo "=========================================="

# Optional: Add to shell config
read -p "Add ENABLE_LSP_TOOLS=1 to ~/.bashrc? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if ! grep -q "ENABLE_LSP_TOOLS" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# Enable LSP tools for Claude Code" >> ~/.bashrc
        echo "export ENABLE_LSP_TOOLS=1" >> ~/.bashrc
        echo "  ✅ Added to ~/.bashrc"
        echo "  Run: source ~/.bashrc"
    else
        echo "  ⚠️  ENABLE_LSP_TOOLS already in ~/.bashrc"
    fi
fi

echo ""
echo "Done! Restart Claude Code to apply changes."
