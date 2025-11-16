import streamlit as st
import psutil
import time
import pandas as pd
import joblib
from collections import defaultdict
from datetime import datetime

# === 1. Sayfa Ayarları ===
st.set_page_config(
    page_title="Akıllı Ağ Monitörü",
    page_icon="📡",
    layout="wide"
)

# === 2. Modelleri Yükle ===
@st.cache_resource
def load_models():
    try:
        model = joblib.load('app_anomaly_model.joblib')
        model_columns = joblib.load('model_columns.joblib')
        return model, model_columns
    except FileNotFoundError:
        st.error("Hata: Model dosyaları ('app_anomaly_model.joblib', 'model_columns.joblib') bulunamadı.")
        st.error("Lütfen önce 'train-app-model.py' betiğini çalıştırın.")
        return None, None

model, model_columns = load_models()

if model is None:
    st.stop()

# === 3. Kalıcı Durum (Session State) ===
if 'start_time' not in st.session_state:
    st.session_state.start_time = time.time()
    st.session_state.total_anomalies = 0
    st.session_state.total_upload_mb = 0
    st.session_state.total_download_mb = 0
    st.session_state.anomaly_log = []
    st.session_state.seen_unknown_apps = set()
    st.session_state.last_bytes = defaultdict(lambda: {'sent': 0, 'recv': 0})
    st.session_state.process_names = {}
    st.session_state.first_loop_complete = False

INTERVAL = 2 

def get_process_name(pid):
    if pid not in st.session_state.process_names:
        try:
            st.session_state.process_names[pid] = psutil.Process(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            st.session_state.process_names[pid] = '?'
    return st.session_state.process_names[pid]

# === 4. Arayüz Başlığı ===
st.title("📡 Akıllı Ağ Anomali Tespit Sistemi")
st.markdown("---")

# === 5. Özet Rapor Alanı (st.metric) ===
st.subheader("📊 GENEL OTURUM ÖZETİ")
col1, col2, col3, col4 = st.columns(4)
placeholder_anomalies = col1.empty()
placeholder_duration = col2.empty()
placeholder_upload = col3.empty()
placeholder_download = col4.empty()
st.markdown("---")

# === 6. Ana Arayüz Düzeni (Yer Tutucuları Oluştur) ===
col_status, col_anomalies = st.columns(2)

with col_status:
    st.subheader("CANLI AĞ TRAFİĞİ")
    live_traffic_placeholder = st.empty() # Bu yer tutucuyu oluştur

with col_anomalies:
    st.subheader("🚨 TESPİT EDİLEN ANOMALİLER")
    anomaly_placeholder = st.empty() # Bu yer tutucuyu oluştur

# --- Ana Tespit Döngüsü ---
while True:
    try:
        current_loop_time = time.time()
        
        # === DÜZELTME 1: SAYAÇ PATLAMASI (Benzersiz PID'leri al) ===
        unique_pids = set()
        for conn in psutil.net_connections():
            if conn.pid is not None and conn.status == 'ESTABLISHED':
                unique_pids.add(conn.pid)
        
        current_bytes = defaultdict(lambda: {'sent': 0, 'recv': 0})
        # Şimdi, her benzersiz uygulama (PID) için SADECE BİR KEZ veri al
        for pid in unique_pids:
            try:
                proc_io = psutil.Process(pid).io_counters()
                current_bytes[pid]['sent'] = proc_io.write_bytes
                current_bytes[pid]['recv'] = proc_io.read_bytes
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        # ========================================================

        live_traffic_list = []
        
        if st.session_state.first_loop_complete:
            # Artık 'current_bytes' SADECE benzersiz uygulamaları içeriyor
            for pid, data in current_bytes.items():
                proc_name = get_process_name(pid)
                
                # 'Isınma turu' mantığı: PID'yi ilk kez görüyorsak hız hesaplama
                if pid in st.session_state.last_bytes:
                    upload_speed = (data['sent'] - st.session_state.last_bytes[pid]['sent']) / 1024 / INTERVAL
                    download_speed = (data['recv'] - st.session_state.last_bytes[pid]['recv']) / 1024 / INTERVAL
                else:
                    upload_speed = 0 # Bu PID yeni başladı, ilk ölçümü '0' kabul et
                    download_speed = 0
                
                if upload_speed < 0: upload_speed = 0
                if download_speed < 0: download_speed = 0

                if upload_speed < 0.1 and download_speed < 0.1:
                    continue
                
                # Bu hesaplama artık DOĞRU (çünkü 'upload_speed' artık patlamıyor)
                st.session_state.total_upload_mb += (upload_speed * INTERVAL) / 1024
                st.session_state.total_download_mb += (download_speed * INTERVAL) / 1024

                app_column_name = f"process_name_{proc_name}"
                status = "✅ Normal"
                is_anomaly = False

                if app_column_name in model_columns:
                    live_row = pd.DataFrame(0, index=[0], columns=model_columns)
                    live_row['upload_kbps'] = upload_speed
                    live_row['download_kbps'] = download_speed
                    if app_column_name in live_row.columns:
                         live_row[app_column_name] = 1
                    
                    prediction = model.predict(live_row)
                    
                    if prediction[0] == -1:
                        status = f"🚨 ANOMALİ (Davranışsal)"
                        is_anomaly = True
                
                else:
                    if proc_name not in st.session_state.seen_unknown_apps:
                        status = f"🚨🚨 ANOMALİ (Bilinmeyen)"
                        is_anomaly = True
                        st.session_state.seen_unknown_apps.add(proc_name)
                    else:
                        status = "⚪️ Normal (Bilinmeyen)"
                
                app_info = {
                    "Uygulama": proc_name,
                    "Durum": status,
                    "Upload (KB/s)": f"{upload_speed:.2f}",
                    "Download (KB/s)": f"{download_speed:.2f}"
                }
                live_traffic_list.append(app_info)
                
                if is_anomaly:
                    st.session_state.total_anomalies += 1
                    app_info['Zaman'] = datetime.now().strftime("%H:%M:%S")
                    st.session_state.anomaly_log.append(app_info)
        
        # 'Isınma turu' ve bir sonraki döngü için sayaçları güncelle
        st.session_state.last_bytes = current_bytes
        st.session_state.first_loop_complete = True
        
        # === 7. ARAYÜZÜ GÜNCELLE ===
        
        duration_seconds = int(time.time() - st.session_state.start_time)
        placeholder_anomalies.metric(label="Toplam Anomali Sayısı", value=st.session_state.total_anomalies)
        placeholder_duration.metric(label="Geçen Süre (Saniye)", value=duration_seconds)
        placeholder_upload.metric(label="Toplam Upload (MB)", value=f"{st.session_state.total_upload_mb:.2f}")
        placeholder_download.metric(label="Toplam Download (MB)", value=f"{st.session_state.total_download_mb:.2f}")

        # === DÜZELTME 2: 'key' ve 'ID' Hatası ===
        # Yer tutucunun (placeholder) KENDİSİNİ doğrudan güncelliyoruz.
        live_traffic_placeholder.data_editor(live_traffic_list, use_container_width=True, hide_index=True)

        if not st.session_state.anomaly_log:
            anomaly_placeholder.info("Henüz bir anomali tespit edilmedi.")
        else:
            anomaly_placeholder.data_editor(st.session_state.anomaly_log[::-1][:10], use_container_width=True, hide_index=True)
        # ======================================

        time.sleep(max(0, INTERVAL - (time.time() - current_loop_time))) 

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
        break