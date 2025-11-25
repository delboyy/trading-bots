#!/bin/bash

echo "🚀 Setting up Trading Bot VPS Environment..."

# 1. Update System
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Python 3 and pip
sudo apt-get install -y python3 python3-pip python3-venv

# 3. Create Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 4. Install Dependencies
pip install -r requirements.txt

# 5. Create Logs Directory
mkdir -p logs

# 6. Cleanup Unnecessary Files (Save Space)
echo "🧹 Cleaning up backtesting and data files..."
rm -rf backtesting
rm -rf data
rm -rf tests
rm -rf .git  # Optional: Remove git history to save space if not developing on VPS

echo "✅ Setup Complete!"
echo "To activate environment: source venv/bin/activate"
echo "To run bots: python grok/live_bots/run_all_live_bots.py"
