#!/usr/bin/env python3
"""
Convert all market orders to limit orders in winner bots
Also ensures proper TP/SL setup (not OCO)
"""

import re
from pathlib import Path

def update_bot_to_limit_orders(file_path):
    """Convert market orders to limit orders in a bot file"""
    print(f"\nUpdating: {file_path.name}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original = content
    changes = []
    
    # Pattern 1: Market order submissions
    # Replace: type='market' with type='limit' + limit_price
    if "type='market'" in content:
        # Find the submit_order calls with market orders
        pattern = r"(self\.api\.submit_order\(\s*symbol=self\.symbol,\s*qty=\w+,\s*side='buy',\s*)type='market'(,\s*time_in_force='gtc'\s*\))"
        
        if re.search(pattern, content):
            # Add comment about limit orders
            content = content.replace(
                "# Place market order",
                "# Place LIMIT order (0.01% fee vs 0.035% market order)"
            )
            
            # Replace market with limit
            content = re.sub(
                r"type='market'",
                "type='limit',\n                limit_price=round(current_price * 0.9995, 2)  # Slightly below for quick fill",
                content,
                count=1  # Only replace first occurrence (entry order)
            )
            changes.append("✅ Converted entry order to limit")
        
        # Update logging messages
        content = content.replace(
            "Buying", "Buying (LIMIT)"
        ).replace(
            "Placing market buy", "Placing LIMIT buy"
        )
    
    # Pattern 2: Ensure TP/SL comments mention OCO limitation
    if "Place TP and SL" in content and "OCO" not in content:
        content = content.replace(
            "# Place TP and SL orders",
            "# Place TP and SL orders (separate orders, NOT OCO - Alpaca doesn't support OCO for crypto)"
        )
        changes.append("✅ Added OCO limitation comment")
    
    # Pattern 3: Check if update_bot_status or update_status exists
    if "update_bot_status" not in content and "update_status" not in content:
        changes.append("⚠️  WARNING: No StatusTracker integration found!")
    
    # Pattern 4: Ensure wait time after limit order
    if "time.sleep(2)" in content and "limit" in content:
        content = content.replace(
            "time.sleep(2)",
            "time.sleep(5)  # Limit orders may take longer to fill"
        )
        changes.append("✅ Increased wait time for limit order fills")
    
    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"  Changes made:")
        for change in changes:
            print(f"    {change}")
        return True
    else:
        print(f"  ✅ No changes needed (already updated)")
        return False

def main():
    print("="*80)
    print("🔧 CONVERTING ALL BOTS TO LIMIT ORDERS")
    print("="*80)
    
    base_path = Path("/Users/a1/Projects/Trading/trading-bots/grok/live_bots")
    
    bots_to_update = [
        base_path / "scalping/live_btc_combo_claude.py",
        base_path / "scalping/live_tsla_15m_time_based_scalping.py",
        base_path / "long_term/live_eth_1h_volatility_breakout_claude.py",
        base_path / "long_term/live_eth_4h_volatility_breakout_claude.py",
        base_path / "long_term/live_nvda_1h_volatility_breakout_claude.py",
    ]
    
    updated_count = 0
    for bot_path in bots_to_update:
        if bot_path.exists():
            if update_bot_to_limit_orders(bot_path):
                updated_count += 1
        else:
            print(f"\n❌ File not found: {bot_path}")
    
    print("\n" + "="*80)
    print(f"✅ COMPLETE: Updated {updated_count}/{len(bots_to_update)} bots")
    print("="*80)
    print("\n💡 Next steps:")
    print("1. Test each bot manually")
    print("2. Update run_all_live_bots.py with latest bot list")
    print("3. Deploy to VPS")

if __name__ == "__main__":
    main()

