#!/bin/bash
# Stop all trading bot sessions

echo "🛑 Stopping all trading bot sessions..."

tmux kill-session -t longterm 2>/dev/null && echo "✅ Stopped long-term bots"
tmux kill-session -t shortterm 2>/dev/null && echo "✅ Stopped short-term bots"
tmux kill-session -t dashboard_lt 2>/dev/null && echo "✅ Stopped long-term dashboard"
tmux kill-session -t dashboard_st 2>/dev/null && echo "✅ Stopped short-term dashboard"

echo ""
echo "✅ All sessions stopped"
