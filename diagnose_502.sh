#!/bin/bash
# 502 Bad Gateway Diagnostic Script
# Run this on your production server to diagnose the issue

echo "=========================================="
echo "PageCraft 502 Diagnostic Script"
echo "=========================================="
echo ""

# Step 1: Check if the service is running
echo "[1] Checking service status..."
sudo systemctl status cms

echo ""
echo "=========================================="
echo ""

# Step 2: Check recent logs for errors
echo "[2] Checking last 50 lines of service logs..."
sudo journalctl -u cms -n 50 --no-pager

echo ""
echo "=========================================="
echo ""

# Step 3: Check if gunicorn processes are running
echo "[3] Checking for gunicorn processes..."
ps aux | grep gunicorn | grep -v grep

echo ""
echo "=========================================="
echo ""

# Step 4: Try to start the app manually to see errors
echo "[4] Attempting manual start to see errors..."
echo "This will show any import or startup errors..."
cd /var/www/cms
source venv/bin/activate
timeout 5 python app.py 2>&1 || true

echo ""
echo "=========================================="
echo ""

# Step 5: Check nginx configuration
echo "[5] Checking nginx error log..."
sudo tail -n 30 /var/log/nginx/error.log

echo ""
echo "=========================================="
echo "Diagnostic complete!"
echo ""
echo "Common fixes:"
echo "1. If service is not running: sudo systemctl restart cms"
echo "2. If import errors: Check that all dependencies are installed in venv"
echo "3. If permission errors: Check file ownership in /var/www/cms"
echo ""
