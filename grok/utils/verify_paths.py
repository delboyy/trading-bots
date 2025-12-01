
import sys
import os
from pathlib import Path

def verify_paths():
    print("Verifying path resolution logic...")
    
    # Simulate being in grok/live_bots/scalping/
    current_file = Path(os.getcwd()) / "grok/live_bots/scalping/dummy_bot.py"
    
    # Logic used by bots: parents[3]
    project_root = current_file.resolve().parents[3]
    print(f"Calculated project root (parents[3]): {project_root}")
    
    # Check if grok exists in this root
    grok_path = project_root / "grok"
    if grok_path.exists():
        print("✅ 'grok' directory found in calculated root.")
    else:
        print("❌ 'grok' directory NOT found in calculated root.")
        
    # Simulate being in grok/live_bots/long_term/
    current_file_lt = Path(os.getcwd()) / "grok/live_bots/long_term/dummy_bot.py"
    
    # Logic used by os.path bots: 4 dirnames
    # os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(abspath))))
    path_str = str(current_file_lt)
    root_os = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(path_str))))
    print(f"Calculated project root (4 dirnames): {root_os}")
    
    if os.path.exists(os.path.join(root_os, "grok")):
        print("✅ 'grok' directory found in calculated root (os.path).")
    else:
        print("❌ 'grok' directory NOT found in calculated root (os.path).")

if __name__ == "__main__":
    verify_paths()
