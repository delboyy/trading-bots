# Quick Reference: Dual-Account Trading System

## 🚀 Quick Start

```bash
# 1. Set your API keys (one-time setup)
export APCA_LONGTERM_KEY="pk_xxxxx"
export APCA_LONGTERM_SECRET="sk_xxxxx"
export APCA_SHORTTERM_KEY="pk_yyyyy"
export APCA_SHORTTERM_SECRET="sk_yyyyy"

# 2. Start everything
./start_dual_account_system.sh

# 3. Access dashboards
# Long-term:  http://localhost:8501
# Short-term: http://localhost:8502
```

## 📊 Bot Distribution

| Account | Bots | Timeframes | Strategy Type |
|---------|------|------------|---------------|
| Long-term | 15 | 1h, 4h, 1d | Swing/Position |
| Short-term | 15 | 5m, 15m | Scalping/Day |

## ⌨️ Tmux Commands

```bash
# Attach to sessions
tmux attach -t longterm      # Long-term bots
tmux attach -t shortterm     # Short-term bots
tmux attach -t dashboard_lt  # LT dashboard
tmux attach -t dashboard_st  # ST dashboard

# Detach: Ctrl+B, then D

# List sessions
tmux list-sessions

# Stop everything
./stop_all_sessions.sh
```

## 🎮 Bot Controller Commands

```
start_all        - Start all bots in this group
stop_all         - Stop all bots
status           - Show status
monitor          - Live logs (all)
monitor_errors   - Live logs (errors only)
monitor_trades   - Live logs (trades only)
exit             - Exit (bots keep running)
```

## 📁 Files

```
run_longterm_bots.py   - Long-term controller (15 bots)
run_shortterm_bots.py  - Short-term controller (15 bots)
run_all_live_bots.py   - Original (all 30 bots)
```

## 🔧 Troubleshooting

```bash
# Check if sessions are running
tmux list-sessions

# View session
tmux attach -t longterm

# Kill stuck session
tmux kill-session -t longterm

# Check ports
lsof -i :8501
lsof -i :8502

# Restart everything
./stop_all_sessions.sh
./start_dual_account_system.sh
```

## 💡 Tips

- Each account has $100k paper capital
- Crypto bots run 24/7
- Stock bots only trade 9:30 AM - 4:00 PM ET
- Dashboards auto-refresh every 30 seconds
- Logs saved to `logs/` directory
- Use `Ctrl+C` to exit monitor mode (bots keep running)
