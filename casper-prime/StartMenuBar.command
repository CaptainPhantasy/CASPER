#!/bin/bash
# CASPER Prime Menu Bar Launcher

cd "/Volumes/Storage/Development/CASPER DEV/casper-prime"
source venv/bin/activate

# Test the menu bar app
echo "╔═══════════════════════════════════════════╗"
echo "║      🚀 CASPER PRIME MENU BAR APP          ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "Starting CASPER Prime in your menu bar..."
echo "Look for the 🤖 icon in the top-right corner"
echo ""
echo "Features:"
echo "  • Click to start/stop services"
echo "  • Submit tasks directly from menu"
echo "  • View logs and settings"
echo ""

python CasperMenuBar.py
