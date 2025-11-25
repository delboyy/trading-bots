#!/usr/bin/env python3
"""
Add stop logging to all remaining live bots
"""

import os
import re
from pathlib import Path

def add_signal_handling_to_bot(bot_file):
    """Add signal handling and stop logging to a bot file"""

    with open(bot_file, 'r') as f:
        content = f.read()

    # Check if signal import is already there
    if 'import signal' not in content:
        # Add signal import after other imports
        import_pattern = r'(import schedule\n)'
        signal_import = 'import signal\n'
        content = re.sub(import_pattern, r'\1' + signal_import, content, count=1)

    # Check if signal handling code is already there
    if 'stop_flag = False' not in content:
        # Add signal handling code after logs directory creation
        logs_pattern = r'(# Create logs directory\nos\.makedirs\(.logs.\, exist_ok=True\)\n\n)'
        signal_code = '''# Global stop flag
stop_flag = False

def signal_handler(signum, frame):
    """Handle stop signals gracefully"""
    global stop_flag
    stop_flag = True
    logger.info(f"Received signal {signum}, stopping bot gracefully...")
    # Give a moment for cleanup
    time.sleep(2)
    logger.info("Bot stopped successfully")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill command

'''
        content = re.sub(logs_pattern, r'\1' + signal_code, content, count=1)

    # Update run_live method if it doesn't have stop flag checking
    if 'while not stop_flag:' not in content:
        # Find the run_live method and update it
        run_live_pattern = r'(    def run_live\(self\):\n        logger\.info\("Starting [^"]+ Bot\.\.\."\)\n        schedule\.every\([^)]+\)\.do\(self\.run_strategy\)\n        while True:\n            try:\n                schedule\.run_pending\(\)\n                time\.sleep\(\d+\)\n            except Exception as e:\n                logger\.error\(f"Loop error: \{e\}"\)\n                time\.sleep\(\d+\)\n)'
        replacement = r'    def run_live(self):
        global stop_flag
        logger.info("Starting \\1 Bot...")
        schedule.every(1).minutes.do(self.run_strategy)

        try:
            while not stop_flag:
                try:
                    schedule.run_pending()
                    time.sleep(10)
                except Exception as e:
                    logger.error(f"Loop error: {e}")
                    time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"Bot crashed with error: {e}")
        finally:
            logger.info("Bot shutdown complete - cleaning up...")
            # Add any cleanup logic here if needed
            logger.info("\\1 Bot stopped")'

        # This regex is complex, let me use a simpler approach
        if 'while True:' in content and 'while not stop_flag:' not in content:
            content = content.replace(
                '        while True:\n            try:\n                schedule.run_pending()\n                time.sleep(10)\n            except Exception as e:\n                logger.error(f"Loop error: {e}")\n                time.sleep(60)',
                '        try:\n            while not stop_flag:\n                try:\n                    schedule.run_pending()\n                    time.sleep(10)\n                except Exception as e:\n                    logger.error(f"Loop error: {e}")\n                    time.sleep(60)\n        except KeyboardInterrupt:\n            logger.info("Bot stopped by user (Ctrl+C)")\n        except Exception as e:\n            logger.error(f"Bot crashed with error: {e}")\n        finally:\n            logger.info("Bot shutdown complete - cleaning up...")\n            # Add any cleanup logic here if needed\n            logger.info("Bot stopped")'
            )

    # Write back the modified content
    with open(bot_file, 'w') as f:
        f.write(content)

    print(f"✅ Updated {bot_file}")

def main():
    """Update all live bots with stop logging"""
    grok_dir = Path('grok/live_bots')

    # Skip these files
    skip_files = {'check_alpaca_setup.py', 'run_all_live_bots.py'}

    updated_count = 0
    for bot_file in grok_dir.glob('live_*.py'):
        if bot_file.name not in skip_files:
            print(f"Processing {bot_file.name}...")
            add_signal_handling_to_bot(bot_file)
            updated_count += 1

    print(f"\n🎯 Updated {updated_count} live bot files with stop logging")

if __name__ == "__main__":
    main()
