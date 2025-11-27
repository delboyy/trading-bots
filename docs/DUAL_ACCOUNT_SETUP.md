# Dual-Account Trading Bot System

This system runs two separate groups of trading bots using two different Alpaca paper trading accounts.

## Account Separation

### Long-Term Account (1h+ timeframes)
- **Bots:** 15 bots with 1h, 4h, and 1d timeframes
- **Strategy:** Position trading, swing trading
- **Dashboard:** Port 8501
- **Tmux Session:** `longterm`

### Short-Term Account (<1h timeframes)
- **Bots:** 15 bots with 5m and 15m timeframes  
- **Strategy:** Scalping, day trading
- **Dashboard:** Port 8502
- **Tmux Session:** `shortterm`

## Setup Instructions

### 1. Create Two Alpaca Paper Accounts

1. Go to https://alpaca.markets
2. Create first account → Get API keys
3. Create second account (use `youremail+1@gmail.com`) → Get API keys

### 2. Set Environment Variables

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Long-term account (1h+ bots)
export APCA_LONGTERM_KEY="your_longterm_api_key_here"
export APCA_LONGTERM_SECRET="your_longterm_secret_key_here"

# Short-term account (<1h bots)
export APCA_SHORTTERM_KEY="your_shortterm_api_key_here"
export APCA_SHORTTERM_SECRET="your_shortterm_secret_key_here"
```

Then reload: `source ~/.bashrc` or `source ~/.zshrc`

### 3. Start the System

```bash
chmod +x start_dual_account_system.sh
./start_dual_account_system.sh
```

This creates 4 tmux sessions:
- `longterm` - Long-term bot controller
- `shortterm` - Short-term bot controller
- `dashboard_lt` - Long-term dashboard (port 8501)
- `dashboard_st` - Short-term dashboard (port 8502)

### 4. Access Dashboards

- **Long-term:** http://localhost:8501 (or http://your-vps-ip:8501)
- **Short-term:** http://localhost:8502 (or http://your-vps-ip:8502)

## Managing Sessions

### Attach to a Session
```bash
tmux attach -t longterm      # Long-term bots
tmux attach -t shortterm     # Short-term bots
tmux attach -t dashboard_lt  # Long-term dashboard
tmux attach -t dashboard_st  # Short-term dashboard
```

### Detach from Session
Press: `Ctrl+B`, then `D`

### List All Sessions
```bash
tmux list-sessions
```

### Stop Everything
```bash
./stop_all_sessions.sh
```

## Bot Controllers

### Long-Term Controller
**File:** `grok/live_bots/run_longterm_bots.py`

**Bots (15 total):**
- eth_1h, nvda_1h, btc_1h, meta_1h, xlk_1h (1-hour)
- slv_4h, gld_4h, eth_4h, tsla_4h, nq_4h, tsla_4h_le (4-hour)
- eth_1d, tsla_1d, nvda_1d, spy_1d (daily)

### Short-Term Controller
**File:** `grok/live_bots/run_shortterm_bots.py`

**Bots (15 total):**
- eth_5m, btc_5m, nvda_5m_squeeze, btc_5m_scalp_z, amd_5m_vol, msft_5m_rsi, msft_5m_winner, gld_5m_atr, gld_5m_fib, gld_5m_session, btc_5m_vwap (5-minute)
- btc_15m_squeeze, nvda_15m_squeeze, googl_15m_rsi, tsla_15m_time (15-minute)

## Commands in Each Controller

```
Available commands:
  start_all        - Start all bots
  stop_all         - Stop all bots
  status           - Show bot status
  monitor          - Monitor all logs
  monitor_errors   - Monitor only errors
  monitor_trades   - Monitor only trades
  monitor_info     - Monitor info logs
  start <bot_key>  - Start specific bot
  stop <bot_key>   - Stop specific bot
  exit             - Exit controller (bots keep running)
```

## Advantages of Dual-Account System

✅ **Isolated Capital** - Each strategy type has dedicated capital  
✅ **Clear Attribution** - Easy to see which timeframe performs better  
✅ **Independent Monitoring** - Separate dashboards for each  
✅ **Risk Isolation** - Issues in one group don't affect the other  
✅ **Easier Debugging** - Smaller groups to troubleshoot  
✅ **Flexible Testing** - Can pause one group independently  

## Troubleshooting

### Sessions Won't Start
- Check environment variables are set: `echo $APCA_LONGTERM_KEY`
- Verify tmux is installed: `tmux -V`
- Check for port conflicts: `lsof -i :8501` and `lsof -i :8502`

### Can't Access Dashboards
- Check firewall allows ports 8501 and 8502
- Verify Streamlit is running: `tmux attach -t dashboard_lt`
- Check VPS IP address is correct

### Bots Not Trading
- Verify API keys are correct in Alpaca dashboard
- Check market hours (stocks only trade 9:30 AM - 4:00 PM ET)
- Review bot logs in the tmux sessions

## File Structure

```
trading-bots/
├── grok/live_bots/
│   ├── run_all_live_bots.py      # Original (all 30 bots)
│   ├── run_longterm_bots.py      # Long-term only (15 bots)
│   ├── run_shortterm_bots.py     # Short-term only (15 bots)
│   └── live_*.py                 # Individual bot files
├── dashboard/
│   └── app.py                    # Streamlit dashboard
├── start_dual_account_system.sh  # Main setup script
├── stop_all_sessions.sh          # Stop all sessions
└── docs/
    └── DUAL_ACCOUNT_SETUP.md     # This file
```

## Monitoring Best Practices

1. **Check dashboards daily** - Review P&L and errors
2. **Monitor both accounts** - Compare performance
3. **Review logs weekly** - Look for patterns
4. **Adjust allocation** - Move capital to better performers
5. **Keep sessions alive** - Use tmux to survive disconnects

---

**Created:** 2025-11-27  
**Version:** 1.0
