#!/usr/bin/env python3
"""
Batch update all bots to use limit orders
"""

from pathlib import Path
import re

def update_bot_file(file_path):
    """Update a single bot file"""
    print(f"\nProcessing: {file_path.name}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original = content
    
    # Step 1: Update place_order signature to include current_price
    content = re.sub(
        r'def place_order\(self, side: str, qty: float\) -> bool:',
        'def place_order(self, side: str, qty: float, current_price: float = None) -> bool:',
        content
    )
    
    # Step 2: Replace market order docstring
    content = content.replace(
        '"""Place a market order"""',
        '"""Place a LIMIT order (0.01% fee vs 0.035% market)"""'
    )
    
    # Step 3: Add price fetching logic if current_price is None
    if "def place_order" in content and "current_price is None" not in content:
        # Find the place_order function and add price fetching
        pattern = r'(def place_order\(self, side: str, qty: float, current_price: float = None\) -> bool:\s+"""[^"]+"""\s+try:)'
        replacement = r'''\1
            # Get current price if not provided
            if current_price is None:
                quote = self.api.get_latest_crypto_quote(self.symbol) if '/' in self.symbol else self.api.get_latest_quote(self.symbol)
                current_price = float(quote.ap) if hasattr(quote, 'ap') else float(quote.askprice)
            
            # Place limit order slightly favorable for quick fill
            if side == 'buy':
                limit_price = current_price * 1.0005  # 0.05% above for quick fill
            else:  # sell
                limit_price = current_price * 0.9995  # 0.05% below for quick fill
            
            limit_price = round(limit_price, 2)
'''
        content = re.sub(pattern, replacement, content)
    
    # Step 4: Replace type='market' with type='limit' + limit_price
    content = re.sub(
        r"type='market',\s*time_in_force='gtc'",
        "type='limit',\n                limit_price=limit_price,\n                time_in_force='gtc'",
        content
    )
    
    # Step 5: Update place_order calls to pass current_price
    content = re.sub(
        r'self\.place_order\((side, qty_to_close|side, qty)\)(\s+self\.position)',
        r'self.place_order(\1, current_price)\2',
        content
    )
    
    # Step 6: Update logging messages
    content = content.replace(
        "Placed {side} order for {qty}",
        "Placed {side} LIMIT order for {qty} @ ${limit_price}"
    )
    
    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  ✅ Updated to use limit orders")
        return True
    else:
        print(f"  ℹ️  No changes made")
        return False

def main():
    base = Path("/Users/a1/Projects/Trading/trading-bots/grok/live_bots")
    
    bots = [
        base / "long_term/live_nvda_1h_volatility_breakout_claude.py",
        base / "scalping/live_tsla_15m_time_based_scalping.py",
    ]
    
    print("="*80)
    print("🔧 BATCH UPDATE TO LIMIT ORDERS")
    print("="*80)
    
    for bot in bots:
        if bot.exists():
            update_bot_file(bot)
    
    print("\n" + "="*80)
    print("✅ COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()

