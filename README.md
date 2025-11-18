# 🛡️ AINetMonitor

**AI-Powered Network Usage Monitor with Anomaly Detection**

AINetMonitor, ağ trafiğinizi gerçek zamanlı olarak izleyen ve yapay zeka tabanlı anomali tespiti ile şüpheli aktiviteleri tespit eden gelişmiş bir masaüstü uygulamasıdır.

![AINetMonitor](assets/icon.ico)

## ✨ Özellikler

### 🔍 **Gerçek Zamanlı Ağ İzleme**
- Tüm çalışan uygulamaların ağ kullanımını anlık izleme
- İndirilen/yüklenen veri miktarları (MB/saniye)
- İnternet trafiğine odaklı filtreleme (yerel ağ trafiği hariç)
- Toplam bant genişliği kullanım istatistikleri

### 🤖 **AI Tabanlı Anomali Tespiti**
- IsolationForest algoritması ile anormal ağ davranışlarını tespit
- 1787+ gerçek veri örneği ile eğitilmiş model
- Şüpheli aktiviteler için anlık uyarılar
- Adaptive learning ile sürekli iyileşen tespit

### 🎨 **Modern Kullanıcı Arayüzü**
- Karanlık tema desteği
- Çift tablo görünümü (Normal/Anormal aktiviteler)
- Tıklanabilir sütun başlıkları ile sıralama
- Gerçek zamanlı istatistikler ve sayaçlar

### 🔔 **Akıllı Bildirimler**
- Windows toast bildirimleri
- Anomali tespit edildiğinde anlık uyarılar
- Sistem tepsisi entegrasyonu

## 🚀 Kurulum

### Gereksinimler
- **Python 3.8+** (önerilen: Python 3.10+)
- **Windows 10/11** (tkinter desteği için)
- **Yönetici yetkileri** (ağ paket yakalama için)

### Adım 1: Repository'yi İndirin
```bash
git clone https://github.com/EnesK41/smart-network-usage-monitor.git
cd smart-network-usage-monitor
```

### Adım 2: Bağımlılıkları Kurun
```bash
# Sanal ortam oluşturun (isteğe bağlı ama önerilen)
python -m venv venv
venv\Scripts\activate

# Gereken paketleri kurun
pip install -r requirements.txt
```

### Adım 3: Uygulamayı Çalıştırın
```bash
# Ana uygulamayı başlatın
python src/dashboard.py

# Veri toplama için (model eğitimi)
python src/data-collector.py
```

## 📊 Veri Toplama ve Model Eğitimi

**⚠️ ÖNEMLİ**: Uygulamayı kullanmadan önce kendi verilerinizle model eğitmelisiniz!

### Adım 1: Veri Toplama
```bash
# Ağ trafiği verilerini toplamak için (5-10 dakika çalıştırın)
python src/data-collector.py
```

### Adım 2: Model Eğitimi
```bash
# Toplanan verilerle modeli yeniden eğitin
python src/train-app-model.py
```

### Adım 3: Uygulamayı Çalıştırın
```bash
# Artık eğitilmiş modelinizle uygulamayı kullanabilirsiniz
python src/dashboard.py
```

Eğitim tamamlandığında `models/` klasöründe güncellenmiş model dosyaları oluşacaktır.

## 🔧 Kişisel EXE Dosyası Oluşturma

Modelinizi eğittikten sonra, kendi kişiselleştirilmiş EXE dosyanızı oluşturabilirsiniz:

```bash
cd build
python build_exe.py
```

Bu işlem `dist/` klasöründe sizin verilerinizle eğitilmiş `AINetMonitor.exe` dosyasını oluşturacaktır.

## 🎯 Kullanım

