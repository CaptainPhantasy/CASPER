#!/bin/bash
# CASPER Prime Quick Start

clear
echo "╔═══════════════════════════════════════════╗"
echo "║      🚀 STARTING CASPER PRIME             ║"  
echo "╚═══════════════════════════════════════════╝"
echo ""

# Go to project directory
cd "/Volumes/Storage/Development/CASPER DEV/casper-prime"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Make sure dependencies are installed
echo "Checking dependencies..."
pip install anthropic fastapi uvicorn rich python-dotenv requests --quiet

# Kill any existing processes on our ports
lsof -ti:8742 | xargs kill -9 2>/dev/null
lsof -ti:9318 | xargs kill -9 2>/dev/null

echo ""
echo "Starting services..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start the Python launcher script
python3 LaunchCasper.py
