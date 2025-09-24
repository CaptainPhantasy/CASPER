#!/bin/bash
#
# CASPER Prime App Builder
# Creates a clickable macOS application

APP_NAME="CASPER Prime"
APP_DIR="/Applications/CASPER Prime.app"
BASE_DIR="/Volumes/Storage/Development/CASPER DEV/casper-prime"

echo "🔨 Building CASPER Prime Application..."

# Create app structure
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Create the Info.plist
cat > "$APP_DIR/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>CASPER Prime</string>
    <key>CFBundleDisplayName</key>
    <string>CASPER Prime</string>
    <key>CFBundleIdentifier</key>
    <string>com.legacyai.casper-prime</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Create the launcher script
cat > "$APP_DIR/Contents/MacOS/launcher" << 'EOF'
#!/bin/bash

# CASPER Prime Launcher
# Obscure ports to avoid conflicts
API_PORT=8742
DASHBOARD_PORT=9318

# Find the Python virtual environment
BASE_DIR="/Volumes/Storage/Development/CASPER DEV/casper-prime"
cd "$BASE_DIR"

# Activate virtual environment
source venv/bin/activate

# Kill any existing CASPER processes
pkill -f "core.server"
pkill -f "npm run dev"

# Start backend API server
echo "Starting CASPER Prime backend on port $API_PORT..."
python -m core.server --port $API_PORT > /tmp/casper-backend.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start dashboard
echo "Starting dashboard on port $DASHBOARD_PORT..."
cd dashboard
npm run dev -- --port $DASHBOARD_PORT > /tmp/casper-dashboard.log 2>&1 &
DASHBOARD_PID=$!

# Wait for dashboard to start
sleep 3

# Open browser
open "http://localhost:$DASHBOARD_PORT"

# Show notification
osascript -e 'display notification "CASPER Prime is running! Click the browser to start building." with title "CASPER Prime" subtitle "Autonomous AI Development Platform"'

# Create a menu bar status item (optional)
osascript << 'APPLESCRIPT'
tell application "System Events"
    display dialog "CASPER Prime is running!" & return & return & "• API: Port 8742" & return & "• Dashboard: Port 9318" & return & return & "Enter tasks in your browser." buttons {"Stop CASPER"} default button 1
end tell
APPLESCRIPT

# Cleanup
kill $BACKEND_PID 2>/dev/null
kill $DASHBOARD_PID 2>/dev/null
EOF

# Make launcher executable
chmod +x "$APP_DIR/Contents/MacOS/launcher"

echo "✅ Application created at: $APP_DIR"
echo ""
echo "📱 You can now:"
echo "   1. Double-click 'CASPER Prime' in Applications folder"
echo "   2. Drag it to your Dock for easy access"
echo "   3. Add it to Login Items for startup launch"
