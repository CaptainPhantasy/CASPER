#!/bin/bash

# Create desktop shortcut for CASPER Prime

DESKTOP_PATH="$HOME/Desktop"
CASPER_PATH="/Volumes/Storage/Development/CASPER DEV/casper-prime"

# Create an AppleScript application that can be double-clicked
cat > "$DESKTOP_PATH/CASPER Prime.command" << 'EOF'
#!/bin/bash

# CASPER Prime Launcher
# Uses obscure ports: 8742 (API) and 9318 (Dashboard)

clear
echo "╔═══════════════════════════════════════════╗"
echo "║         🚀 CASPER PRIME                    ║"
echo "║   Autonomous AI Development Platform       ║"
echo "╚═══════════════════════════════════════════╝"

cd "/Volumes/Storage/Development/CASPER DEV/casper-prime"

# Kill any existing processes on our ports
lsof -ti:8742 | xargs kill -9 2>/dev/null
lsof -ti:9318 | xargs kill -9 2>/dev/null

echo ""
echo "Starting CASPER Prime services..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Start backend
source venv/bin/activate 2>/dev/null
python -m core.server --port 8742 > /tmp/casper-backend.log 2>&1 &
echo "✓ Backend API running on port 8742"

sleep 2

# Start dashboard
cd dashboard
npm run dev -- --port 9318 > /tmp/casper-dashboard.log 2>&1 &
echo "✓ Dashboard running on port 9318"

sleep 3

# Open browser
echo ""
echo "🌐 Opening browser..."
open "http://localhost:9318"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CASPER Prime is ready!"
echo ""
echo "Just type what you want to build in the browser!"
echo ""
echo "Examples:"
echo "  • Build a user authentication system"
echo "  • Create a REST API for blog posts"
echo "  • Add real-time chat to my app"
echo ""
echo "Press Ctrl+C to stop CASPER Prime"

# Keep terminal open
while true; do
    sleep 1
done
EOF

# Make it executable
chmod +x "$DESKTOP_PATH/CASPER Prime.command"

echo "✅ Desktop shortcut created!"
echo ""
echo "You can now:"
echo "  1. Double-click 'CASPER Prime' on your Desktop"
echo "  2. The terminal will open and start everything"
echo "  3. Your browser will open automatically"
echo "  4. Just type what you want to build!"
echo ""
echo "Using ports 8742 and 9318 (unlikely to conflict)"
