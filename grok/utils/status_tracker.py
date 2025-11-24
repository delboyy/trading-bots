import json
import os
import time
import fcntl
from datetime import datetime
from typing import Dict, Any

class StatusTracker:
    """
    Tracks the status of multiple bots in a shared JSON file.
    Uses file locking to ensure safe concurrent access.
    """
    def __init__(self, status_file: str = "dashboard/bot_status.json"):
        self.status_file = status_file
        self.ensure_file_exists()

    def ensure_file_exists(self):
        """Create the status file if it doesn't exist"""
        os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
        if not os.path.exists(self.status_file):
            with open(self.status_file, 'w') as f:
                json.dump({}, f)

    def update_status(self, bot_id: str, status_data: Dict[str, Any]):
        """
        Update the status for a specific bot.
        
        Args:
            bot_id: Unique identifier for the bot (e.g., 'eth_1h')
            status_data: Dictionary containing status info (equity, position, etc.)
        """
        # Add timestamp
        status_data['last_updated'] = datetime.now().isoformat()
        
        # Retry mechanism for file locking
        max_retries = 5
        for i in range(max_retries):
            try:
                with open(self.status_file, 'r+') as f:
                    # Acquire exclusive lock
                    fcntl.flock(f, fcntl.LOCK_EX)
                    
                    try:
                        # Read current data
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = {}
                            
                        # Update bot data
                        data[bot_id] = status_data
                        
                        # Write back
                        f.seek(0)
                        json.dump(data, f, indent=4)
                        f.truncate()
                        
                    finally:
                        # Release lock
                        fcntl.flock(f, fcntl.LOCK_UN)
                break
            except IOError:
                time.sleep(0.1)
