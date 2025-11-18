import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import threading
import time
from datetime import datetime
from collections import defaultdict

# Windows notifications
try:
    from plyer import notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("plyer not available - notifications disabled")

# Model imports
try:
    import joblib
    import pandas as pd
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class NetworkMonitorDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("🌐 AINetMonitor")
        self.root.geometry("1400x900")  # Bigger for new table
        
        # Set window icon (if available)
        try:
            self.root.iconbitmap("icon.ico")  # Will add this icon file
        except:
            pass  # If icon file doesn't exist, continue without it
        
        # Prevent window from being resized too small
        self.root.minsize(1200, 700)
        
        # Dark Mode Configuration
        self.setup_dark_theme()
        
        # Network monitoring state
        self.monitoring = True
        self.start_time = time.time()
        self.last_io_stats = {}
        self.total_anomalies = 0
        self.total_upload_mb = 0.0
        self.total_download_mb = 0.0
        self.anomaly_log = []
        self.seen_unknown = set()
        self.app_usage_history = defaultdict(lambda: {
            'upload': 0, 'download': 0, 'samples': 0, 
            'first_seen': time.time(), 'total_upload_speed': 0, 'total_download_speed': 0
        })
        self.last_notification_time = 0
        self.current_process_data = []  # Store current session data
        self.sort_mode = 'time'  # 'upload', 'download', 'time'
        
        # Load model
        self.model = None
        self.model_columns = None
        self.load_model()
        
        # Create interface
        self.create_widgets()
        
        # Start monitoring
        self.start_monitoring_thread()
        
    def setup_dark_theme(self):
        """Setup dark mode theme for tkinter"""
        # Dark color scheme
        self.bg_color = "#1e1e1e"          # Dark background
        self.fg_color = "#ffffff"          # White text
        self.accent_color = "#0078d4"      # Blue accent
        self.frame_color = "#2d2d2d"       # Darker frame
        self.success_color = "#00ff88"     # Green for success
        self.warning_color = "#ffaa00"     # Orange for warning
        self.error_color = "#ff4444"       # Red for error
        
        # Apply to root window
        self.root.configure(bg=self.bg_color)
        
        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure ttk styles for dark theme
        style.configure('TLabel', background=self.bg_color, foreground=self.fg_color, font=('Arial', 10))
        style.configure('TFrame', background=self.bg_color)
        style.configure('TLabelFrame', background=self.bg_color, foreground=self.fg_color, borderwidth=1)
        style.configure('TButton', background=self.frame_color, foreground=self.fg_color, borderwidth=1)
        style.map('TButton', background=[('active', self.accent_color)])
        style.configure('Treeview', background=self.frame_color, foreground=self.fg_color, fieldbackground=self.frame_color)
        style.configure('Treeview.Heading', background=self.accent_color, foreground=self.fg_color)

    def load_model(self):
        """Load anomaly detection model"""
        if not SKLEARN_AVAILABLE:
            print("scikit-learn not available")
            return
            
        try:
            self.model = joblib.load("app_anomaly_model.joblib")
            self.model_columns = joblib.load("model_columns.joblib")
            if not isinstance(self.model_columns, list):
                self.model_columns = list(self.model_columns)
            print("Model loaded successfully!")
        except Exception as e:
            print(f"Model load error: {e}")

    def create_widgets(self):
        """Create all interface elements"""
        
        # === 1. TOP METRICS SECTION ===
        metrics_frame = ttk.LabelFrame(self.root, text="📊 Genel İstatistikler")
        metrics_frame.pack(fill="x", padx=10, pady=5)
        
        # Metrics grid
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill="x", padx=10, pady=10)
        
        # Anomaly count
        ttk.Label(metrics_grid, text="🚨 Toplam Anomali:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.anomaly_count_label = ttk.Label(metrics_grid, text="0", font=("Arial", 12))
        self.anomaly_count_label.grid(row=0, column=1, sticky="w", padx=(10,20))
        
        # Uptime
        ttk.Label(metrics_grid, text="⏰ Çalışma Süresi:", font=("Arial", 10, "bold")).grid(row=0, column=2, sticky="w")
        self.uptime_label = ttk.Label(metrics_grid, text="00:00:00", font=("Arial", 12))
        self.uptime_label.grid(row=0, column=3, sticky="w", padx=(10,20))
        
        # Total upload (Clickable with sorting)
        ttk.Label(metrics_grid, text="📤 Toplam Upload:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w")
        self.upload_label = tk.Label(metrics_grid, text="0.00 MB (0.0 KB/s avg)", font=("Arial", 12, "bold"), 
                                   fg=self.success_color, bg=self.bg_color, cursor="hand2")
        self.upload_label.grid(row=1, column=1, sticky="w", padx=(10,20))
        self.upload_label.bind("<Button-1>", lambda e: self.show_top_apps('upload'))  # Direct popup
        
        # Total download (Clickable with sorting)
        ttk.Label(metrics_grid, text="📥 Toplam Download:", font=("Arial", 10, "bold")).grid(row=1, column=2, sticky="w")
        self.download_label = tk.Label(metrics_grid, text="0.00 MB (0.0 KB/s avg)", font=("Arial", 12, "bold"),
                                     fg=self.success_color, bg=self.bg_color, cursor="hand2")
        self.download_label.grid(row=1, column=3, sticky="w", padx=(10,20))
        self.download_label.bind("<Button-1>", lambda e: self.show_top_apps('download'))  # Direct popup
        
        # Sort indicator
        ttk.Label(metrics_grid, text="📋 Sıralama:", font=("Arial", 9)).grid(row=2, column=0, sticky="w")
        self.sort_label = ttk.Label(metrics_grid, text="Zaman (Yeni→Eski)", font=("Arial", 9, "italic"))
        self.sort_label.grid(row=2, column=1, sticky="w", padx=(10,20))
        
        # === 2. MAIN CONTENT AREA ===
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # === 3. TOP ROW - TWO TABLES ===
        tables_frame = ttk.Frame(main_frame)
        tables_frame.pack(fill="both", expand=True)
        
        # LEFT TABLE - Current Traffic
        left_table_frame = ttk.LabelFrame(tables_frame, text="🔍 Anlık Ağ Trafiği")
        left_table_frame.pack(side="left", fill="both", expand=True, padx=(0,5))
        
        # Process table
        process_frame = ttk.Frame(left_table_frame)
        process_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Treeview for current processes
        self.process_tree = ttk.Treeview(process_frame, 
                                       columns=("Status", "Upload", "Download", "Connections"), 
                                       show="tree headings", height=12)
        
        # Column headings (Clickable for sorting)
        self.process_tree.heading("#0", text="Uygulama")
        self.process_tree.heading("Status", text="Durum")
        self.process_tree.heading("Upload", text="📤 Upload (KB/s)", command=lambda: self.sort_by_column('upload'))
        self.process_tree.heading("Download", text="📥 Download (KB/s)", command=lambda: self.sort_by_column('download'))
        self.process_tree.heading("Connections", text="🔗 Bağlantı")
        
        # Column widths
        self.process_tree.column("#0", width=150)
        self.process_tree.column("Status", width=150)
        self.process_tree.column("Upload", width=120)
        self.process_tree.column("Download", width=120)
        self.process_tree.column("Connections", width=80)
        
        # Scrollbar for process tree
        process_scroll = ttk.Scrollbar(process_frame, orient="vertical", command=self.process_tree.yview)
        self.process_tree.configure(yscrollcommand=process_scroll.set)
        
        self.process_tree.pack(side="left", fill="both", expand=True)
        process_scroll.pack(side="right", fill="y")
        
        # RIGHT TABLE - Session Totals
        right_table_frame = ttk.LabelFrame(tables_frame, text="📊 Session Toplamları")
        right_table_frame.pack(side="right", fill="both", expand=True, padx=(5,0))
        
        # Session totals table
        session_frame = ttk.Frame(right_table_frame)
        session_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Treeview for session totals
        self.session_tree = ttk.Treeview(session_frame, 
                                       columns=("TotalUp", "TotalDown", "AvgUp", "AvgDown", "Duration"), 
                                       show="tree headings", height=12)
        
        # Column headings
        self.session_tree.heading("#0", text="Uygulama")
        self.session_tree.heading("TotalUp", text="📤 Toplam Upload") 
        self.session_tree.heading("TotalDown", text="📥 Toplam Download") 
        self.session_tree.heading("AvgUp", text="⚡ Ort Upload")
        self.session_tree.heading("AvgDown", text="⚡ Ort Download")
        self.session_tree.heading("Duration", text="⏱️ Süre")
        
        # Column widths
        self.session_tree.column("#0", width=120)
        self.session_tree.column("TotalUp", width=80)
        self.session_tree.column("TotalDown", width=80)
        self.session_tree.column("AvgUp", width=80)
        self.session_tree.column("AvgDown", width=80)
        self.session_tree.column("Duration", width=80)
        
        # Scrollbar for session tree
        session_scroll = ttk.Scrollbar(session_frame, orient="vertical", command=self.session_tree.yview)
        self.session_tree.configure(yscrollcommand=session_scroll.set)
        
        self.session_tree.pack(side="left", fill="both", expand=True)
        session_scroll.pack(side="right", fill="y")
        
        # === 4. BOTTOM ROW - ANOMALY LOG ===
        bottom_frame = ttk.LabelFrame(main_frame, text="🚨 Anomali Günlüğü")
        bottom_frame.pack(side="bottom", fill="x", expand=False, pady=(10,0))
        
        # Anomaly listbox (horizontal now)
        anomaly_frame = ttk.Frame(bottom_frame)
        anomaly_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.anomaly_listbox = tk.Listbox(anomaly_frame, height=6, font=("Consolas", 9),
                                         bg=self.frame_color, fg=self.fg_color, selectbackground=self.accent_color)
        anomaly_scroll = ttk.Scrollbar(anomaly_frame, orient="vertical", command=self.anomaly_listbox.yview)
        self.anomaly_listbox.configure(yscrollcommand=anomaly_scroll.set)
        
        self.anomaly_listbox.pack(side="left", fill="both", expand=True)
        anomaly_scroll.pack(side="right", fill="y")
        
        # === 5. BOTTOM STATUS BAR ===
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Status: Internet trafiği monitör ediliyiyor...", font=("Arial", 10))
        self.status_label.pack(side="left")
        
        # Close button
        close_btn = ttk.Button(status_frame, text="Kapat", command=self.on_closing)
        close_btn.pack(side="right")

    def is_internet_connection(self, ip_address):
        """Check if IP address is a real internet connection (not localhost/private)"""
        if not ip_address:
            return False
        # Filter out localhost and private networks
        if ip_address.startswith('127.'):        # localhost
            return False
        if ip_address.startswith('192.168.'):    # private class C
            return False
        if ip_address.startswith('10.'):         # private class A
            return False
        if ip_address.startswith('172.'):        # private class B (16-31)
            ip_parts = ip_address.split('.')
            if len(ip_parts) >= 2 and 16 <= int(ip_parts[1]) <= 31:
                return False
        if ip_address.startswith('169.254.'):    # link-local
            return False
        if ip_address == '::1' or ip_address.startswith('fe80:'):  # IPv6 localhost/link-local
            return False
        return True

    def get_network_io_stats(self):
        """Get per-process network I/O stats using psutil (Internet-only)"""
        process_stats = {}
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    
                    # Get network connections for this process (INTERNET ONLY)
                    connections = proc.net_connections(kind='inet')
                    internet_connections = []
                    
                    for conn in connections:
                        if (conn.status == psutil.CONN_ESTABLISHED and 
                            conn.raddr and 
                            self.is_internet_connection(conn.raddr.ip)):
                            internet_connections.append(conn)
                    
                    if internet_connections:
                        try:
                            # Get I/O counters
                            io_counters = proc.io_counters()
                            process_stats[pid] = {
                                'name': name,
                                'bytes_sent': io_counters.write_bytes,
                                'bytes_recv': io_counters.read_bytes,
                                'connections': len(internet_connections)
                            }
                        except (psutil.AccessDenied, AttributeError):
                            # Fallback for processes we can't access
                            process_stats[pid] = {
                                'name': name,
                                'bytes_sent': len(internet_connections) * 1024,
                                'bytes_recv': len(internet_connections) * 1024,
                                'connections': len(internet_connections)
                            }
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        return process_stats

    def calculate_bandwidth_usage(self):
        """Calculate per-process bandwidth usage"""
        current_time = time.time()
        current_stats = self.get_network_io_stats()
        
        if not self.last_io_stats:
            self.last_io_stats = current_stats
            self.last_measurement_time = current_time
            return []
        
        time_diff = current_time - getattr(self, 'last_measurement_time', current_time - 2)
        if time_diff < 1:
            return []
        
        process_bandwidth = []
        
        for pid, current in current_stats.items():
            if pid in self.last_io_stats:
                last = self.last_io_stats[pid]
                
                # Calculate bandwidth
                bytes_sent_diff = max(0, current['bytes_sent'] - last['bytes_sent'])
                bytes_recv_diff = max(0, current['bytes_recv'] - last['bytes_recv'])
                
                upload_kbps = (bytes_sent_diff / 1024) / time_diff
                download_kbps = (bytes_recv_diff / 1024) / time_diff
                
                if upload_kbps > 0.1 or download_kbps > 0.1 or current['connections'] > 0:
                    # Anomaly detection (MODEL ONLY - NO CONNECTION THRESHOLD)
                    status = "✅ Normal"
                    is_anom = False
                    
                    if self.model and self.model_columns:
                        proc_name = current['name']
                        app_col = f"process_name_{proc_name}"
                        
                        if app_col in self.model_columns:
                            try:
                                live_row = pd.DataFrame(0, index=[0], columns=self.model_columns)
                                if 'upload_kbps' in live_row.columns:
                                    live_row['upload_kbps'] = upload_kbps
                                if 'download_kbps' in live_row.columns:
                                    live_row['download_kbps'] = download_kbps
                                if app_col in live_row.columns:
                                    live_row[app_col] = 1
                                
                                pred = self.model.predict(live_row)[0]
                                if pred == -1:
                                    status = "🚨 Davranışsal Anomali"
                                    is_anom = True
                            except Exception:
                                status = "⚠️ Model Hatası"
                        else:
                            if proc_name not in self.seen_unknown:
                                status = "🚨🚨 Bilinmeyen Uygulama"
                                is_anom = True
                                self.seen_unknown.add(proc_name)
                            else:
                                status = "⚪ Bilinmeyen"
                    
                    # Update totals and usage history
                    upload_mb = (bytes_sent_diff / (1024 * 1024))
                    download_mb = (bytes_recv_diff / (1024 * 1024))
                    
                    self.total_upload_mb += upload_mb
                    self.total_download_mb += download_mb
                    
                    # Track per-app usage history with speed tracking
                    self.app_usage_history[current['name']]['upload'] += bytes_sent_diff
                    self.app_usage_history[current['name']]['download'] += bytes_recv_diff
                    self.app_usage_history[current['name']]['samples'] += 1
                    self.app_usage_history[current['name']]['total_upload_speed'] += upload_kbps
                    self.app_usage_history[current['name']]['total_download_speed'] += download_kbps
                    
                    # Log anomaly and send notification
                    if is_anom:
                        self.total_anomalies += 1
                        anomaly_time = datetime.now().strftime("%H:%M:%S")
                        self.anomaly_log.append(f"{anomaly_time} - {current['name']} - {status}")
                        
                        # Send notification (max 1 per 30 seconds)
                        current_time = time.time()
                        if current_time - self.last_notification_time > 30:
                            self.show_notification(
                                "🚨 Network Anomaly Detected!",
                                f"{current['name']} - {status}"
                            )
                            self.last_notification_time = current_time
                    
                    process_bandwidth.append({
                        'name': current['name'],
                        'upload_kbps': upload_kbps,
                        'download_kbps': download_kbps,
                        'connections': current['connections'],
                        'status': status,
                        'is_anomaly': is_anom
                    })
        
        # Update state
        self.last_io_stats = current_stats
        self.last_measurement_time = current_time
        
        return process_bandwidth

    def sort_by_column(self, column_type):
        """Sort table by clicked column header"""
        if self.sort_mode == column_type:
            # Toggle between ascending/descending
            self.sort_mode = f"{column_type}_desc"
        elif self.sort_mode == f"{column_type}_desc":
            self.sort_mode = "time"  # Back to time sorting
        else:
            self.sort_mode = column_type
        
        # Update column headers with sort indicators
        self.update_column_headers()
        
        # Refresh display with new sorting
        self.update_display()

    def update_column_headers(self):
        """Update column headers with sort indicators"""
        # Reset headers
        upload_text = "📤 Upload (KB/s)"
        download_text = "📥 Download (KB/s)"
        
        # Add sort indicators
        if self.sort_mode == "upload":
            upload_text += " ⬇️"  # Descending (high to low)
        elif self.sort_mode == "upload_desc":
            upload_text += " ⬆️"  # Ascending (low to high)
        elif self.sort_mode == "download":
            download_text += " ⬇️"
        elif self.sort_mode == "download_desc":
            download_text += " ⬆️"
        
        # Update headers
        self.process_tree.heading("Upload", text=upload_text)
        self.process_tree.heading("Download", text=download_text)
        
        # Update sort label
        sort_labels = {
            'time': "⏰ Zaman Sırası (Yeni→Eski)",
            'upload': "📤 Upload Sırası (Yüksek→Düşük)", 
            'upload_desc': "📤 Upload Sırası (Düşük→Yüksek)",
            'download': "📥 Download Sırası (Yüksek→Düşük)",
            'download_desc': "📥 Download Sırası (Düşük→Yüksek)"
        }
        self.sort_label.config(text=sort_labels.get(self.sort_mode, "⏰ Zaman Sırası"))

    def toggle_sort(self, sort_type):
        """Toggle sorting mode and update display"""
        if self.sort_mode == sort_type:
            # If same mode, toggle between ascending/descending
            self.sort_mode = f"{sort_type}_desc" if not self.sort_mode.endswith('_desc') else sort_type
        else:
            self.sort_mode = sort_type
        
        # Update column headers
        self.update_column_headers()
        
        # Refresh display with new sorting
        self.update_display()

    def show_notification(self, title, message):
        """Show Windows notification"""
        if NOTIFICATIONS_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Network Monitor",
                    timeout=5
                )
            except Exception as e:
                print(f"Notification error: {e}")
    
    def show_top_apps(self, sort_type):
        """Show detailed app statistics popup"""
        if not hasattr(self, 'app_usage_history') or not self.app_usage_history:
            messagebox.showinfo("Bilgi", "Henüz yeterli veri toplanmadı.")
            return
        
        # Create popup window
        popup = tk.Toplevel(self.root)
        popup.title(f"📊 Detaylı {sort_type.upper()} İstatistikleri")
        popup.geometry("700x600")
        popup.configure(bg=self.bg_color)
        popup.transient(self.root)
        popup.grab_set()
        
        # Create frame with scrollbar
        main_frame = tk.Frame(popup, bg=self.bg_color)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_text = "📤 Upload Detayları" if sort_type == 'upload' else "📥 Download Detayları"
        title_label = tk.Label(main_frame, text=title_text, 
                font=("Arial", 16, "bold"), bg=self.bg_color, fg=self.accent_color)
        title_label.pack(pady=(0,20))
        
        # Create scrollable text widget
        text_frame = tk.Frame(main_frame, bg=self.bg_color)
        text_frame.pack(fill="both", expand=True)
        
        text_widget = tk.Text(text_frame, font=("Consolas", 11), bg=self.frame_color, 
                            fg=self.fg_color, wrap=tk.WORD, height=25)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Top 15 apps
        sorted_apps = sorted(self.app_usage_history.items(), 
                           key=lambda x: x[1][sort_type], reverse=True)[:15]
        
        text_widget.insert(tk.END, f"🏆 TOP 15 - En Çok {sort_type.upper()} Kullanan:\\n\\n")
        
        for i, (app_name, usage) in enumerate(sorted_apps, 1):
            value_mb = usage[sort_type] / (1024*1024)  # Convert to MB
            avg_speed = usage[f'total_{sort_type}_speed'] / max(usage['samples'], 1)  # Average KB/s
            duration = time.time() - usage['first_seen']
            duration_min = duration / 60
            
            if value_mb > 0.01:  # Only show if > 0.01 MB
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:2d}."
                text_widget.insert(tk.END, 
                    f"{emoji} {app_name:<25}\\n"
                    f"   📊 Toplam: {value_mb:>8.2f} MB\\n"
                    f"   ⚡ Ortalama: {avg_speed:>6.1f} KB/s\\n"
                    f"   ⏱️ Süre: {duration_min:>6.1f} dakika\\n"
                    f"   📈 Örnek: {usage['samples']:>4d} ölçüm\\n\\n")
        
        # Summary statistics
        text_widget.insert(tk.END, "\\n" + "─" * 50 + "\\n\\n")
        text_widget.insert(tk.END, "📊 GENEL İSTATİSTİKLER:\\n\\n")
        
        total_value = sum(app[sort_type] for app in self.app_usage_history.values()) / (1024*1024)
        total_apps = len([app for app in self.app_usage_history.values() if app[sort_type] > 0])
        session_duration = (time.time() - self.start_time) / 60
        
        text_widget.insert(tk.END, 
            f"🎯 Toplam {sort_type}: {total_value:.2f} MB\\n"
            f"🔢 Aktif uygulama: {total_apps}\\n"
            f"⏰ Session süresi: {session_duration:.1f} dakika\\n"
            f"📊 Ortalama hız: {total_value*1024/max(session_duration, 1):.1f} KB/dakika\\n")
        
        text_widget.config(state=tk.DISABLED)  # Make read-only
        
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Close button
        close_btn = tk.Button(main_frame, text="Kapat", command=popup.destroy,
                             bg=self.frame_color, fg=self.fg_color, font=("Arial", 12, "bold"),
                             padx=20, pady=5)
        close_btn.pack(pady=(20, 0))

    def update_display(self):
        """Update the GUI with current data"""
        # === CLEAR EXISTING DATA ===
        for item in self.process_tree.get_children():
            self.process_tree.delete(item)
        for item in self.session_tree.get_children():
            self.session_tree.delete(item)
        
        # === GET NEW DATA ===
        process_data = self.calculate_bandwidth_usage()
        self.current_process_data = process_data
        
        # === APPLY SORTING ===
        if self.sort_mode.startswith('upload'):
            process_data.sort(key=lambda x: x['upload_kbps'], 
                            reverse=not self.sort_mode.endswith('_desc'))
        elif self.sort_mode.startswith('download'):
            process_data.sort(key=lambda x: x['download_kbps'], 
                            reverse=not self.sort_mode.endswith('_desc'))
        # Default is time order (newest first)
        
        # Update column headers with current sort
        self.update_column_headers()
        
        # === UPDATE CURRENT TRAFFIC TABLE ===
        for process in process_data:
            status = process['status']
            
            # Color coding for status
            if "Anomali" in status or "Bilinmeyen" in status:
                tags = ('anomaly',)
            else:
                tags = ('normal',)
            
            self.process_tree.insert("", "end", 
                text=process['name'], 
                values=(
                    status,
                    f"{process['upload_kbps']:.1f}",
                    f"{process['download_kbps']:.1f}",
                    f"{process['connections']}"
                ),
                tags=tags
            )
        
        # Configure tags for colors
        self.process_tree.tag_configure('anomaly', foreground=self.error_color)
        self.process_tree.tag_configure('normal', foreground=self.success_color)
        
        # === UPDATE SESSION TOTALS TABLE ===
        session_data = []
        for app_name, usage in self.app_usage_history.items():
            if usage['upload'] > 0 or usage['download'] > 0:
                duration = time.time() - usage['first_seen']
                avg_upload = usage['total_upload_speed'] / max(usage['samples'], 1)
                avg_download = usage['total_download_speed'] / max(usage['samples'], 1)
                
                session_data.append({
                    'name': app_name,
                    'total_upload': usage['upload'] / (1024*1024),  # MB
                    'total_download': usage['download'] / (1024*1024),  # MB
                    'avg_upload': avg_upload,
                    'avg_download': avg_download,
                    'duration': duration / 60  # minutes
                })
        
        # Sort session data by total usage
        session_data.sort(key=lambda x: x['total_upload'] + x['total_download'], reverse=True)
        
        # Add to session tree (top 20)
        for session in session_data[:20]:
            self.session_tree.insert("", "end",
                text=session['name'],
                values=(
                    f"{session['total_upload']:.1f} MB",
                    f"{session['total_download']:.1f} MB", 
                    f"{session['avg_upload']:.1f} KB/s",
                    f"{session['avg_download']:.1f} KB/s",
                    f"{session['duration']:.1f}m"
                )
            )
        
        # === UPDATE ANOMALY LOG ===
        # Clear listbox
        self.anomaly_listbox.delete(0, tk.END)
        
        # Add recent anomalies (last 50)
        recent_anomalies = self.anomaly_log[-50:]
        for anomaly in recent_anomalies:
            self.anomaly_listbox.insert(tk.END, anomaly)
        
        if self.anomaly_log:
            self.anomaly_listbox.see(tk.END)  # Auto scroll to bottom
        
        # === UPDATE METRICS WITH AVERAGES ===
        session_duration = time.time() - self.start_time
        avg_upload_speed = (self.total_upload_mb * 1024) / max(session_duration, 1)  # KB/s
        avg_download_speed = (self.total_download_mb * 1024) / max(session_duration, 1)  # KB/s
        
        self.anomaly_count_label.config(text=str(self.total_anomalies))
        self.upload_label.config(text=f"{self.total_upload_mb:.2f} MB ({avg_upload_speed:.1f} KB/s avg)")
        self.download_label.config(text=f"{self.total_download_mb:.2f} MB ({avg_download_speed:.1f} KB/s avg)")
        
        # Update uptime
        uptime = int(session_duration)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.uptime_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Update status
        active_processes = len([p for p in process_data if p['upload_kbps'] > 0.1 or p['download_kbps'] > 0.1])
        total_apps = len(session_data)
        self.status_label.config(
            text=f"📊 Anlık: {active_processes} aktif | Session: {total_apps} uygulama | {len(self.anomaly_log)} anomali"
        )

    def monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                # Thread-safe GUI update
                self.root.after(0, self.update_display)
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Monitoring error: {e}")
                break

    def start_monitoring_thread(self):
        """Start monitoring in background thread"""
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()

    def on_closing(self):
        """Handle application closing"""
        self.monitoring = False
        self.root.destroy()

# Main execution
if __name__ == "__main__":
    # Install plyer if needed
    try:
        from plyer import notification
    except ImportError:
        print("🚨 Bilgilendirme: Windows notification özelliği için 'plyer' kütüphanesini yükleyin:")
        print("pip install plyer")
    
    root = tk.Tk()
    app = NetworkMonitorDashboard(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()