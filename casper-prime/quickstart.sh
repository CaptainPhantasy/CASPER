#!/bin/bash

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   ____    _    ____  ____  _____ ____    ____  ____      ║"
echo "║  / ___|  / \\  / ___||  _ \\| ____|  _ \\  |  _ \\|  _ \\     ║"
echo "║ | |     / _ \\ \\___ \\| |_) |  _| | |_) | | |_) | |_) |    ║"
echo "║ | |___ / ___ \\ ___) |  __/| |___|  _ <  |  __/|  _ <     ║"
echo "║  \\____/_/   \\_\\____/|_|   |_____|_| \\_\\ |_|   |_| \\_\\    ║"
echo "║                                                           ║"
echo "║         Autonomous AI Development Platform                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | grep -Po '(?<=Python )[\d.]+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required (found $python_version)"
    exit 1
fi

echo "✓ Python $python_version detected"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install package in development mode
echo "🔧 Installing CASPER Prime..."
pip install -e .

# Install dashboard dependencies
echo "📦 Installing dashboard dependencies..."
cd dashboard
npm install
cd ..

echo ""
echo "✅ CASPER Prime installation complete!"
echo ""
echo "🚀 Quick Start Commands:"
echo ""
echo "  1. Start the API server:"
echo "     python core/server.py"
echo ""
echo "  2. Start the dashboard (in another terminal):"
echo "     cd dashboard && npm run dev"
echo ""
echo "  3. Use the CLI:"
echo "     python -m core.cli task 'Your task description'"
echo ""
echo "  Example:"
echo "     python -m core.cli task 'Build a user authentication system with JWT'"
echo ""
echo "📚 Documentation: https://github.com/casper-prime/casper-prime"
echo "💬 Support: https://discord.gg/casper-prime"