# Position Sizing Configuration Guide

## Overview

This guide explains how to configure position sizing for all trading bots. Position sizing determines how much capital to risk per trade based on your account size and risk tolerance.

---

## Position Sizing Methods

### 1. **Fixed Percentage of Equity** (Recommended)
Risk a fixed percentage of your account equity per trade.

```python
# Example: Risk 2% of equity per trade
account_equity = 100000  # $100k
risk_per_trade = 0.02    # 2%
risk_amount = account_equity * risk_per_trade  # $2,000
```

### 2. **Fixed Dollar Amount**
Risk a fixed dollar amount per trade.

```python
# Example: Risk $1,000 per trade
risk_amount = 1000
```

### 3. **Volatility-Based (ATR)**
Adjust position size based on market volatility.

```python
# Example: Risk based on ATR
atr = calculate_atr(df)
risk_amount = account_equity * 0.02
position_size = risk_amount / atr
```

---

## Configuration File: `config/position_sizing.yaml`

Create this file to centralize all position sizing settings:

```yaml
# Position Sizing Configuration
# Edit these values to adjust risk per bot

# Global Settings
global:
  default_risk_pct: 0.02          # 2% of equity per trade
  max_position_pct: 0.10          # Max 10% of equity in one position
  use_volatility_adjustment: true  # Adjust for ATR/volatility

# Long-Term Bots (1h+)
long_term:
  eth_1h:
    risk_pct: 0.03               # 3% risk (higher conviction)
    max_position_pct: 0.15
    
  eth_4h:
    risk_pct: 0.025              # 2.5% risk
    max_position_pct: 0.12
    
  nvda_1h:
    risk_pct: 0.02               # 2% risk
    max_position_pct: 0.10

# Scalping Bots (<1h)
scalping:
  btc_combo:
    risk_pct: 0.015              # 1.5% risk (more frequent trades)
    max_position_pct: 0.08
    
  btc_combo_momentum:
    risk_pct: 0.015
    max_position_pct: 0.08
    
  eth_vol:
    risk_pct: 0.02
    max_position_pct: 0.10
    
  gld_5m_candlestick:
    risk_pct: 0.01               # 1% risk (very frequent)
    max_position_pct: 0.05
    
  gld_5m_fib:
    risk_pct: 0.01
    max_position_pct: 0.05
    
  googl_15m_rsi:
    risk_pct: 0.015
    max_position_pct: 0.08
    
  tsla_15m_time:
    risk_pct: 0.015
    max_position_pct: 0.08
```

---

## Standard Position Sizing Function

Add this to each bot (or create a shared utility):

```python
def calculate_position_size(self, account_equity, entry_price, stop_loss_price, risk_pct=0.02):
    """
    Calculate position size based on risk management
    
    Args:
        account_equity: Total account equity
        entry_price: Planned entry price
        stop_loss_price: Stop loss price
        risk_pct: Percentage of equity to risk (default 2%)
    
    Returns:
        position_size: Number of shares/units to buy
    """
    # Calculate risk amount in dollars
    risk_amount = account_equity * risk_pct
    
    # Calculate distance to stop loss
    price_risk = abs(entry_price - stop_loss_price)
    
    # Avoid division by zero
    if price_risk == 0:
        logger.warning("Stop loss equals entry price, using default position size")
        return (account_equity * 0.05) / entry_price  # 5% of equity
    
    # Calculate position size
    position_size = risk_amount / price_risk
    
    # Apply maximum position size limit
    max_position_value = account_equity * self.max_position_pct
    max_position_size = max_position_value / entry_price
    
    # Use the smaller of the two
    final_position_size = min(position_size, max_position_size)
    
    logger.info(f"Position Sizing:")
    logger.info(f"  Risk Amount: ${risk_amount:,.2f} ({risk_pct*100}%)")
    logger.info(f"  Price Risk: ${price_risk:.2f}")
    logger.info(f"  Calculated Size: {position_size:.6f}")
    logger.info(f"  Max Size: {max_position_size:.6f}")
    logger.info(f"  Final Size: {final_position_size:.6f}")
    
    return final_position_size
```

---

## Example Implementation

### In Bot __init__:

