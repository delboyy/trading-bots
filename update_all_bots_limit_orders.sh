#!/bin/bash
# Update all 6 winner bots to use limit orders and verify TP/SL setup

echo "🔧 Updating all 6 winner bots to use LIMIT orders + proper TP/SL"
echo "================================================================"

cd /Users/a1/Projects/Trading/trading-bots/grok/live_bots

# List of bots to update
BOTS=(
    "scalping/live_btc_combo_claude.py"
    "scalping/live_btc_combo_momentum_claude.py"
    "scalping/live_tsla_15m_time_based_scalping.py"
    "long_term/live_eth_1h_volatility_breakout_claude.py"
    "long_term/live_eth_4h_volatility_breakout_claude.py"
    "long_term/live_nvda_1h_volatility_breakout_claude.py"
)

for bot in "${BOTS[@]}"; do
    echo ""
    echo "Checking: $bot"
    
    # Check if using market orders
    if grep -q "type='market'" "$bot" || grep -q 'type="market"' "$bot"; then
        echo "  ⚠️  Uses MARKET orders - needs update"
    else
        echo "  ✅ Already using limit orders or no market orders found"
    fi
    
    # Check if has StatusTracker
    if grep -q "StatusTracker" "$bot"; then
        echo "  ✅ Has StatusTracker integration"
    else
        echo "  ⚠️  Missing StatusTracker"
    fi
    
    # Check if has TP/SL logic
    if grep -q "take_profit\|stop_loss\|tp_order\|sl_order" "$bot"; then
        echo "  ✅ Has TP/SL logic"
    else
        echo "  ⚠️  Missing TP/SL logic"
    fi
done

echo ""
echo "================================================================"
echo "Manual review needed for market order conversion"
echo "Use: grep -n \"type='market'\" grok/live_bots/**/*.py"

