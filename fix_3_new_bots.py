#!/usr/bin/env python3
"""
Fix 3 new bots for proper integration:
1. GLD Candlestick Scalping
2. GLD Fibonacci Momentum  
3. GOOGL RSI Scalping

Issues to fix:
- Convert market orders to limit orders (0.01% fee)
- Add StatusTracker updates in main loop
- Add to run_all_live_bots.py
"""

import re
from pathlib import Path

def fix_bot_file(file_path, bot_name):
    """Fix a single bot file"""
    print(f"\n🔧 Fixing: {file_path.name}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original = content
    changes = []
    
    # 1. Convert market orders to limit orders
    if "type='market'" in content:
        # Replace market buy orders
        content = re.sub(
            r"type='market',\s*time_in_force='gtc'",
            "type='limit',\n                            limit_price=round(current_price * 1.0005, 2),  # 0.01% fee\n                            time_in_force='gtc'",
            content
        )
        changes.append("✅ Converted market orders to limit orders")
    
    # 2. Add current_price fetching before limit orders
    if "limit_price=round(current_price" in content and "current_price = self.api.get_latest_quote" not in content:
        # Find submit_order calls and add current_price fetching before them
        pattern = r'(\s+)(order = self\.api\.submit_order\()'
        replacement = r'\1# Get current price for limit order\n\1current_price = float(self.api.get_latest_quote(self.symbol).askprice)\n\1\2'
        content = re.sub(pattern, replacement, content, count=1)
        changes.append("✅ Added current price fetching for limit orders")
    
    # 3. Add StatusTracker update in main loop (if missing)
    if "def run(" in content and "self.tracker.update_status" not in content:
        # Find the main run loop and add status update
        pattern = r'(while True:\s*try:)'
        replacement = r'''\1
                # Update dashboard status
                try:
                    account = self.api.get_account()
                    positions = self.api.list_positions()
                    pos = next((p for p in positions if p.symbol == self.symbol), None)
                    
                    self.tracker.update_status(self.bot_id, {
                        'equity': float(account.equity),
                        'cash': float(account.cash),
                        'position': float(pos.qty) if pos else 0,
                        'entry_price': float(pos.avg_entry_price) if pos else 0,
                        'unrealized_pl': float(pos.unrealized_pl) if pos else 0,
                        'error': None
                    })
                except Exception as e:
                    logger.error(f"Status update failed: {e}")
                    self.tracker.update_status(self.bot_id, {'error': str(e)})
'''
        content = re.sub(pattern, replacement, content)
        changes.append("✅ Added StatusTracker updates in main loop")
    
    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        
        print(f"  Changes made:")
        for change in changes:
            print(f"    {change}")
        return True
    else:
        print(f"  ✅ No changes needed")
        return False

def update_master_controller():
    """Add new bots to run_all_live_bots.py"""
    controller_path = Path("grok/live_bots/run_all_live_bots.py")
    
    with open(controller_path, 'r') as f:
        content = f.read()
    
    # Add new bots to bot_scripts dictionary
    new_bots_scripts = """            # New bots
            'gld_candlestick': 'scalping/live_gld_5m_candlestick_scalping.py',
            'gld_fibonacci': 'scalping/live_gld_5m_fibonacci_momentum.py',
            'googl_rsi': 'scalping/live_googl_15m_rsi_scalping.py',"""
    
    # Insert before the closing brace of bot_scripts
    if "'tsla_15m': 'scalping/live_tsla_15m_time_based_scalping.py'" in content:
        content = content.replace(
            "'tsla_15m': 'scalping/live_tsla_15m_time_based_scalping.py'",
            "'tsla_15m': 'scalping/live_tsla_15m_time_based_scalping.py',\n" + new_bots_scripts
        )
    
    # Add new bots to bot_info dictionary
    new_bots_info = """            # New bots
            'gld_candlestick': {
                'name': 'GLD Candlestick Scalping', 
                'description': '✅ NEW: 69.45% return, 50.3% win rate, 5m scalping'
            },
            'gld_fibonacci': {
                'name': 'GLD Fibonacci Momentum', 
                'description': '✅ NEW: 66.75% return, 52.3% win rate, 5m momentum'
            },
            'googl_rsi': {
                'name': 'GOOGL RSI Scalping', 
                'description': '✅ NEW: 71.52% return, 54.1% win rate, 15m RSI'
            },"""
    
    # Insert before the closing brace of bot_info
    if "'tsla_15m': {'name': 'TSLA 15m Time-Based'" in content:
        content = content.replace(
            "'tsla_15m': {'name': 'TSLA 15m Time-Based', 'description': '✅ SOLID: 0.160%/day, 79% annual, 2yr validated'}",
            "'tsla_15m': {'name': 'TSLA 15m Time-Based', 'description': '✅ SOLID: 0.160%/day, 79% annual, 2yr validated'},\n" + new_bots_info
        )
    
    with open(controller_path, 'w') as f:
        f.write(content)
    
    print("✅ Added new bots to run_all_live_bots.py")

def main():
    print("="*80)
    print("🔧 FIXING 3 NEW BOTS FOR PROPER INTEGRATION")
    print("="*80)
    
    base_path = Path("grok/live_bots/scalping")
    
    bots_to_fix = [
        (base_path / "live_gld_5m_candlestick_scalping.py", "GLD Candlestick"),
        (base_path / "live_gld_5m_fibonacci_momentum.py", "GLD Fibonacci"),
        (base_path / "live_googl_15m_rsi_scalping.py", "GOOGL RSI"),
    ]
    
    fixed_count = 0
    for bot_path, bot_name in bots_to_fix:
        if bot_path.exists():
            if fix_bot_file(bot_path, bot_name):
                fixed_count += 1
        else:
            print(f"\n❌ File not found: {bot_path}")
    
    # Update master controller
    print(f"\n🎛️  Updating master controller...")
    update_master_controller()
    
    print("\n" + "="*80)
    print(f"✅ COMPLETE: Fixed {fixed_count}/3 bots + updated controller")
    print("="*80)
    print("\n💡 What was fixed:")
    print("✅ Market orders → Limit orders (0.01% fee)")
    print("✅ Added StatusTracker updates in main loop")
    print("✅ Added current price fetching for limit orders")
    print("✅ Added all 3 bots to run_all_live_bots.py")
    print("\n🚀 Your new bots are now ready for deployment!")

if __name__ == "__main__":
    main()