```python
def __init__(self):
    # ... existing code ...
    
    # Position Sizing Parameters
    self.risk_per_trade = 0.02        # 2% of equity
    self.max_position_pct = 0.10      # Max 10% of equity
    self.use_volatility_adj = True    # Adjust for volatility
```

### In place_order Method:

```python
def place_order(self, side, entry_price, stop_loss_price):
    try:
        # Get account info
        account = self.api.get_account()
        equity = float(account.equity)
        
        # Calculate position size
        position_size = self.calculate_position_size(
            account_equity=equity,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            risk_pct=self.risk_per_trade
        )
        
        # Round to appropriate precision
        if 'BTC' in self.symbol or 'ETH' in self.symbol:
            position_size = round(position_size, 6)  # Crypto precision
        else:
            position_size = int(position_size)  # Stocks are whole shares
        
        # Place order
        order = self.api.submit_order(
            symbol=self.symbol,
            qty=position_size,
            side=side,
            type='limit',
            limit_price=entry_price,
            time_in_force='gtc'
        )
        
        logger.info(f"✅ Order placed: {side} {position_size} @ ${entry_price}")
        return True
        
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return False
```

---

## Risk Management Best Practices

### 1. **Never Risk More Than 2% Per Trade**
```python
# Good
self.risk_per_trade = 0.02  # 2%

# Risky
self.risk_per_trade = 0.10  # 10% - TOO HIGH!
```

### 2. **Set Maximum Position Size**
```python
# Limit total exposure
self.max_position_pct = 0.10  # Never more than 10% in one position
```

### 3. **Account for Volatility**
```python
# Reduce size in high volatility
if atr > atr_ma * 1.5:  # High volatility
    position_size *= 0.5  # Cut size in half
```

### 4. **Set Maximum Daily Loss**
```python
# Stop trading if daily loss exceeds limit
max_daily_loss = equity * 0.05  # 5% max daily loss
if daily_pnl < -max_daily_loss:
    logger.warning("Max daily loss reached, stopping trading")
    return
```

---

## Quick Reference Table

| Account Size | Risk % | Risk $ | Stop Loss | Position Size |
|--------------|--------|--------|-----------|---------------|
| $10,000 | 2% | $200 | $1 | 200 shares |
| $10,000 | 2% | $200 | $2 | 100 shares |
| $100,000 | 2% | $2,000 | $1 | 2,000 shares |
| $100,000 | 1% | $1,000 | $5 | 200 shares |

**Formula:** `Position Size = Risk Amount / Stop Loss Distance`

---

## Configuration Steps

### 1. Create Config File
```bash
mkdir -p config
nano config/position_sizing.yaml
# Paste the YAML configuration above
```

### 2. Update Each Bot
Add position sizing parameters to `__init__`:
```python
self.risk_per_trade = 0.02
self.max_position_pct = 0.10
```

### 3. Add Calculation Function
Copy the `calculate_position_size()` function to each bot.

### 4. Update Order Placement
Use the function in `place_order()` method.

### 5. Test
```python
# Test with small amounts first
self.risk_per_trade = 0.001  # 0.1% for testing
```

---

## Monitoring Position Sizing

### Check Logs
```bash
# Look for position sizing info
grep "Position Sizing" logs/*.log
```

### Dashboard
The dashboard shows:
- Current position size
- Entry price
- Unrealized P&L
- % of equity used

---

## Adjusting Risk

### Conservative (Recommended for beginners)
```python
self.risk_per_trade = 0.01  # 1%
self.max_position_pct = 0.05  # 5%
```

### Moderate (Recommended for most)
```python
self.risk_per_trade = 0.02  # 2%
self.max_position_pct = 0.10  # 10%
```

### Aggressive (Only for experienced)
```python
self.risk_per_trade = 0.03  # 3%
self.max_position_pct = 0.15  # 15%
```

---

## Common Mistakes to Avoid

❌ **Using fixed position sizes** (doesn't scale with account)  
❌ **Ignoring stop loss distance** (over-leveraging)  
❌ **No maximum position limit** (too much in one trade)  
❌ **Not accounting for volatility** (same size in all conditions)  

✅ **Use percentage-based sizing**  
✅ **Calculate based on stop loss**  
✅ **Set position limits**  
✅ **Adjust for market conditions**  

---

**Remember:** Position sizing is the most important aspect of risk management. Even the best strategy will fail with poor position sizing!
