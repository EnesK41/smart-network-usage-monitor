import psutil
import time
import os
from collections import defaultdict
import signal  

# --- Globals and Signal Handling ---
keep_running = True

def signal_handler(sig, frame):
    """ Changes the global flag to stop the main loop when Ctrl+C is pressed. """
    global keep_running
    print("\nStopping the monitor...")
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

last_bytes = defaultdict(lambda: {'sent': 0, 'recv': 0})
process_names = {}

def get_process_name(pid):
    """ Get and cache the name of a process from its PID. """
    if pid not in process_names:
        try:
            process_names[pid] = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_names[pid] = '?'
    return process_names[pid]

print("--- Live Application Network Monitor ---")
print("Press Ctrl+C to stop.")

while keep_running:
    try:
        connections = psutil.net_connections()
        current_bytes = defaultdict(lambda: {'sent': 0, 'recv': 0})

        for conn in connections:
            if conn.pid is not None and conn.status == 'ESTABLISHED':
                try:
                    proc_io = psutil.Process(conn.pid).io_counters()
                    current_bytes[conn.pid]['sent'] += proc_io.write_bytes
                    current_bytes[conn.pid]['recv'] += proc_io.read_bytes
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue # Skip processes that have ended or we can't access

        # Clear the screen
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{'PROCESS':<30} | {'UPLOAD (KB/s)':<20} | {'DOWNLOAD (KB/s)':<20}")
        print("-" * 75)

        for pid, data in current_bytes.items():
            proc_name = get_process_name(pid)
            
            upload_speed = (data['sent'] - last_bytes[pid]['sent']) / 1024
            download_speed = (data['recv'] - last_bytes[pid]['recv']) / 1024

            if upload_speed > 0.1 or download_speed > 0.1:
                print(f"{proc_name:<30} | {upload_speed:<20.2f} | {download_speed:<20.2f}")
            
            last_bytes[pid] = data

        time.sleep(1)

    except Exception as e:
        print(f"An error occurred: {e}")
        break

print("Monitor stopped.")