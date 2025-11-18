# real_time_detector.py
import time
import threading
from collections import defaultdict
import psutil
from scapy.all import sniff, IP, IPv6, TCP, UDP
import signal
import pandas as pd
import joblib
import sys

TIME_WINDOW = 2
MAP_REFRESH = 2
BPF_FILTER = "ip or ip6"

# load model & columns
try:
    model = joblib.load('app_anomaly_model.joblib')
    model_columns = joblib.load('model_columns.joblib')
    # ensure model_columns is an Index or list
    model_columns = list(model_columns)
    print("Model yüklendi.")
except Exception as e:
    print("Model dosyaları bulunamadı veya yüklenemedi:", e)
    sys.exit(1)

keep_running = True
pid_bytes = defaultdict(lambda: {'up': 0, 'down': 0})
lock = threading.Lock()
conn_map = {}
last_map_refresh = 0
seen_unknown = set()

def signal_handler(sig, frame):
    global keep_running
    print("\nDurduruluyor...")
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

def build_conn_map():
    new_map = {}
    for c in psutil.net_connections(kind='inet'):
        try:
            if c.laddr and c.raddr and c.pid:
                l_ip, l_port = c.laddr
                r_ip, r_port = c.raddr
                proto = 6 if c.type == psutil.SOCK_STREAM else 17
                key = (l_ip, int(l_port), r_ip, int(r_port), proto)
                rev = (r_ip, int(r_port), l_ip, int(l_port), proto)
                new_map[key] = c.pid
                new_map[rev] = c.pid
        except Exception:
            continue
    return new_map

def match_packet_to_pid(pkt):
    if pkt.haslayer(IP):
        ip = pkt[IP]
        proto = ip.proto
        src = ip.src
        dst = ip.dst
    elif pkt.haslayer(IPv6):
        ip = pkt[IPv6]
        proto = ip.nh
        src = ip.src
        dst = ip.dst
    else:
        return None, None
    sport = None; dport = None
    if pkt.haslayer(TCP):
        sport = pkt[TCP].sport; dport = pkt[TCP].dport; proto = 6
    elif pkt.haslayer(UDP):
        sport = pkt[UDP].sport; dport = pkt[UDP].dport; proto = 17
    else:
        return None, None
    key = (src, int(sport), dst, int(dport), proto)
    with lock:
        pid = conn_map.get(key)
    if pid is None:
        rev = (dst, int(dport), src, int(sport), proto)
        with lock:
            pid = conn_map.get(rev)
        if pid is not None:
            return pid, 'in'
    return (pid, 'out') if pid else (None, None)

def packet_handler(pkt):
    global last_map_refresh
    now = time.time()
    if now - last_map_refresh > MAP_REFRESH:
        new_map = build_conn_map()
        with lock:
            conn_map.clear()
            conn_map.update(new_map)
            last_map_refresh = now

    pid, direction = match_packet_to_pid(pkt)
    if pid is None:
        return
    l = len(pkt)
    with lock:
        if direction == 'out':
            pid_bytes[pid]['up'] += l
        else:
            pid_bytes[pid]['down'] += l

def sniffer():
    sniff(filter=BPF_FILTER, prn=packet_handler, store=False)

def get_proc_name(pid):
    try:
        return psutil.Process(pid).name()
    except Exception:
        return "?"

def run_detection():
    t = threading.Thread(target=sniffer, daemon=True)
    t.start()
    print("Canlı tespit başladı. Ctrl+C ile durdurun.")
    try:
        while keep_running:
            time.sleep(TIME_WINDOW)
            with lock:
                snapshot = dict(pid_bytes)
                pid_bytes.clear()
            for pid, vals in snapshot.items():
                up_kbps = vals['up'] / 1024.0 / TIME_WINDOW
                down_kbps = vals['down'] / 1024.0 / TIME_WINDOW
                if up_kbps < 0.01 and down_kbps < 0.01:
                    continue
                name = get_proc_name(pid)
                colname = f"process_name_{name}"
                if colname in model_columns:
                    live_row = pd.DataFrame(0, index=[0], columns=model_columns)
                    live_row['upload_kbps'] = up_kbps
                    live_row['download_kbps'] = down_kbps
                    live_row[colname] = 1
                    try:
                        pred = model.predict(live_row)[0]
                        if pred == -1:
                            print(f"🚨 Davranışsal Anomali: {name} ↑{up_kbps:.2f} KB/s ↓{down_kbps:.2f} KB/s")
                        else:
                            print(f"OK: {name} ↑{up_kbps:.2f} KB/s ↓{down_kbps:.2f} KB/s")
                    except Exception as e:
                        print("Model tahmini sırasında hata:", e)
                else:
                    if name not in seen_unknown:
                        print(f"🚨 Bilinmeyen uygulama tespit edildi: {name} (ilk görüldü)")
                        seen_unknown.add(name)
                    else:
                        print(f"⚪️ Bilinmeyen (daha önce görüldü): {name} ↑{up_kbps:.2f} KB/s ↓{down_kbps:.2f} KB/s")
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run_detection()
