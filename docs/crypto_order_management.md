# Crypto Bot Order Management - Implementation Summary

## Problem Solved
Alpaca doesn't support bracket orders (`order_class='bracket'`) for cryptocurrency trading.

## Solution Implemented
Replace bracket orders with **separate stop loss and take profit orders** + automatic order management.

## How It Works

### 1. Order Placement (3-Step Process)
```python
# Step 1: Place market entry order
entry_order = api.submit_order(symbol, qty, side='buy', type='market')

# Step 2: Place stop loss (opposite side)
sl_order = api.submit_order(symbol, qty, side='sell', type='stop', stop_price=SL)

# Step 3: Place take profit (opposite side)  
tp_order = api.submit_order(symbol, qty, side='sell', type='limit', limit_price=TP)
```

### 2. Order Tracking
- Store `sl_order.id` and `tp_order.id`
- Bot tracks which orders are active

### 3. Automatic Cleanup
```python
def check_and_cleanup_orders():
    # If position closed (TP or SL filled):
    if no_position:
        cancel_all_orders()  # Cancel the unfilled order
        clear_order_tracking()
```

## Key Features

✅ **Orders Persist** - Survive bot restarts (Alpaca manages them)  
✅ **Automatic Execution** - Alpaca monitors and fills orders  
✅ **Orphan Prevention** - Cleanup logic prevents unwanted re-entries  
✅ **Strategy Unchanged** - Entry logic stays exactly the same  

## What Happens in Different Scenarios

### Scenario 1: Take Profit Hits
1. TP order fills → position closed
2. Bot detects no position
3. Bot cancels SL order
4. ✅ Clean state, ready for next trade

### Scenario 2: Stop Loss Hits
1. SL order fills → position closed
2. Bot detects no position
3. Bot cancels TP order
4. ✅ Clean state, ready for next trade

### Scenario 3: Bot Restarts Mid-Trade
1. Bot starts up
2. Checks current position
3. If position exists: orders still active (Alpaca manages them)
4. If no position: cleanup any orphaned orders
5. ✅ No manual monitoring needed

### Scenario 4: Both Orders Active, Price Whipsaws
- **Rare edge case:** Price hits SL, then quickly reverses to TP
- SL fills first → position closed
- Bot cancels TP before it can fill
- ✅ Prevented by cleanup logic running every minute

## Bots Updated

1. ✅ `live_btc_5m_fib_zigzag.py` - DONE
2. ⏳ `live_eth_5m_fib_zigzag.py` - TODO
3. ⏳ `live_btc_15m_squeeze_pro.py` - TODO  
4. ⏳ `live_btc_5m_scalp_z.py` - TODO

## Advantages Over Manual Monitoring

| Feature | Separate Orders | Manual Monitoring |
|---------|----------------|-------------------|
| Survives restart | ✅ Yes | ❌ No |
| Alpaca executes | ✅ Yes | ❌ Bot must check |
| State persistence | ✅ Alpaca | ❌ Bot memory |
| Complexity | ✅ Low | ❌ High |
| Bug risk | ✅ Low | ❌ High |

## Code Changes Summary

### Added Methods:
- `cancel_all_orders()` - Cancel all open orders for symbol
- `check_and_cleanup_orders()` - Cleanup orphaned orders

### Modified Methods:
- `place_order()` - Now places 3 separate orders instead of 1 bracket
- `__init__()` - Added order tracking variables
- `run_strategy()` - Added cleanup calls

### Added Variables:
- `self.active_sl_order` - Track stop loss order ID
- `self.active_tp_order` - Track take profit order ID

## Testing Checklist

- [ ] Entry order places successfully
- [ ] SL order places after entry
- [ ] TP order places after entry
- [ ] When TP fills, SL gets cancelled
- [ ] When SL fills, TP gets cancelled
- [ ] Bot restart doesn't create duplicate orders
- [ ] Orphaned orders get cleaned up

---

**Status:** Implementation in progress  
**Next:** Apply to remaining 3 crypto bots
