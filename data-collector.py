import psutil
import time
import os
import signal
import pandas as pd
from collections import defaultdict

# --- Globals and Signal Handling ---
keep_running = True
all_data = [] # Toplanan verileri saklamak için liste

def signal_handler(sig, frame):
    global keep_running
    print("\nVeri toplama durduruluyor...")
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

# --- Process Information Caching ---
last_bytes = defaultdict(lambda: {'sent': 0, 'recv': 0})
process_names = {}

def get_process_name(pid):
    if pid not in process_names:
        try:
            process_names[pid] = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_names[pid] = '?'
    return process_names[pid]

# --- Main Loop ---
print("--- Yapay Zeka Eğitimi İçin Veri Toplama Başlatıldı ---")
print("Bilgisayarınızı normal şekilde kullanın. Durdurmak ve kaydetmek için Ctrl+C tuşuna basın.")
INTERVAL = 2 # Saniye

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
                    continue

        for pid, data in current_bytes.items():
            proc_name = get_process_name(pid)
            
            upload_speed = (data['sent'] - last_bytes[pid]['sent']) / 1024 / INTERVAL
            download_speed = (data['recv'] - last_bytes[pid]['recv']) / 1024 / INTERVAL
            
            if upload_speed > 0 or download_speed > 0:
                data_point = {
                    'process_name': proc_name,
                    'upload_kbps': upload_speed,
                    'download_kbps': download_speed
                }
                all_data.append(data_point)
            
            last_bytes[pid] = data

        time.sleep(INTERVAL)

    except Exception as e:
        print(f"Bir hata oluştu: {e}")
        break

# --- Verileri CSV dosyasına kaydet ---
if all_data:
    print(f"\n{len(all_data)} adet veri toplandı. 'app_traffic_baseline.csv' dosyasına kaydediliyor...")
    df = pd.DataFrame(all_data)
    df.to_csv('app_traffic_baseline.csv', index=False)
    print("Kayıt tamamlandı.")
else:
    print("\nHiç veri toplanmadı.")