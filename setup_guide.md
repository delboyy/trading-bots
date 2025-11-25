# 🚀 Grok Trading Bot System - VPS Setup Guide

This guide details how to deploy the Grok Trading Bot System to a VPS (Virtual Private Server), configure the environment, and start the live trading bots and monitoring dashboard.

## 📋 Prerequisites

- A VPS running **Ubuntu 20.04 LTS** or newer (recommended).
- **Alpaca Paper Trading Account** (API Key and Secret).
- SSH access to your VPS.

---

## � Fresh Re-Install (Resetting Everything)

If you need to wipe the slate clean and start over (e.g., to pull the latest code updates), follow these steps:

1.  **Navigate to Home Directory**:
    ```bash
    cd ~
    ```

2.  **Remove Existing Directory**:
    ```bash
    rm -rf trading-bots
    ```

3.  **Clone the Repository Again**:
    ```bash
    git clone https://github.com/yourusername/trading-bots.git
    cd trading-bots
    ```

4.  **Run Setup Script**:
    ```bash
    bash setup_vps.sh
    ```

5.  **Activate Environment**:
    ```bash
    source venv/bin/activate
    ```

6.  **Re-Export Keys** (if not in `.bashrc`):
    ```bash
    export APCA_API_KEY_ID='YOUR_KEY'
    export APCA_API_SECRET_KEY='YOUR_SECRET'
    export APCA_API_BASE_URL='https://paper-api.alpaca.markets'
    ```

7.  **Start Bots**:
    ```bash
    python grok/live_bots/run_all_live_bots.py
    ```

---

## �🛠️ Step 1: Initial VPS Setup

1.  **Connect to your VPS** via SSH:
    ```bash
    ssh trader@46.224.77.149
    ```

2.  **Clone the Repository** (or upload your files):
    ```bash
    # Example using git (if you have a repo)
    git clone https://github.com/yourusername/trading-bots.git
    cd trading-bots
    
    # OR upload the 'trading-bots' folder via SFTP/SCP
    ```

3.  **Run the Setup Script**:
    We have prepared a script to automate the installation of Python, pip, and virtual environments.
    ```bash
    bash setup_vps.sh
    ```
    *This script will update the system, install Python 3.9+, create a virtual environment in `venv`, and install all dependencies from `requirements.txt`.*

---

## 🔑 Step 2: Configure Environment Variables

You need to set your Alpaca API credentials.

1.  **Create a `.env` file** (optional but recommended for local dev) OR export variables directly.
    For VPS, it's often easiest to export them in your session or add to `.bashrc`.

    ```bash
export APCA_API_KEY_ID='PKWXWUDCYO6MWM552BTL5RKN2X'
export APCA_API_SECRET_KEY='J6fYWkzcXhAibRg6eapMwjwXH5musxgTP27SeGGqsJ6R'
export APCA_API_BASE_URL='https://paper-api.alpaca.markets'  
    ```

2.  **Verify Connection**:
    Run the check script to ensure everything is working.
    ```bash
    source venv/bin/activate
    python grok/live_bots/check_alpaca_setup.py
    ```
    *Output should say "✅ Connected to Alpaca Account" and "✅ Market Data Access: OK".*

---

## 🖥️ Step 2.5: Using `tmux` for Persistence (CRITICAL)

**IMPORTANT:** If you just run the bots and close your SSH window, **the bots will stop**. To keep them running 24/7, use `tmux`.

1.  **Start a new tmux session**:
    ```bash
    tmux new -s trading
    ```
    *You are now inside a "virtual terminal" that won't close when you disconnect.*

2.  **To Detach (leave bots running)**:
    Press `Ctrl+B`, then release and press `D`.
    *You will return to your main command prompt. The bots keep running in the background.*

3.  **To Re-attach (check on bots)**:
    ```bash
    tmux attach -t trading
    ```

---

## 🤖 Step 3: Start the Trading Bots

We have a master controller script that manages all active bots.

1.  **Activate Virtual Environment** (if not already):
    ```bash
    source venv/bin/activate
    ```

2.  **Run the Master Controller**:
    ```bash
    python grok/live_bots/run_all_live_bots.py
    ```

3.  **Select Option 1** ("Start ALL Bots") to launch all strategies.
    *   The script will spawn independent processes for each bot.
    *   Logs for each bot are written to the `logs/` directory (e.g., `logs/eth_1h_volatility_breakout.log`).

---

## 📊 Step 4: Start the Dashboard

The real-time dashboard allows you to monitor all bots from your browser.

1.  **Run Streamlit**:
    ```bash
    streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
    ```

2.  **Access the Dashboard**:
    Open your web browser and navigate to:
    `http://your_vps_ip:8501`

    *You should see the "Grok Trading Bot Dashboard" with a table showing the status of all active bots.*

---

## 📝 Bot Portfolio Overview

Your system is running **26 Live Bots** covering Crypto, Stocks, Commodities, and Indices:

### 🏆 The Champions (High Return)
- **ETH 1h Volatility Breakout**: 181% Return
- **ETH 1d Volatility Breakout**: 154% Return
- **TSLA 1d Volatility Breakout**: 144% Return
- **NVDA 1d Volatility Breakout**: 143% Return
- **ETH 4h Volatility Breakout**: 148% Return

### 🛡️ The Safe Havens (High Win Rate / Low Drawdown)
- **GLD 4h Mean Reversion**: 100% Win Rate, 4.7% Drawdown
- **SLV 4h Mean Reversion**: 91% Win Rate, 9.3% Drawdown
- **TSLA 4h Fib Local Extrema**: 100% Win Rate (Swing)
- **SPY 1d Volatility Breakout**: 75% Win Rate

### ⚡ The Scalpers (High Frequency)
- **ETH 5m Fib Zigzag**: 91% Win Rate
- **BTC 5m Fib Zigzag**: 85% Win Rate
- **NVDA 5m Squeeze-Pro**: 82% Return
- **BTC 5m Scalp-Z**: 66% Return
- **GOOGL 15m RSI Scalping**: 41% Return
- **TSLA 15m Time Scalping**: 36% Return
- **BTC 15m Squeeze-Pro**: 30% Return
- **NVDA 15m Squeeze-Pro**: 25% Return
- **AMD 5m Volume Breakout**: 13% Return
- **MSFT 5m RSI Scalping**: 4% Return
- **MSFT 5m RSI Winner**: Validated Winner

### 🌍 Diversification
- **BTC 1h/4h**: Crypto Stability
- **NQ 4h**: Futures
- **XLK 1h**: Tech Sector
- **NVDA 1h**: Tech Momentum

---

## ⚠️ Maintenance & Monitoring

-   **Check Logs**: If a bot isn't appearing on the dashboard, check its log file in `logs/`.
-   **Stop Bots**: Use Option 2 in `run_all_live_bots.py` or manually kill the python processes (`pkill -f live_`).
-   **Updates**: If you modify code, restart the affected bots.

**Happy Trading! 🚀**

---

## 🚀 Dashboard Quick Start

To access the real-time dashboard:

1.  **On the VPS**, run the dashboard app:
    ```bash
    streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
    ```
    *Note: You can run this in a separate terminal window, or use `nohup` / `screen` / `tmux` to keep it running in the background.*

2.  **On your Local Machine**, open your browser and go to:
    ```
    http://YOUR_VPS_IP:8501
    ```
    *(Replace `YOUR_VPS_IP` with your VPS's actual IP address)*
