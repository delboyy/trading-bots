import sys
import os
import time
import multiprocessing
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from grok.utils.status_tracker import StatusTracker

def worker(i):
    start_time = time.time()
    print(f"Worker {i} starting init at {datetime.now().strftime('%H:%M:%S.%f')}")
    tracker = StatusTracker() # This should sleep for 1-20s
    end_time = time.time()
    duration = end_time - start_time
    print(f"Worker {i} finished init at {datetime.now().strftime('%H:%M:%S.%f')} (Duration: {duration:.2f}s)")

if __name__ == "__main__":
    print("Starting Jitter Verification Test with 5 workers...")
    processes = []
    for i in range(5):
        p = multiprocessing.Process(target=worker, args=(i,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()
    
    print("Test Complete. Check timestamps above for stagger.")
