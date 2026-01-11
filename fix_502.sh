#!/bin/bash
# Quick Fix Script for 502 Bad Gateway
# Run this on your production server

echo "=========================================="
echo "PageCraft 502 Quick Fix Script"
echo "=========================================="
echo ""

# Navigate to project directory
cd /var/www/cms

echo "[1] Activating virtual environment..."
source venv/bin/activate

echo "[2] Installing any missing dependencies..."
pip install -r requirements.txt --quiet

echo "[3] Checking if app starts without errors..."
timeout 3 python -c "from app import create_app; app = create_app()" 2>&1

if [ $? -eq 0 ] || [ $? -eq 124 ]; then
    echo "[OK] App imports successfully"
else
    echo "[ERROR] App has import errors - check output above"
    exit 1
fi

echo ""
echo "[4] Restarting the application service..."
sudo systemctl restart cms

echo ""
echo "[5] Waiting 3 seconds for service to start..."
sleep 3

echo ""
echo "[6] Checking service status..."
sudo systemctl status cms --no-pager

echo ""
echo "=========================================="
echo "Fix complete!"
echo ""
echo "Try accessing your site now."
echo "If still getting 502, run: bash diagnose_502.sh"
echo ""
