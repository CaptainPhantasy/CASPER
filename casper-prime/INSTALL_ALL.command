#!/bin/bash
# CASPER Prime Complete Setup Script

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         🚀 CASPER PRIME SETUP COMPLETE                     ║"
echo "║           All Launch Options Installed                      ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Copy launchers to Desktop for easy access
cp "/Volumes/Storage/Development/CASPER DEV/casper-prime/CASPER Prime.command" "$HOME/Desktop/CASPER Prime.command" 2>/dev/null
cp "/Volumes/Storage/Development/CASPER DEV/casper-prime/StartMenuBar.command" "$HOME/Desktop/CASPER MenuBar.command" 2>/dev/null

# Create app alias in Applications folder
ln -sf "/Applications/CASPER Prime.app" "$HOME/Desktop/CASPER Prime App" 2>/dev/null

echo "✅ Installation Complete!"
echo ""
echo "You now have 3 ways to launch CASPER Prime:"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🖱️  OPTION 1: Desktop Shortcut (Simplest)"
echo "   • Double-click 'CASPER Prime' on your Desktop"
echo "   • Terminal opens, services start, browser launches"
echo "   • Uses ports 8742 & 9318"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "🔝  OPTION 2: Menu Bar App (Most Convenient)"
echo "   • Double-click 'CASPER MenuBar' on your Desktop"
echo "   • Look for 🤖 icon in top-right menu bar"
echo "   • Click icon to start/stop services"
echo "   • Submit tasks directly from menu"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📱  OPTION 3: macOS Application (Professional)"
echo "   • Open Applications folder"
echo "   • Double-click 'CASPER Prime'"
echo "   • Or drag to Dock for permanent access"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📝  HOW TO USE:"
echo "   1. Launch using any method above"
echo "   2. Browser opens to dashboard automatically"
echo "   3. Type your task: 'Build a user authentication system'"
echo "   4. Watch AI agents work autonomously!"
echo ""
echo "💡  TIP: The Menu Bar app stays running even when you close windows"
echo ""
echo "Press Enter to continue..."
read
