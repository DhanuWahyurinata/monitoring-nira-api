import time
from flask import Flask, jsonify, render_template_string, request
import requests

app = Flask(__name__)

# ========================================================
# KREDENSIAL
# ========================================================
BLYNK_AUTH_TOKEN = "iQzz4E6ABVj5obYjRrIwz4wlWkmHGjfd"
TELEGRAM_BOT_TOKEN = "8875092454:AAFXOGlTXULXecrgOAPaKCaNVhJ3E-HXmZk"
TELEGRAM_CHAT_ID = "8178380257"

# ========================================================
# FUNGSI KIRIM TELEGRAM (Aman Lewat Vercel)
# ========================================================


def kirim_telegram(pesan):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": pesan,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegram Error: {e}")


# ========================================================
# FUNGSI UPDATE BLYNK (Lancar Tanpa Blokir Proxy di Vercel)
# ========================================================


def update_blynk(pin, value):
    # Menggunakan HTTPS resmi Blynk Cloud server regional Asia
    url = "https://sgp1.blynk.cloud/external/api/update"
    params = {"token": BLYNK_AUTH_TOKEN, pin.upper(): str(value)}
    try:
        requests.get(url, params=params, timeout=5)
    except Exception as e:
        print(f"Blynk Error: {e}")


# ========================================================
# TEMPLATE HTML DASHBOARD
# ========================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Monitoring Nira Enau</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; text-align: center; background: #f4f6f9; padding: 20px; color: #333; margin: 0; }
        .card { background: white; margin: 15px auto; padding: 25px; max-width: 400px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: left; }
        h1 { color: #d81b60; margin-top: 30px; }
        .value { font-size: 36px; font-weight: bold; color: #d81b60; margin: 5px 0; }
        .status-text { font-weight: 600; color: #2e7d32; }
    </style>
</head>
<body>
    <h1>Dashboard Monitoring Nira</h1>
    <div class="card">
        <h3>Volume Nira</h3>
        <div class="value">{{ nira }}%</div>
        <p>Status: <span class="status-text">{{ status }}</span></p>
    </div>
    <div class="card">
        <h3>Informasi Sistem</h3>
        <p>🔋 Baterai Node: <strong>{{ baterai }}%</strong></p>
        <p>📡 Sinyal RSSI: <strong>{{ rssi }} dBm</strong></p>
    </div>
</body>
</html>
"""

# Variabel fallback statis jika diakses via GET browser luar
data_dummy = {"nira": 0.0, "baterai": 0.0, "rssi": 0, "status": "Online"}


@app.route("/")
def home():
    return render_template_string(HTML_PAGE, **data_dummy)


# ========================================================
# API RECEIVE DATA FROM ESP32 GATEWAY
# ========================================================


@app.route("/api/nira", methods=["POST"])
def terima_data():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "Payload JSON kosong!"}), 400

        nira_persen = float(data.get("nira_persen", 0.0))
        uptime_jam = float(data.get("uptime_jam", 0.0))
        rssi = int(data.get("rssi", 0))

        # 1. Simulasi Kapasitas Baterai
        kapasitas_awal_mah = 12580.0
        konsumsi_arus_ma = 70.0
        sisa_baterai_persen = min(
            (
                max(kapasitas_awal_mah - (uptime_jam * konsumsi_arus_ma), 0)
                / kapasitas_awal_mah
            )
            * 100,
            100.0,
        )

        # 2. Klasifikasi Status & Teks Estimasi
        status = "Kondisi Aman"
        teks_waktu = "Sedang Terisi"
        if nira_persen >= 80.0:
            status = "Bersiap Panen!"
            teks_waktu = "Hampir Penuh"
        elif nira_persen >= 50.0:
            status = "Mulai Terisi"

        if nira_persen >= 100.0:
            teks_waktu = "Penuh!"

        # Update data dummy untuk tampilan sementara web
        global data_dummy
        data_dummy = {
            "nira": round(nira_persen, 1),
            "baterai": round(sisa_baterai_persen, 1),
            "rssi": rssi,
            "status": status,
        }

        # 3. Kirim ke Blynk via HTTPS (Aman Jaya di Vercel!)
        update_blynk("V1", round(nira_persen, 1))
        update_blynk("V2", teks_waktu)
        update_blynk("V3", rssi)
        update_blynk("V4", round(sisa_baterai_persen, 1))

        # 4. Notifikasi Telegram Instan
        if 50.0 <= nira_persen < 53.0:
            kirim_telegram(f"💧 *Volume Nira mencapai 50%* \nStatus: {status}")
        elif 80.0 <= nira_persen < 83.0:
            kirim_telegram(
                f"⚠️ *Volume Nira mencapai 80%* \nStatus: {status} (Siap-siap ke pohon)"
            )
        elif nira_persen >= 100.0:
            kirim_telegram(
                "🚨 *PERINGATAN: NIRA PENUH 100%!* 🚨\nSegera amankan wadah penampung!"
            )

        return jsonify({"status": "success", "blynk_updated": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Blok run ini wajib dipertahankan untuk kebutuhan routing Vercel serverless
if __name__ == "__main__":
    app.run(debug=True)