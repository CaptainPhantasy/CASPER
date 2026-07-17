#!/bin/bash

# Script to start both dashboard and backend servers for testing

# Start CASPER backend server in background
cd ../ && python3 -m core.server &
BACKEND_PID=$!

# Give the backend a moment to start
sleep 3

# Start dashboard preview server in background
cd dashboard && npx vite preview --port 4173 &
DASHBOARD_PID=$!

# Wait for both processes
wait $BACKEND_PID $DASHBOARD_PID