#!/bin/bash
# Fix VPS deployment issues

echo "🔧 FIXING VPS DEPENDENCIES AND PATH ISSUES"
echo "==========================================="

cd /home/trader/trading-bots

# 1. Install missing packages
echo ""
echo "📦 Installing missing packages..."
pip install loguru

# 2. Verify other dependencies
echo ""
echo "📦 Verifying other packages..."
pip install alpaca-trade-api pandas numpy schedule pytz python-dateutil

# 3. Fix Python path issues by adding project root to PYTHONPATH
echo ""
echo "🔧 Setting PYTHONPATH..."
export PYTHONPATH="/home/trader/trading-bots:$PYTHONPATH"
echo "export PYTHONPATH=\"/home/trader/trading-bots:\$PYTHONPATH\"" >> ~/.bashrc

echo ""
echo "✅ Dependencies installed!"
echo ""
echo "🔄 Now restart the bots:"
echo "   python grok/live_bots/run_all_live_bots.py"
echo "   > start_all"

