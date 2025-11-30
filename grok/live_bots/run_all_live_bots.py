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

        # All bots - 6 VALIDATED WINNERS ONLY
        self.bot_scripts = {
            # Long-term bots (>=1h timeframe)
            'eth_1h': 'long_term/live_eth_1h_volatility_breakout_claude.py',
            'eth_4h': 'long_term/live_eth_4h_volatility_breakout_claude.py',
            'nvda_1h': 'long_term/live_nvda_1h_volatility_breakout_claude.py',
            # Scalping bots (<1h timeframe)
            'btc_combo_15m': 'scalping/live_btc_combo_claude.py',
            'btc_combo_1d': 'scalping/live_btc_combo_momentum_claude.py',
            'tsla_15m': 'scalping/live_tsla_15m_time_based_scalping.py',
            # New bots
            'gld_candlestick': 'scalping/live_gld_5m_candlestick_scalping.py',
            'gld_fibonacci': 'scalping/live_gld_5m_fibonacci_momentum.py',
            'googl_rsi': 'scalping/live_googl_15m_rsi_scalping.py',
        }

        self.bot_info = {
            # Long-term bots (>=1h)
            'eth_1h': {
                'name': 'ETH 1h Volatility (Claude)', 
                'description': '🏆 TOP: 0.248%/day, 142% annual, 2yr validated'
            },
            'eth_4h': {
                'name': 'ETH 4h Volatility (Claude)', 
                'description': '🥇 EXCELLENT: 0.203%/day, 107% annual, 2yr validated'
            },
            'nvda_1h': {
                'name': 'NVDA 1h Volatility (Claude)', 
                'description': '✅ SOLID: 0.149%/day, 72% annual, 2yr validated'
            },
            # Scalping bots (<1h)
            'btc_combo_15m': {
                'name': 'BTC Combo 15m (Claude)', 
                'description': '🏆 TOP: 0.247%/day, 141% annual, 60d validated'
            },
            'btc_combo_1d': {
                'name': 'BTC Combo Momentum 1d (Claude)', 
                'description': '✅ KEEPER: 0.161%/day, 48% annual, 2yr validated'
            },
            'tsla_15m': {
                'name': 'TSLA 15m Time-Based', 
                'description': '✅ SOLID: 0.160%/day, 79% annual, 2yr validated'
            }
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
            # CRITICAL: start_new_session=True prevents Ctrl+C from killing bots
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd(),
                text=True,
                bufsize=1,
                start_new_session=True  # Isolate from parent's signal group
            )

            self.bot_processes[bot_key] = process
            logger.info(f"Started bot: {self.bot_info[bot_key]['name']}")
            
            # Start a thread to capture and log stderr
            def log_stderr(filter_level=None):
                try:
                    with open(bot_log_file, 'a') as f:
                        for line in process.stderr:
                            error_msg = line.strip()
                            if error_msg:
                                # Determine log level
                                is_error = 'ERROR' in error_msg or 'CRITICAL' in error_msg or 'WARNING' in error_msg
                                is_trade = any(keyword in error_msg for keyword in ['order', 'Order', 'position', 'Position', 'trade', 'Trade', 'buy', 'sell', 'Buy', 'Sell'])
                                is_info = 'INFO' in error_msg
                                
                                # Apply filter if specified
                                should_log = True
                                if filter_level == 'errors' and not is_error:
                                    should_log = False
                                elif filter_level == 'trades' and not is_trade:
                                    should_log = False
                                elif filter_level == 'info' and not (is_info and not is_error):
                                    should_log = False
                                
                                # Only log to console if monitoring is active
                                if should_log and getattr(self, 'monitoring_active', False):
                                    logger.error(f"Bot {bot_key} ERROR: {error_msg}")
                                
                                # Always write to file
                                f.write(f"{error_msg}\n")
                                f.flush()
                except Exception as e:
                    logger.error(f"Error logging stderr for {bot_key}: {e}")
            
            import threading
            # Get filter level from instance variable if set
            filter_level = getattr(self, 'log_filter', None)
            stderr_thread = threading.Thread(target=lambda: log_stderr(filter_level), daemon=True)
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
        
        # Clean up dead processes first
        dead_bots = []
        for bot_key, process in list(self.bot_processes.items()):
            if process.poll() is not None:  # Process has terminated
                dead_bots.append(bot_key)
        
        # Remove dead processes from tracking
        for bot_key in dead_bots:
            del self.bot_processes[bot_key]
        
        # Build status for all bots
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
        print("\n" + "="*80)
        print("📊 MONITORING MODE ACTIVE")
        print("="*80)
        print("Press Ctrl+C to exit monitoring (bots will keep running)")
        print("="*80 + "\n")
        
        logger.info("Starting bot monitoring...")
        self.monitoring_active = True  # Enable console logging
        
        try:
            while True:
                try:
                    status = self.get_status()
                    running_count = sum(1 for s in status.values() if s['running'])

                    logger.info(f"Bot Status: {running_count}/{len(status)} running")

                    # Auto-restart stopped bots
                    for bot_key, bot_status in status.items():
                        if not bot_status['running'] and bot_key in self.bot_scripts:
                            logger.warning(f"Bot {bot_key} has stopped, attempting restart...")
                            self.start_bot(bot_key)

                    time.sleep(60)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Monitor error: {e}")
                    time.sleep(60)
        finally:
            self.monitoring_active = False  # Disable console logging when exiting monitor
            print("\n" + "="*80)
            print("✅ Exited monitoring mode - All bots still running in background")
            print("="*80 + "\n")

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
            print("  monitor            - Monitor all logs (verbose)")
            print("  monitor_errors     - Monitor ERRORS only")
            print("  monitor_trades     - Monitor TRADES only")
            print("  monitor_info       - Monitor INFO logs only")
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
                    print("Entering monitoring mode (ALL LOGS)... (Ctrl+C to exit)")
                    self.log_filter = None
                    self.monitor_bots()
                elif command == 'monitor_errors':
                    print("Entering ERROR monitoring mode... (Ctrl+C to exit)")
                    self.log_filter = 'errors'
                    self.monitor_bots()
                elif command == 'monitor_trades':
                    print("Entering TRADE monitoring mode... (Ctrl+C to exit)")
                    self.log_filter = 'trades'
                    self.monitor_bots()
                elif command == 'monitor_info':
                    print("Entering INFO monitoring mode... (Ctrl+C to exit)")
                    self.log_filter = 'info'
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
