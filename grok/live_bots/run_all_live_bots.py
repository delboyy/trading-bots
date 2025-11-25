#!/usr/bin/env python3
"""
MASTER SCRIPT: Run Multiple Live Trading Bots in Parallel
Controls and monitors all 10 live trading bots for the top strategies
"""

import os
import sys
import time
import subprocess
import signal
import logging
from typing import List, Dict, Any
from pathlib import Path

# Create logs directory BEFORE setting up logging
os.makedirs('logs', exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/master_bot_controller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MASTER_BOT_CONTROLLER')


class LiveBotController:
    """Controls multiple live trading bots running in parallel"""

    def __init__(self):
        self.bot_processes: Dict[str, subprocess.Popen] = {}

        # Get the directory where this script is located
        self.bot_dir = Path(__file__).resolve().parent

        self.bot_scripts = {
            'eth_1h': 'live_eth_1h_volatility_breakout.py',
            'slv_4h': 'live_slv_4h_mean_reversion.py',
            'gld_4h': 'live_gld_4h_mean_reversion.py',
            'nvda_1h': 'live_nvda_1h_volatility_breakout.py',
            'eth_4h': 'live_eth_4h_volatility_breakout.py',
            'tsla_4h': 'live_tsla_4h_volatility_breakout.py',
            'nq_4h': 'live_nq_4h_volatility_breakout.py',
            'btc_1h': 'live_btc_1h_volatility_breakout.py',
            'meta_1h': 'live_meta_1h_volatility_breakout.py',
            'xlk_1h': 'live_xlk_1h_volatility_breakout.py',
            'eth_5m': 'live_eth_5m_fib_zigzag.py',
            'btc_5m': 'live_btc_5m_fib_zigzag.py',
            'tsla_4h_le': 'live_tsla_4h_fib_local_extrema.py',
            'eth_1d': 'live_eth_1d_volatility_breakout.py',
            'tsla_1d': 'live_tsla_1d_volatility_breakout.py',
            'nvda_1d': 'live_nvda_1d_volatility_breakout.py',
            'spy_1d': 'live_spy_1d_volatility_breakout.py',
            'nvda_5m_squeeze': 'live_nvda_5m_squeeze_pro.py',
            'btc_15m_squeeze': 'live_btc_15m_squeeze_pro.py',
            'btc_5m_scalp_z': 'live_btc_5m_scalp_z.py',
            'nvda_15m_squeeze': 'live_nvda_15m_squeeze_pro.py',
            'amd_5m_vol': 'live_amd_5m_volume_breakout.py',
            'googl_15m_rsi': 'live_googl_15m_rsi_scalping.py',
            'msft_5m_rsi': 'live_msft_5m_rsi_scalping.py',
            'msft_5m_winner': 'live_msft_5m_rsi_winner.py',
            'tsla_15m_time': 'live_tsla_15m_time_based_scalping.py'
        }

        self.bot_info = {
            'eth_1h': {'name': 'ETH 1h Volatility Breakout', 'description': 'Champion strategy - 181% returns'},
            'slv_4h': {'name': 'SLV 4h Mean Reversion', 'description': 'Perfect balance - 70% returns, 9% DD'},
            'gld_4h': {'name': 'GLD 4h Mean Reversion', 'description': 'Ultra-safe - 39% returns, 100% win rate'},
            'nvda_1h': {'name': 'NVDA 1h Volatility Breakout', 'description': 'Tech leader - 109% returns'},
            'eth_4h': {'name': 'ETH 4h Volatility Breakout', 'description': 'Conservative ETH - 148% returns'},
            'tsla_4h': {'name': 'TSLA 4h Volatility Breakout', 'description': 'Stock champion - 59% returns'},
            'nq_4h': {'name': 'NQ 4h Volatility Breakout', 'description': 'Futures winner - 33% returns'},
            'btc_1h': {'name': 'BTC 1h Volatility Breakout', 'description': 'Crypto steady - 45% returns'},
            'meta_1h': {'name': 'META 1h Volatility Breakout', 'description': 'Social media - 29% returns'},
            'xlk_1h': {'name': 'XLK 1h Volatility Breakout', 'description': 'Tech sector - 24% returns'},
            'eth_5m': {'name': 'ETH 5m Fib Zigzag', 'description': 'Scalper - 91% Win Rate'},
            'btc_5m': {'name': 'BTC 5m Fib Zigzag', 'description': 'Scalper - 85% Win Rate'},
            'tsla_4h_le': {'name': 'TSLA 4h Fib Local Extrema', 'description': 'Swing - 100% Win Rate'},
            'eth_1d': {'name': 'ETH 1d Volatility Breakout', 'description': 'Daily Swing - 154% Return'},
            'tsla_1d': {'name': 'TSLA 1d Volatility Breakout', 'description': 'Daily Swing - 144% Return'},
            'nvda_1d': {'name': 'NVDA 1d Volatility Breakout', 'description': 'Daily Swing - 143% Return'},
            'spy_1d': {'name': 'SPY 1d Volatility Breakout', 'description': 'Daily Swing - 75% Win Rate'},
            'nvda_5m_squeeze': {'name': 'NVDA 5m Squeeze-Pro', 'description': 'Scalper - 82% Return, 7.9% DD'},
            'btc_15m_squeeze': {'name': 'BTC 15m Squeeze-Pro', 'description': 'Scalper - 30% Return, 8% DD'},
            'btc_5m_scalp_z': {'name': 'BTC 5m Scalp-Z', 'description': 'Scalper - 66% Return, 13.5% DD'},
            'nvda_15m_squeeze': {'name': 'NVDA 15m Squeeze-Pro', 'description': 'Scalper - 25% Return, 3.8% DD'},
            'amd_5m_vol': {'name': 'AMD 5m Volume Breakout', 'description': 'Scalper - 13.75% Return, 66.7% Win Rate'},
            'googl_15m_rsi': {'name': 'GOOGL 15m RSI Scalping', 'description': 'Scalper - 41.3% Return, 54% Win Rate'},
            'msft_5m_rsi': {'name': 'MSFT 5m RSI Scalping', 'description': 'Scalper - 4% Return, 53.7% Win Rate'},
            'msft_5m_winner': {'name': 'MSFT 5m RSI Winner', 'description': 'Scalper - Validated Winner Strategy'},
            'tsla_15m_time': {'name': 'TSLA 15m Time Scalping', 'description': 'Scalper - 36% Return, 64% Win Rate'}
        }

    def check_environment(self) -> bool:
        """Check if environment is properly configured"""
        required_vars = ['APCA_API_KEY_ID', 'APCA_API_SECRET_KEY']
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            logger.info("Please set your Alpaca API credentials:")
            logger.info("export APCA_API_KEY_ID='your_key_here'")
            logger.info("export APCA_API_SECRET_KEY='your_secret_here'")
            logger.info("export APCA_API_BASE_URL='https://paper-api.alpaca.markets'  # For paper trading")
            return False

        logger.info("Environment variables configured ✓")
        return True

    def start_bot(self, bot_key: str) -> bool:
        """Start a specific bot"""
        if bot_key not in self.bot_scripts:
            logger.error(f"Unknown bot: {bot_key}")
            return False

        if bot_key in self.bot_processes:
            logger.warning(f"Bot {bot_key} is already running")
            return False

        script_path = self.bot_dir / self.bot_scripts[bot_key]
        if not script_path.exists():
            logger.error(f"Script not found: {script_path}")
            return False

        try:
            # Create bot-specific log file for errors
            bot_log_file = f"logs/{bot_key}_error.log"
            
            # Start the bot process with error logging
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd(),
                text=True,
                bufsize=1
            )

            self.bot_processes[bot_key] = process
            logger.info(f"Started bot: {self.bot_info[bot_key]['name']}")
            
            # Start a thread to capture and log stderr
            def log_stderr():
                try:
                    with open(bot_log_file, 'a') as f:
                        for line in process.stderr:
                            error_msg = line.strip()
                            if error_msg:
                                logger.error(f"Bot {bot_key} ERROR: {error_msg}")
                                f.write(f"{error_msg}\n")
                                f.flush()
                except Exception as e:
                    logger.error(f"Error logging stderr for {bot_key}: {e}")
            
            import threading
            stderr_thread = threading.Thread(target=log_stderr, daemon=True)
            stderr_thread.start()
            
            return True

        except Exception as e:
            logger.error(f"Failed to start bot {bot_key}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def stop_bot(self, bot_key: str) -> bool:
        """Stop a specific bot"""
        if bot_key not in self.bot_processes:
            logger.warning(f"Bot {bot_key} is not running")
            return False

        try:
            process = self.bot_processes[bot_key]
            process.terminate()

            # Wait for process to terminate
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            del self.bot_processes[bot_key]
            logger.info(f"Stopped bot: {self.bot_info[bot_key]['name']}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop bot {bot_key}: {e}")
            return False

    def start_all_bots(self) -> int:
        """Start all bots"""
        started_count = 0
        for bot_key in self.bot_scripts.keys():
            if self.start_bot(bot_key):
                started_count += 1
                time.sleep(2)  # Small delay between starting bots

        logger.info(f"Started {started_count}/{len(self.bot_scripts)} bots")
        return started_count

    def stop_all_bots(self) -> int:
        """Stop all bots"""
        stopped_count = 0
        for bot_key in list(self.bot_processes.keys()):
            if self.stop_bot(bot_key):
                stopped_count += 1

        logger.info(f"Stopped {stopped_count} bots")
        return stopped_count

    def get_status(self) -> Dict[str, Any]:
        """Get status of all bots"""
        status = {}
        for bot_key, info in self.bot_info.items():
            is_running = bot_key in self.bot_processes
            if is_running:
                process = self.bot_processes[bot_key]
                is_alive = process.poll() is None
                status[bot_key] = {
                    'name': info['name'],
                    'description': info['description'],
                    'running': is_alive,
                    'pid': process.pid if is_alive else None
                }
            else:
                status[bot_key] = {
                    'name': info['name'],
                    'description': info['description'],
                    'running': False,
                    'pid': None
                }

        return status

    def monitor_bots(self):
        """Monitor bot status continuously"""
        logger.info("Starting bot monitoring...")

        while True:
            try:
                status = self.get_status()
                running_count = sum(1 for s in status.values() if s['running'])

                logger.info(f"Bot Status: {running_count}/{len(status)} running")

                # Check for crashed bots and restart them
                for bot_key, bot_status in status.items():
                    if not bot_status['running'] and bot_key in self.bot_processes:
                        logger.warning(f"Bot {bot_key} has stopped, attempting restart...")
                        del self.bot_processes[bot_key]
                        self.start_bot(bot_key)

                time.sleep(60)  # Check every minute

            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring: {e}")
                time.sleep(30)

    def show_menu(self):
        """Show interactive menu"""
        while True:
            print("\n" + "="*80)
            print("🎯 LIVE TRADING BOT CONTROLLER")
            print("="*80)
            print("Available bots:")
            for key, info in self.bot_info.items():
                status = "🟢 RUNNING" if key in self.bot_processes and self.bot_processes[key].poll() is None else "🔴 STOPPED"
                print(f"  {key}: {info['name']} - {status}")

            print("\nCommands:")
            print("  start <bot_key>    - Start specific bot")
            print("  stop <bot_key>     - Stop specific bot")
            print("  start_all          - Start all bots")
            print("  stop_all           - Stop all bots")
            print("  status             - Show detailed status")
            print("  monitor            - Start monitoring mode")
            print("  exit               - Exit controller")

            try:
                command = input("\nEnter command: ").strip().lower()

                if command == 'exit':
                    break
                elif command == 'start_all':
                    self.start_all_bots()
                elif command == 'stop_all':
                    self.stop_all_bots()
                elif command == 'status':
                    status = self.get_status()
                    print("\nDetailed Status:")
                    for key, info in status.items():
                        print(f"  {key}: {info['name']} - {'RUNNING' if info['running'] else 'STOPPED'}")
                elif command == 'monitor':
                    print("Entering monitoring mode... (Ctrl+C to exit)")
                    self.monitor_bots()
                elif command.startswith('start '):
                    bot_key = command.split()[1]
                    if bot_key in self.bot_scripts:
                        self.start_bot(bot_key)
                    else:
                        print(f"Unknown bot: {bot_key}")
                elif command.startswith('stop '):
                    bot_key = command.split()[1]
                    if bot_key in self.bot_scripts:
                        self.stop_bot(bot_key)
                    else:
                        print(f"Unknown bot: {bot_key}")
                else:
                    print("Unknown command")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

    def cleanup(self):
        """Cleanup: stop all bots"""
        logger.info("Cleaning up: stopping all bots...")
        self.stop_all_bots()


def print_setup_instructions():
    """Print setup instructions"""
    print("""
🚀 LIVE TRADING BOT SETUP INSTRUCTIONS
========================================

1. ENVIRONMENT SETUP:
   export APCA_API_KEY_ID='your_alpaca_key'
   export APCA_API_SECRET_KEY='your_alpaca_secret'
   export APCA_API_BASE_URL='https://paper-api.alpaca.markets'

2. INSTALL DEPENDENCIES:
   pip install alpaca-trade-api pandas numpy schedule

3. START INDIVIDUAL BOTS:
   python live_eth_1h_volatility_breakout.py &
   python live_slv_4h_mean_reversion.py &
   # ... etc for each bot

4. OR USE MASTER CONTROLLER:
   python run_all_live_bots.py

5. MONITOR LOGS:
   tail -f logs/*.log

⚠️  IMPORTANT NOTES:
- These are PAPER TRADING bots - no real money at risk
- Each bot runs independently and can be started/stopped separately
- Monitor logs regularly for errors
- Stop losses are implemented but monitor positions
- Crypto markets are 24/7, stocks are 9:30-16:00 ET

🎯 BOT PORTFOLIO ALLOCATION SUGGESTIONS:
- ETH 1h VB: 25% (high growth potential)
- SLV 4h MR: 20% (low risk, high win rate)
- GLD 4h MR: 15% (ultra-safe)
- NVDA 1h VB: 10% (tech growth)
- Others: 5% each (diversification)
""")


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == '--setup':
        print_setup_instructions()
        return

    controller = LiveBotController()

    if not controller.check_environment():
        print("❌ Environment not configured. Run with --setup for instructions.")
        sys.exit(1)

    try:
        controller.show_menu()
    except KeyboardInterrupt:
        pass
    finally:
        controller.cleanup()


if __name__ == "__main__":
    main()
