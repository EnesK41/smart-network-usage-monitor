import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

print("Baseline veri seti yükleniyor...")
try:
    df = pd.read_csv('app_traffic_baseline.csv')
except FileNotFoundError:
    print("Hata: 'app_traffic_baseline.csv' bulunamadı. Lütfen önce data_collector.py dosyasını çalıştırın.")
    exit()

# --- Model için Veri Hazırlama ---
print("Veri model için hazırlanıyor...")
# 'process_name' sütununu sayısal bir formata (One-Hot Encoding) dönüştür
features = pd.get_dummies(df, columns=['process_name'])

print("Anomali tespit modeli eğitiliyor...")

# Modeli başlat
model = IsolationForest(contamination='auto', random_state=42, n_estimators=200)

# Modeli eğit
model.fit(features)

print("Model eğitimi tamamlandı.")

# Eğitilmiş modeli ve modelin öğrendiği sütunları kaydet
joblib.dump(model, 'app_anomaly_model.joblib')
joblib.dump(features.columns, 'model_columns.joblib')

print("Model ve sütun bilgileri başarıyla kaydedildi!")