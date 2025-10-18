import time
from collections import defaultdict
import pandas as pd
from scapy.all import sniff,IP
import signal 

keep_running = True
def signal_handler(sig, frame):
    """
    This function will be called when Ctrl+C is pressed.
    It changes the global flag to stop the main loop.
    """
    global keep_running
    print("\nStopping the sniffer... Please wait for the current capture to finish.")
    keep_running = False

# CHANGED: Register our new function to handle the Ctrl+C signal (SIGINT)
signal.signal(signal.SIGINT, signal_handler)


def extract_features(packets):
    if not packets:
        return None
    
    features = {}
    
    #total number of packets
    features['packet_count'] = len(packets)
    
    #total size of all packets in bytes
    total_size = sum(len(p) for p in packets)
    
    #find the number of unique source IPs
    source_ips = {p[IP].src for p in packets if p.haslayer(IP)} 
    features['unique_src_ips'] = len(source_ips)
    
    #calculating the average packet size
    if features['packet_count'] > 0:
        features['avg_packet_size'] = total_size / features['packet_count']
    else:
        features['avg_packet_size'] = 0

    return features

print("Starting real-time feature extraction... Press Ctrl+C to stop.")
TIME_WINDOW = 5

while keep_running:
    try:
        print(f"\n--- Capturing packets for {TIME_WINDOW} seconds ---")
        captured_packets = sniff(timeout=TIME_WINDOW)
        
        window_features = extract_features(captured_packets)
        
        if window_features:
            print("Features for this window:")
            df = pd.DataFrame([window_features])
            print(df.to_string(index=False))
        else:
            if keep_running:
                print("No traffic captured in this window.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        break