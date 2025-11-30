#!/bin/bash
# Setup script for running long-term and short-term bots in separate tmux sessions
# Each session uses different Alpaca API keys

echo "🚀 Trading Bot Dual-Account Setup"
echo "=================================="
echo ""

# Check if we're already in a tmux session
if [ -n "$TMUX" ]; then
    echo "⚠️  You're already in a tmux session. Please detach first (Ctrl+B, then D)"
    exit 1
fi

# Check for required environment variables
if [ -z "$APCA_LONGTERM_KEY" ] || [ -z "$APCA_LONGTERM_SECRET" ]; then
    echo "❌ Long-term Alpaca credentials not set!"
    echo "Please set:"
    echo "  export APCA_LONGTERM_KEY='your_longterm_api_key'"
    echo "  export APCA_LONGTERM_SECRET='your_longterm_secret_key'"
    exit 1
fi

if [ -z "$APCA_SHORTTERM_KEY" ] || [ -z "$APCA_SHORTTERM_SECRET" ]; then
    echo "❌ Short-term Alpaca credentials not set!"
    echo "Please set:"
    echo "  export APCA_SHORTTERM_KEY='your_shortterm_api_key'"
    echo "  export APCA_SHORTTERM_SECRET='your_shortterm_secret_key'"
    exit 1
fi

echo "✅ Credentials found for both accounts"
echo ""

# Kill existing sessions if they exist
tmux kill-session -t longterm 2>/dev/null
tmux kill-session -t shortterm 2>/dev/null
tmux kill-session -t dashboard_lt 2>/dev/null
tmux kill-session -t dashboard_st 2>/dev/null

echo "📊 Creating Long-Term Bots Session..."
# Create long-term bots session
tmux new-session -d -s longterm -n "LT-Bots"
tmux send-keys -t longterm "cd $(pwd)" C-m
tmux send-keys -t longterm "export APCA_API_KEY_ID='$APCA_LONGTERM_KEY'" C-m
tmux send-keys -t longterm "export APCA_API_SECRET_KEY='$APCA_LONGTERM_SECRET'" C-m
tmux send-keys -t longterm "export APCA_API_BASE_URL='https://paper-api.alpaca.markets'" C-m
tmux send-keys -t longterm "echo '🔵 LONG-TERM BOTS (1h+ timeframes)'" C-m
tmux send-keys -t longterm "echo '15 bots ready to start'" C-m
tmux send-keys -t longterm "python grok/live_bots/run_longterm_bots.py" C-m

echo "📈 Creating Short-Term Bots Session..."
# Create short-term bots session
tmux new-session -d -s shortterm -n "ST-Bots"
tmux send-keys -t shortterm "cd $(pwd)" C-m
tmux send-keys -t shortterm "export APCA_API_KEY_ID='$APCA_SHORTTERM_KEY'" C-m
tmux send-keys -t shortterm "export APCA_API_SECRET_KEY='$APCA_SHORTTERM_SECRET'" C-m
tmux send-keys -t shortterm "export APCA_API_BASE_URL='https://paper-api.alpaca.markets'" C-m
tmux send-keys -t shortterm "echo '🟢 SHORT-TERM BOTS (<1h timeframes)'" C-m
tmux send-keys -t shortterm "echo '15 bots ready to start'" C-m
tmux send-keys -t shortterm "python grok/live_bots/run_shortterm_bots.py" C-m

echo "📊 Creating Long-Term Dashboard..."
# Create long-term dashboard session
tmux new-session -d -s dashboard_lt -n "LT-Dashboard"
tmux send-keys -t dashboard_lt "cd $(pwd)" C-m
tmux send-keys -t dashboard_lt "export APCA_API_KEY_ID='$APCA_LONGTERM_KEY'" C-m
tmux send-keys -t dashboard_lt "export APCA_API_SECRET_KEY='$APCA_LONGTERM_SECRET'" C-m
tmux send-keys -t dashboard_lt "sleep 5" C-m  # Wait for bots to start
tmux send-keys -t dashboard_lt "streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0" C-m

echo "📈 Creating Short-Term Dashboard..."
# Create short-term dashboard session
tmux new-session -d -s dashboard_st -n "ST-Dashboard"
tmux send-keys -t dashboard_st "cd $(pwd)" C-m
tmux send-keys -t dashboard_st "export APCA_API_KEY_ID='$APCA_SHORTTERM_KEY'" C-m
tmux send-keys -t dashboard_st "export APCA_API_SECRET_KEY='$APCA_SHORTTERM_SECRET'" C-m
tmux send-keys -t dashboard_st "sleep 5" C-m  # Wait for bots to start
tmux send-keys -t dashboard_st "streamlit run dashboard/app.py --server.port 8502 --server.address 0.0.0.0" C-m

echo ""
echo "✅ All sessions created!"
echo ""
echo "📋 Session Overview:"
echo "  🔵 longterm      - Long-term bots (1h+ timeframes)"
echo "  🟢 shortterm     - Short-term bots (<1h timeframes)"
echo "  📊 dashboard_lt  - Long-term dashboard (port 8501)"
echo "  📈 dashboard_st  - Short-term dashboard (port 8502)"
echo ""
echo "🔗 Access Dashboards:"
echo "  Long-term:  http://localhost:8501"
echo "  Short-term: http://localhost:8502"
echo ""
echo "📱 Attach to Sessions:"
echo "  tmux attach -t longterm"
echo "  tmux attach -t shortterm"
echo "  tmux attach -t dashboard_lt"
echo "  tmux attach -t dashboard_st"
echo ""
echo "⌨️  Detach from session: Ctrl+B, then D"
echo "🛑 Stop all: ./stop_all_sessions.sh"
echo ""
echo "Waiting 10 seconds for everything to initialize..."
sleep 10

echo ""
echo "✅ Setup complete! Check dashboards in your browser."
