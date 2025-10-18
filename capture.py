from scapy.all import sniff, IP

def process_packet(packet):
    # Check if the packet has an Internet Protocol (IP) layer
    if packet.haslayer(IP):
        source_ip = packet[IP].src
        destination_ip = packet[IP].dst
        
        # Get the protocol type (e.g., TCP, UDP, ICMP)
        protocol = packet[IP].protocol
        
        size = len(packet)

        print(f"Source IP: {source_ip}, Destination IP: {destination_ip}, Protocol: {protocol}, Size: {size} bytes")        