#!/bin/bash
# FINAL VPS FIX - Run this on your VPS

echo "🔧 FINAL VPS FIX - COMPREHENSIVE SOLUTION"
echo "========================================"

cd /home/trader/trading-bots

# 1. Pull latest fixes
echo "📥 Pulling latest code..."
git pull

# 2. Install all required packages
echo "📦 Installing packages..."
pip install alpaca-trade-api pandas numpy schedule pytz python-dateutil

# 3. Set PYTHONPATH properly (critical!)
echo "🔧 Setting PYTHONPATH..."
export PYTHONPATH="/home/trader/trading-bots:$PYTHONPATH"
echo 'export PYTHONPATH="/home/trader/trading-bots:$PYTHONPATH"' >> ~/.bashrc

# 4. Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs

# 5. Test PYTHONPATH is working
echo "🧪 Testing PYTHONPATH..."
python3 -c "import sys; print('PYTHONPATH:', sys.path)" | grep trading-bots

if [ $? -eq 0 ]; then
    echo "✅ PYTHONPATH is working!"
else
    echo "❌ PYTHONPATH issue - manually run:"
    echo "   export PYTHONPATH=\"/home/trader/trading-bots:\$PYTHONPATH\""
fi

# 6. Test imports
echo "🧪 Testing imports..."
python3 -c "
try:
    from grok.utils.status_tracker import StatusTracker
    print('✅ StatusTracker import: OK')
except ImportError as e:
    print('⚠️  StatusTracker import failed, but fallback will work:', e)

try:
    from alpaca_trade_api.rest import REST
    print('✅ Alpaca API import: OK')
except ImportError as e:
    print('❌ Alpaca API import failed:', e)
    print('   Run: pip install alpaca-trade-api')
"

echo ""
echo "🚀 Starting bot controller..."
python3 grok/live_bots/run_all_live_bots.py
