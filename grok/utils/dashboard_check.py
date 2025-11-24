import sys
import os
import time
import json
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from grok.utils.status_tracker import StatusTracker

def test_dashboard_integration():
    print("Testing Dashboard Integration...")
    
    # Initialize Tracker
    tracker = StatusTracker()
    bot_id = "test_bot_1"
    
    # Simulate Bot Update
    status_data = {
        'equity': 105000.0,
        'cash': 50000.0,
        'position': 1.5,
        'entry_price': 2000.0,
        'unrealized_pl': 500.0
    }
    
    print(f"Updating status for {bot_id}...")
    tracker.update_status(bot_id, status_data)
    
    # Check if file exists
    # The StatusTracker uses relative path 'dashboard/bot_status.json' from CWD
    # So we need to ensure we run this from project root
    status_file = 'dashboard/bot_status.json'
    if os.path.exists(status_file):
        print(f"Success: {status_file} created.")
        
        # Read file content
        with open(status_file, 'r') as f:
            data = json.load(f)
            
        if bot_id in data and data[bot_id]['equity'] == 105000.0:
            print("Success: Data verified correctly.")
        else:
            print("Failure: Data mismatch.")
            print(data)
    else:
        print("Failure: Status file not created.")

if __name__ == "__main__":
    test_dashboard_integration()