### Ana Uygulama (Dashboard)
1. **Başlatma**: `python src/dashboard.py` komutuyla uygulamayı başlatın
2. **Görünüm**: İki tablo ile normal ve anormal aktiviteleri izleyin
3. **Sıralama**: Sütun başlıklarına tıklayarak verilerinizi sıralayın
4. **Bildirimler**: Anormal aktivite tespit edildiğinde otomatik bildirim alın

### Arayüz Açıklamaları
- **🟢 Normal Aktiviteler**: Beklenen ağ kullanım kalıpları
- **🔴 Anormal Aktiviteler**: AI tarafından şüpheli bulunan aktiviteler
- **📊 İstatistikler**: Toplam uygulama sayısı, toplam trafik, anomali sayısı
- **🎨 Tema**: Karanlık/aydınlık tema geçişi

## 🛠️ Teknik Detaylar

### Kullanılan Teknolojiler
- **GUI**: Tkinter (Python built-in)
- **Ağ İzleme**: psutil, scapy
- **Machine Learning**: scikit-learn (IsolationForest)
- **Veri İşleme**: pandas, numpy
- **Bildirimler**: plyer
- **Model Depolama**: joblib

### Anomali Tespit Algoritması
- **Model**: Isolation Forest
- **Özellikler**: Download/Upload hızları, toplam trafik, zaman bazlı kalıplar
- **Eşik Değeri**: Dinamik olarak ayarlanır
- **Güncelleme**: Model periyodik olarak yeniden eğitilebilir

### Performans
- **CPU Kullanımı**: Düşük (%1-3)
- **Bellek**: ~50-100MB
- **Güncelleme Sıklığı**: 2 saniyede bir
- **Veri Depolama**: Minimal (sadece model dosyaları)

## 🔒 Güvenlik

### İzinler
- **Ağ İzleme**: Yüklü uygulamaların ağ trafiğini okuma
- **Sistem Erişimi**: Process bilgilerine erişim
- **Dosya Sistemi**: Model dosyalarını okuma/yazma

### Gizlilik
- **Veri Toplama**: Sadece ağ istatistikleri, kişisel veri toplama YOK
- **Dış Bağlantı**: İnternet bağlantısı gerekmez
- **Veri Paylaşımı**: Hiçbir veri dışarıya gönderilmez


### v1.0.0 (Mevcut)
- ✅ Gerçek zamanlı ağ izleme
- ✅ AI anomali tespiti
- ✅ Modern GUI arayüzü
- ✅ Windows bildirim desteği
- ✅ EXE derleme desteği

### Gelecek Sürümler
- 📅 MacOS/Linux desteği
- 📅 Web dashboard
- 📅 Detaylı raporlama
- 📅 Otomatik güncelleme

## 📦 Dağıtım ve Paylaşım

### ⚠️ Önemli Not
Bu proje **hazır EXE** içermez çünkü:
- Her kullanıcı **kendi verilerini toplamalı**
- **Kendi modelini eğitmeli**  
- **Kişiselleştirilmiş anomali tespiti** oluşturmalı

### Kendi EXE'nizi Paylaşmak
Eğer kendi eğittiğiniz modeli paylaşmak isterseniz:
1. Modelinizi eğitin (`python src/train-app-model.py`)
2. EXE oluşturun (`python build/build_exe.py`)
3. **GitHub Releases** kullanarak paylaşabilirsiniz

### Platform Uyumluluğu
- ✅ **Windows 10/11**: PyInstaller ile EXE oluşturma
- ❌ **macOS**: Windows EXE'si çalışmaz (Python source gerekli)  
- ❌ **Linux**: Windows EXE'si çalışmaz (Python source gerekli)

### Cross-Platform Kullanım
Mac ve Linux kullanıcıları için Python source code:
```bash
git clone https://github.com/EnesK41/smart-network-usage-monitor.git
cd smart-network-usage-monitor
pip install -r requirements.txt
python src/dashboard.py
```

**Not**: Her platform için ayrı executable oluşturmak mümkündür, ancak şu an sadece Windows desteklenmektedir.

---