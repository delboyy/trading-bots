import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime

st.set_page_config(
    page_title="Grok Trading Bot Dashboard",
    page_icon="🤖",
    layout="wide"
)

# --- Constants ---
STATUS_FILE = "dashboard/bot_status.json"

# --- Helper Functions ---
def load_status():
    if not os.path.exists(STATUS_FILE):
        return {}
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def format_currency(val):
    return f"${val:,.2f}"

def format_pct(val):
    return f"{val:.2f}%"

# --- Main Dashboard ---
st.title("🤖 Grok Trading Bot Dashboard")

# Auto-refresh
if st.button("🔄 Refresh Now"):
    st.rerun()

# Load Data
data = load_status()

if not data:
    st.warning("No bot data found yet. Start the bots to see status.")
else:
    # --- Aggregate Metrics ---
    total_equity = 0
    total_pnl = 0
    active_bots = 0
    total_positions = 0
    
    bot_rows = []
    
    for bot_id, info in data.items():
        # Check if bot is "active" (updated in last 5 mins)
        last_updated = datetime.fromisoformat(info.get('last_updated', datetime.min.isoformat()))
        is_active = (datetime.now() - last_updated).total_seconds() < 300
        
        if is_active:
            active_bots += 1
            
        equity = info.get('equity', 0)
        total_equity += equity
        
        # Calculate PnL if available, or estimate from equity - start
        # For now, let's assume start was $100,000 (paper) or track it
        start_equity = info.get('start_equity', 100000)
        pnl = equity - start_equity
        total_pnl += pnl
        
        pos = info.get('position', 0)
        if pos != 0:
            total_positions += 1
            
        bot_rows.append({
            "Bot Name": bot_id,
            "Status": "🟢 Active" if is_active else "🔴 Inactive",
            "Equity": equity,
            "PnL ($)": pnl,
            "PnL (%)": (pnl / start_equity) * 100 if start_equity else 0,
            "Position": "LONG" if pos > 0 else "SHORT" if pos < 0 else "FLAT",
            "Entry Price": info.get('entry_price', 0),
            "Last Update": last_updated.strftime("%H:%M:%S"),
            "Error": info.get('error')
        })
        
    # --- Top Metrics Row ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Equity", format_currency(total_equity))
    col2.metric("Total PnL", format_currency(total_pnl), delta=format_currency(total_pnl))
    col3.metric("Active Bots", f"{active_bots}/{len(data)}")
    col4.metric("Open Positions", total_positions)
    
    # --- Detailed Table ---
    st.subheader("Bot Performance")
    
    df = pd.DataFrame(bot_rows)
    
    # Styling
    st.dataframe(
        df.style.format({
            "Equity": "${:,.2f}",
            "PnL ($)": "${:,.2f}",
            "PnL (%)": "{:.2f}%",
            "Entry Price": "${:,.2f}"
        }).applymap(
            lambda x: 'color: green' if x == '🟢 Active' else 'color: red', subset=['Status']
        ).applymap(
            lambda x: 'color: green' if x > 0 else 'color: red' if x < 0 else 'color: gray', subset=['PnL ($)', 'PnL (%)']
        ),
        use_container_width=True,
        height=400
    )

    # --- Errors Tab ---
    st.subheader("⚠️ System Health & Errors")
    error_bots = [b for b in bot_rows if b.get('Error')]
    
    if error_bots:
        st.error(f"Detected {len(error_bots)} bots with errors!")
        for bot in error_bots:
            with st.expander(f"🚨 {bot['Bot Name']} Error", expanded=True):
                st.write(f"**Time:** {bot['Last Update']}")
                st.code(bot['Error'])
    else:
        st.success("✅ All systems operational. No active errors.")
    
    # --- Log Viewer (Optional) ---
    st.subheader("Recent Logs")
    log_file = st.selectbox("Select Log File", os.listdir("logs") if os.path.exists("logs") else [])
    if log_file:
        with open(f"logs/{log_file}", 'r') as f:
            lines = f.readlines()[-50:] # Last 50 lines
            st.code("".join(lines))

    time.sleep(30)
    st.rerun()
