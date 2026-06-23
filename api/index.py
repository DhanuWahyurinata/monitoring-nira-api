import os
import joblib
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ========================================================
# KONFIGURASI BLYNK & TELEGRAM
# ========================================================
# Ganti dengan token asli milik Anda
BLYNK_AUTH_TOKEN = "iQzz4E6ABVj5obYjRrIwz4wlWkmHGjfd"
TELEGRAM_BOT_TOKEN = "8875092454:AAFXOGlTXULXecrgOAPaKCaNVhJ3E-HXmZk"
TELEGRAM_CHAT_ID = "8178380257"

# ========================================================
# LOAD MODEL ANFIS
# ========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, 'model_anfis.pkl')
model = joblib.load(model_path)

# ========================================================
# GLOBAL STATE VARIABLE
# ========================================================
data_dashboard = {"nira": 0.0, "waktu": "Stagnan", "baterai": 0.0, "rssi": 0}
# Variabel pembantu untuk melacak batas alert terakhir agar tidak spam Telegram
status_alert_terakhir = 0

# ========================================================
# DESAIN WEBSITE (TAILWIND CSS)
# ========================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Monitoring Nira</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script>setInterval(function(){ window.location.reload(); }, 10000);</script>
</head>
<body class="bg-slate-100 min-h-screen flex items-center justify-center p-4 font-sans">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-3xl overflow-hidden border border-gray-100">
        
        <div class="bg-blue-600 text-white p-6 flex justify-between items-center">
            <div>
                <h1 class="text-2xl font-bold tracking-wide">Dashboard Nira</h1>
                <p class="text-blue-200 text-sm mt-1">Sistem Pemantauan Otomatis (ANFIS)</p>
            </div>
            <div class="flex items-center gap-2 bg-blue-700 px-4 py-1.5 rounded-full text-sm font-medium shadow-inner">
                <span class="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse"></span>
                Sistem Aktif
            </div>
        </div>

        <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <div class="bg-white rounded-xl p-5 border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-gray-600 font-semibold"><i class="fa-solid fa-flask text-blue-500 mr-2"></i>Volume Nira</h2>
                    <span class="text-3xl font-bold text-gray-800">{{ data.nira }}<span class="text-lg text-gray-500">%</span></span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-4 overflow-hidden relative shadow-inner">
                    <div class="bg-gradient-to-r from-blue-400 to-blue-600 h-4 rounded-full transition-all duration-500 ease-out" style="width: {{ data.nira }}%;"></div>
                </div>
            </div>

            <div class="bg-white rounded-xl p-5 border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex items-center justify-between">
                <div>
                    <h2 class="text-gray-600 font-semibold mb-1"><i class="fa-solid fa-clock text-orange-500 mr-2"></i>Sisa Waktu</h2>
                    <p class="text-xs text-gray-400">Estimasi hingga penuh</p>
                </div>
                <div class="text-right">
                    <span class="text-3xl font-bold text-gray-800">{{ data.waktu }}</span>
                    <span class="text-gray-500 text-sm font-medium"> Menit</span>
                </div>
            </div>

            <div class="bg-white rounded-xl p-5 border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex items-center justify-between">
                <div>
                    <h2 class="text-gray-600 font-semibold mb-1"><i class="fa-solid fa-battery-three-quarters text-green-500 mr-2"></i>Baterai</h2>
                    <p class="text-xs text-gray-400">Daya perangkat IoT</p>
                </div>
                <div class="text-right">
                    <span class="text-2xl font-bold text-gray-800">{{ data.baterai }}%</span>
                </div>
            </div>

            <div class="bg-white rounded-xl p-5 border border-gray-200 shadow-sm hover:shadow-md transition-shadow flex items-center justify-between">
                <div>
                    <h2 class="text-gray-600 font-semibold mb-1"><i class="fa-solid fa-wifi text-purple-500 mr-2"></i>Sinyal (RSSI)</h2>
                    <p class="text-xs text-gray-400">Kekuatan koneksi</p>
                </div>
                <div class="text-right">
                    <span class="text-2xl font-bold text-gray-800">{{ data.rssi }}</span>
                    <span class="text-gray-500 text-sm font-medium"> dBm</span>
                </div>
            </div>

        </div>
        
        <div class="bg-gray-50 p-4 text-center text-xs text-gray-400 border-t border-gray-200">
            Halaman ini memuat ulang secara otomatis setiap 10 detik.
        </div>
    </div>
