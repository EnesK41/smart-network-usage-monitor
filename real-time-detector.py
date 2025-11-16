import psutil
import time
import os
import signal
import pandas as pd
import joblib
from collections import defaultdict
from datetime import datetime

from app_monitor import get_process_name

# --- Modelleri Yükle ---
try:
    model = joblib.load('app_anomaly_model.joblib')
    model_columns = joblib.load('model_columns.joblib')
    print("✅ Yapay zeka modeli ve model hafızası başarıyla yüklendi.")
except FileNotFoundError:
    print("❌ Hata: Model dosyaları bulunamadı. Lütfen 'train-app-model.py' betiğini çalıştırın.")
    exit()

# --- Globals ve Signal Handling ---
keep_running = True
def signal_handler(sig, frame):
    global keep_running
    print("\nTespit programı durduruluyor... Rapor oluşturulacak...")
    keep_running = False

signal.signal(signal.SIGINT, signal_handler)

# --- Ağ Verisi Takibi ---
last_bytes = defaultdict(lambda: {'sent': 0, 'recv': 0})
process_names = {}
INTERVAL = 2 

# === REFINING #2 (HAFIZA): TOPLAMLARI TUTAN SÖZLÜK ===
# Artık tüm veriyi tutan 'all_session_data' listesi yok.
# Sadece bu özet sözlüğü var.
report_data = defaultdict(lambda: {
    'total_upload_kb': 0,
    'total_download_kb': 0,
    'anomaly_count': 0,
    'anomaly_type': set() # Gördüğü anomali tiplerini tutar
})
# ====================================================

# === REFINING #4 (GÜRÜLTÜ): BİLİNMEYENLERİ BİR KEZ GÖSTER ===
seen_unknown_apps = set()
# =======================================================

print("--- 🚀 Gerçek Zamanlı Anomali Tespiti Başlatıldı ---")
print("(Durdurmak için Ctrl+C tuşuna basın)")

start_time = time.time() # Programın başlangıç zamanı

while keep_running:
    try:
        current_loop_time = time.time()
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

        os.system('cls' if os.name == 'nt' else 'clear')
        print("--- 📡 CANLI AĞ ANALİZİ --- (Özet Rapor için Ctrl+C)")
        
        for pid, data in current_bytes.items():
            proc_name = get_process_name(pid)
            
            upload_speed = (data['sent'] - last_bytes[pid]['sent']) / 1024 / INTERVAL
            download_speed = (data['recv'] - last_bytes[pid]['recv']) / 1024 / INTERVAL
            
            last_bytes[pid] = data

            if upload_speed < 0.1 and download_speed < 0.1:
                continue

            # === REFINING #2: TOPLAMLARI GÜNCELLE ===
            report_data[proc_name]['total_upload_kb'] += upload_speed * INTERVAL
            report_data[proc_name]['total_download_kb'] += download_speed * INTERVAL
            # ======================================

            app_column_name = f"process_name_{proc_name}"
            
            if app_column_name in model_columns:
                live_row = pd.DataFrame(0, index=[0], columns=model_columns)
                live_row['upload_kbps'] = upload_speed
                live_row['download_kbps'] = download_speed
                live_row[app_column_name] = 1
                
                prediction = model.predict(live_row)
                
                if prediction[0] == -1:
                    print(f"🚨 ANOMALİ (Davranışsal): {proc_name} (Upload: {upload_speed:.2f} KB/s, Download: {download_speed:.2f} KB/s)")
                    report_data[proc_name]['anomaly_count'] += 1
                    report_data[proc_name]['anomaly_type'].add("Davranışsal")
                else:
                    print(f"✅ Normal: {proc_name} (Upload: {upload_speed:.2f} KB/s, Download: {download_speed:.2f} KB/s)")
            else:
                # === REFINING #4: GÜRÜLTÜYÜ AZALT ===
                if proc_name not in seen_unknown_apps:
                    # Bilinmeyen bir uygulamayı İLK KEZ görüyoruz. Uyar!
                    print(f"🚨🚨 ANOMALİ (Bilinmeyen): {proc_name} adlı BİLİNMEYEN bir uygulama internet kullanıyor!")
                    seen_unknown_apps.add(proc_name) # Görülenler listesine ekle
                    report_data[proc_name]['anomaly_count'] += 1
                    report_data[proc_name]['anomaly_type'].add("Bilinmeyen")
                else:
                    # Bu uygulamayı daha önce gördük, artık gürültü yapma.
                    print(f"⚪️ Normal (Bilinmeyen): {proc_name} (Upload: {upload_speed:.2f} KB/s, Download: {download_speed:.2f} KB/s)")
                # ==================================

        time.sleep(max(0, INTERVAL - (time.time() - current_loop_time))) 

    except Exception as e:
        if keep_running:
            print(f"Bir hata oluştu: {e}")
            break

# === YENİ: Döngü durduktan sonra TOPLAMLARA dayalı raporu oluştur ===
print("\n" + "="*50)
print("📊 OTURUM ÖZET RAPORU")
print("="*50)

if not report_data:
    print("Hiç ağ aktivitesi kaydedilmedi.")
else:
    total_duration = time.time() - start_time
    total_anomalies = 0
    total_upload_mb = 0
    total_download_mb = 0

    # Rapor verilerini Pandas DataFrame'e dönüştürme (daha kolay analiz için)
    # Önce 'set' olan anomali tiplerini 'str' yapalım
    for app in report_data:
        report_data[app]['anomaly_type'] = ', '.join(report_data[app]['anomaly_type'])
        
    df = pd.DataFrame.from_dict(report_data, orient='index')
    df.index.name = 'Uygulama'
    
    # Toplamları hesapla
    total_anomalies = df['anomaly_count'].sum()
    total_upload_mb = df['total_upload_kb'].sum() / 1024
    total_download_mb = df['total_download_kb'].sum() / 1024

    print(f"Toplam İzleme Süresi: {total_duration:.2f} saniye")
    print(f"Toplam Yükleme (Upload): {total_upload_mb:.2f} MB")
    print(f"Toplam İndirme (Download): {total_download_mb:.2f} MB")
    print(f"Tespit Edilen Toplam Anomali Sayısı: {total_anomalies} adet")

    if total_anomalies > 0:
        print("\n--- En Çok Anomali Yapan Uygulamalar ---")
        print(df[df['anomaly_count'] > 0][['anomaly_count', 'anomaly_type']].sort_values(by='anomaly_count', ascending=False).to_string())

    print("\n--- En Çok Veri Kullanan Uygulamalar ---")
    df['total_mb'] = (df['total_upload_kb'] + df['total_download_kb']) / 1024
    print(df[['total_mb']].sort_values(by='total_mb', ascending=False).head(10).to_string(formatters={'total_mb': '{:,.2f} MB'.format}))

print("="*50)
print("Raporlama tamamlandı.")