import sys
import subprocess
import os
from pathlib import Path

def test_subprocess_call():
    print("Testing subprocess.Popen with Path object vs String...")
    
    # Create a dummy script to run
    dummy_script = Path("dummy_bot.py")
    with open(dummy_script, "w") as f:
        f.write("print('Hello from dummy bot')")
        
    try:
        # Test 1: Passing Path object (Simulating the bug)
        print("\nTest 1: Passing Path object (Expected to fail on some systems)...")
        try:
            process = subprocess.Popen(
                [sys.executable, dummy_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                print("SUCCESS: Path object worked (System handles it)")
            else:
                print(f"FAILURE: Process failed with code {process.returncode}")
        except Exception as e:
            print(f"CRASH: Failed to launch with Path object: {e}")

        # Test 2: Passing String (The Fix)
        print("\nTest 2: Passing String (Expected to work everywhere)...")
        try:
            process = subprocess.Popen(
                [sys.executable, str(dummy_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                print("SUCCESS: String path worked")
                print(f"Output: {stdout.decode().strip()}")
            else:
                print(f"FAILURE: Process failed with code {process.returncode}")
        except Exception as e:
            print(f"CRASH: Failed to launch with String path: {e}")
            
    finally:
        # Cleanup
        if dummy_script.exists():
            os.remove(dummy_script)

if __name__ == "__main__":
    test_subprocess_call()