</body>
</html>
"""

# ========================================================
# FUNGSI-FUNGSI PENDUKUNG
# ========================================================
def update_blynk(pin, value):
    url = f"https://sgp1.blynk.cloud/external/api/update?token={BLYNK_AUTH_TOKEN}&{pin.upper()}={value}"
    try:
        requests.get(url, timeout=5)
    except: 
        pass

def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": TELEGRAM_CHAT_ID, "text": pesan, "parse_mode": "Markdown"}, timeout=5)
    except:
        pass

# ========================================================
# ROUTING FLASK
# ========================================================
@app.route("/api/nira", methods=["POST"])
def terima_data():
    global data_dashboard, status_alert_terakhir
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Tidak ada data JSON"}), 400

        nira = float(data.get("nira_persen", 0))
        rssi = int(data.get("rssi", 0))
        
        # 1. ANFIS INFERENCE
        model.input['Volume Nira (%)'] = nira
        model.input['Kecepatan (%/menit)'] = 0.5 # Default rate kecepatan pengisian
        model.compute()
        estimasi_menit = round(model.output['Sisa Waktu (Menit)'], 1)
        
        # 2. Kalkulasi Baterai (Sederhana)
        baterai = 100.0 
        
        # 3. Update Global Data untuk Dashboard Web
        data_dashboard = {"nira": nira, "waktu": str(estimasi_menit), "baterai": baterai, "rssi": rssi}
        
        # 4. KIRIM KE BLYNK (V1=Nira, V2=Status/Waktu, V3=SisaWaktu, V4=Baterai)
        update_blynk("V1", nira)
        update_blynk("V2", "Running")
        update_blynk("V3", estimasi_menit) 
        update_blynk("V4", baterai)

        # 5. LOGIKA TELEGRAM ALERT (BERTINGKAT + ESTIMASI WAKTU)
        # Jika wadah nira dikosongkan/dipanen (turun di bawah 10%), reset status pelacak alert
        if nira < 10.0:
            status_alert_terakhir = 0
            
        # Membuat template pesan sisa waktu dari ANFIS
        pesan_estimasi = f"\n⏳ *Estimasi sisa waktu:* {estimasi_menit} menit lagi sebelum penuh."

        # Pengecekan kondisi dari persentase tertinggi ke terendah
        if nira >= 95.0 and status_alert_terakhir < 95:
            kirim_telegram(f"🚨 *NIRA SIAP PANEN!* \n📊 Volume saat ini: {nira}%\nSilakan segera lakukan proses pemanenan.")
            status_alert_terakhir = 95
            
        elif nira >= 75.0 and status_alert_terakhir < 75:
            kirim_telegram(f"⚠️ *Notifikasi Pengisian:* \n📊 Volume nira sudah mencapai {nira}%." + pesan_estimasi)
            status_alert_terakhir = 75
            
        elif nira >= 50.0 and status_alert_terakhir < 50:
            kirim_telegram(f"ℹ️ *Notifikasi Pengisian:* \n📊 Volume nira sudah mencapai {nira}%." + pesan_estimasi)
            status_alert_terakhir = 50
            
        elif nira >= 25.0 and status_alert_terakhir < 25:
            kirim_telegram(f"ℹ️ *Notifikasi Pengisian:* \n📊 Volume nira sudah mencapai {nira}%." + pesan_estimasi)
            status_alert_terakhir = 25
        
        return jsonify({"status": "success", "estimasi": estimasi_menit})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def home():
    # Merender template HTML yang sudah dibuat dan memasukkan data_dashboard
    return render_template_string(HTML_TEMPLATE, data=data_dashboard)

def handler(environ, start_response):
    return app(environ, start_response)

if __name__ == "__main__":
    # Menjalankan aplikasi secara lokal untuk keperluan testing
    app.run(host="0.0.0.0", port=5000, debug=True)
