# data_collector.py
# sudo/python as admin required
import time
import threading
from collections import defaultdict
import psutil
from scapy.all import sniff, IP, IPv6, TCP, UDP
import signal
import pandas as pd

TIME_WINDOW = 2        # kaç saniyede bir örnek toplanacak (train verisi için)
MAP_REFRESH = 2        # conn_map kaç saniyede bir yenilensin
BPF_FILTER = "ip or ip6"

keep_running = True
pid_bytes = defaultdict(lambda: {'up': 0, 'down': 0})
lock = threading.Lock()
conn_map = {}
last_map_refresh = 0

def signal_handler(sig, frame):
    global keep_running
    print("\nDuruyor... veri kaydedilecek.")
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

def build_conn_map():
    new_map = {}
    for c in psutil.net_connections(kind='inet'):
        try:
            if c.laddr and c.raddr and c.pid and c.status == 'ESTABLISHED':
                l_ip, l_port = c.laddr
                r_ip, r_port = c.raddr
                # Fix: Use socket constants instead of psutil constants
                import socket
                proto = 6 if c.type == socket.SOCK_STREAM else 17
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
    direction = 'out'  # default: src -> dst is outgoing from local machine
    # If mapping not found, try reversed key (packet could be incoming)
    if pid is None:
        rev = (dst, int(dport), src, int(sport), proto)
        with lock:
            pid = conn_map.get(rev)
        if pid is not None:
            direction = 'in'

    return pid, direction

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
    pkt_len = len(pkt)
    with lock:
        if direction == 'out':
            pid_bytes[pid]['up'] += pkt_len
        else:
            pid_bytes[pid]['down'] += pkt_len

def sniffer():
    sniff(filter=BPF_FILTER, prn=packet_handler, store=False)

def get_proc_name(pid):
    try:
        return psutil.Process(pid).name()
    except Exception:
        return "?"

def main():
    t = threading.Thread(target=sniffer, daemon=True)
    t.start()
    print("Veri toplama başladı. Ctrl+C ile durdurup CSV oluşturabilirsiniz.")
    samples = []
    try:
        while keep_running:
            time.sleep(TIME_WINDOW)
            with lock:
                snapshot = dict(pid_bytes)
                pid_bytes.clear()
            for pid, vals in snapshot.items():
                up_kbps = vals['up'] / 1024.0 / TIME_WINDOW
                down_kbps = vals['down'] / 1024.0 / TIME_WINDOW
                if up_kbps > 0 or down_kbps > 0:
                    samples.append({
                        'process_name': get_proc_name(pid),
                        'upload_kbps': up_kbps,
                        'download_kbps': down_kbps
                    })
                    print(f"{get_proc_name(pid):30} ↑{up_kbps:7.2f} KB/s ↓{down_kbps:7.2f} KB/s")
    except KeyboardInterrupt:
        pass

    if samples:
        df = pd.DataFrame(samples)
        df.to_csv('app_traffic_baseline.csv', index=False)
        print(f"\n{len(samples)} satır veri kaydedildi -> app_traffic_baseline.csv")
    else:
        print("\nHiç veri toplanmadı.")

if __name__ == "__main__":
    main()
