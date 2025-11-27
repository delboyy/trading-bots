# Trading Bot System Documentation

Complete documentation for the automated trading bot system.

## 📚 Quick Start Guides

### Essential Setup
- **[Setup Guide](setup_guide.md)** - Initial VPS and system setup
- **[Dual Account Setup](DUAL_ACCOUNT_SETUP.md)** - Run long-term and short-term bots separately
- **[Quick Reference](QUICK_REFERENCE.md)** - Command cheat sheet

### Bot Management
- **[Adding New Bots](adding_new_bots.md)** - Step-by-step guide to add new trading bots
- **[Crypto Order Management](crypto_order_management.md)** - How crypto bots handle stop loss and take profit

### API Reference
- **[Alpaca Symbols Guide](alpaca_symbols_guide.md)** - Supported symbols and formats
- **[ALPACA_SYMBOLS.md](ALPACA_SYMBOLS.md)** - Complete symbol reference

---

## 🎯 By Use Case

### I want to...

**Set up the system for the first time**
→ Start with [Setup Guide](setup_guide.md)

**Run long-term and short-term bots separately**
→ Follow [Dual Account Setup](DUAL_ACCOUNT_SETUP.md)

**Add a new trading bot**
→ Use [Adding New Bots](adding_new_bots.md)

**Understand how crypto orders work**
→ Read [Crypto Order Management](crypto_order_management.md)

**Find supported trading symbols**
→ Check [Alpaca Symbols Guide](alpaca_symbols_guide.md)

**Quick command reference**
→ See [Quick Reference](QUICK_REFERENCE.md)

---

## 📖 Document Descriptions

### Setup Guide
Complete VPS setup, environment configuration, and initial deployment instructions.

**Topics:**
- VPS setup and SSH configuration
- Python environment setup
- Alpaca API credentials
- Running bots and dashboard
- Troubleshooting

### Dual Account Setup
Advanced configuration for running two separate groups of bots with different Alpaca accounts.

**Topics:**
- Account separation strategy
- Tmux session management
- Long-term vs short-term bots
- Separate dashboards
- Environment variable configuration

### Adding New Bots
Comprehensive guide for integrating new trading strategies into the system.

**Topics:**
- Bot file structure
- Required imports and setup
- Dashboard integration
- StatusTracker usage
- Common pitfalls
- Testing checklist

### Crypto Order Management
Technical documentation on how crypto bots handle orders (since Alpaca doesn't support bracket orders for crypto).

**Topics:**
- Why separate orders are needed
- Order placement workflow
- Automatic cleanup logic
- Edge cases and handling
- Advantages over manual monitoring

### Alpaca Symbols Guide
Reference for supported trading symbols and correct format for each asset type.

**Topics:**
- Stock symbols
- Crypto symbols
- ETF symbols
- Futures symbols
- Symbol format requirements

### Quick Reference
One-page cheat sheet for common commands and operations.

**Topics:**
- Tmux commands
- Bot controller commands
- Dashboard access
- Troubleshooting quick fixes

---

## 🔧 System Architecture

```
trading-bots/
├── grok/live_bots/          # Bot controllers and individual bots
│   ├── run_all_live_bots.py      # All 30 bots
│   ├── run_longterm_bots.py      # 15 long-term bots
│   ├── run_shortterm_bots.py     # 15 short-term bots
│   └── live_*.py                 # Individual bot files
├── dashboard/               # Streamlit dashboard
│   └── app.py
├── grok/utils/             # Shared utilities
│   └── status_tracker.py        # Bot status management
├── logs/                   # Bot logs
├── docs/                   # Documentation (you are here)
└── *.sh                    # Setup and control scripts
```

---

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd trading-bots
./setup_vps.sh

# 2. Configure API keys
export APCA_API_KEY_ID="your_key"
export APCA_API_SECRET_KEY="your_secret"

# 3. Start bots
python grok/live_bots/run_all_live_bots.py

# 4. Start dashboard
streamlit run dashboard/app.py --server.port 8501
```

For dual-account setup:
```bash
./start_dual_account_system.sh
```

---

## 📞 Support

For issues or questions:
1. Check the relevant documentation above
2. Review logs in `logs/` directory
3. Check bot status in dashboard
4. Review error messages in bot controller

---

**Last Updated:** 2025-11-27  
**System Version:** 2.0 (Dual-Account)
