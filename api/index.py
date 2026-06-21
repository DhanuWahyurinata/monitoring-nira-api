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
# FUNGSI AMBIL DATA DARI BLYNK
# ========================================================


def ambil_data_dari_blynk():
    data = {"nira": 0.0, "waktu_teks": "Stagnan", "rssi": 0, "baterai": 0.0}
    url = "https://sgp1.blynk.cloud/external/api/get"
    params = {
        "token": BLYNK_AUTH_TOKEN,
        "V1": "",
        "V2": "",
        "V3": "",
        "V4": "",
    }
    try:
        response = requests.get(url, params=params, timeout=4)
        if response.status_code == 200:
            res_json = response.json()
            data["nira"] = float(res_json.get("V1", 0.0))
            data["waktu_teks"] = str(res_json.get("V2", "Stagnan"))
            data["rssi"] = int(res_json.get("V3", 0))
            data["baterai"] = float(res_json.get("V4", 0.0))
    except Exception as e:
        print(f"Gagal ambil data Blynk: {e}")
    return data


# ========================================================
# FUNGSI KIRIM TELEGRAM
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
# FUNGSI UPDATE DATA KE BLYNK
# ========================================================


def update_blynk(pin, value):
    url = "https://sgp1.blynk.cloud/external/api/update"
    params = {"token": BLYNK_AUTH_TOKEN, pin.upper(): str(value)}
    try:
        requests.get(url, params=params, timeout=5)
    except Exception as e:
        print(f"Blynk Update Error: {e}")


# ========================================================
# TEMPLATE HTML DASHBOARD WEB
# ========================================================
HTML_PAGE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>Monitoring Nira Enau</title>
    <meta http-equiv="refresh" content="10">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; text-align: center; background: #f4f6f9; padding: 20px; color: #333; margin: 0; }
        .header { margin: 30px auto; }
        .header h1 { color: #d81b60; margin: 0; font-size: 28px; }
        .header p { color: #777; margin: 5px 0 0 0; }
        .card { background: white; margin: 15px auto; padding: 25px; max-width: 400px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); text-align: left; }
        .card h3 { margin: 0 0 10px 0; color: #555; font-size: 16px; text-transform: uppercase; }
        .value { font-size: 36px; font-weight: bold; color: #d81b60; margin: 5px 0; }
        .status-text { font-weight: 600; color: #2e7d32; }
        .system-info { display: flex; justify-content: space-between; margin-top: 10px; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Dashboard Monitoring Nira</h1>
        <p>Data tersinkronisasi langsung dengan Blynk Cloud</p>
    </div>

    <div class="card">
        <h3>Volume Nira</h3>
        <div class="value">{{ data.nira }}%</div>
        <p>Status: <span class="status-text">
            {% if data.nira >= 80.0 %} Bersiap Panen! {% elif data.nira >= 50.0 %} Mulai Terisi {% else %} Kondisi Aman {% endif %}
        </span></p>
    </div>

    <div class="card">
        <h3>Estimasi Waktu Panen</h3>
        <div class="value" style="color: #1565c0;">{{ data.waktu_teks }}</div>
    </div>

    <div class="card">
        <h3>Informasi Perangkat</h3>
        <div class="system-info">
            <span>🔋 Baterai Node: <strong>{{ data.baterai }}%</strong></span>
            <span>📡 Sinyal RSSI: <strong>{{ data.rssi }} dBm</strong></span>
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    live_data = ambil_data_dari_blynk()
    return render_template_string(HTML_PAGE, data=live_data)


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

        # --------------------------------------------------------
        # BYPASS SERVERLESS: Ambil data sebelumnya dari Blynk
        # --------------------------------------------------------
        data_lama = ambil_data_dari_blynk()
        nira_lalu = data_lama["nira"]

        # Kita asumsikan interval pengiriman ESP32 konstan (misal tiap 1 menit)
        # Jika ada kenaikan nira dari data sebelumnya, hitung kecepatannya
        teks_waktu = "Stagnan"
        selisih_nira = nira_persen - nira_lalu

        if selisih_nira > 0 and nira_persen < 100.0:
            # Estimasi pengisian per interval data masuk
            sisa_kapasitas = 100.0 - nira_persen

            # Rumus perkiraan waktu (skala pengisian nira)
            # Menggunakan rasio pengisian berbasis sisa kapasitas wadah
            faktor_kecepatan = selisih_nira if selisih_nira > 0 else 0.1
            total_menit_sisa = (sisa_kapasitas / faktor_kecepatan) * 1.0

            jam = int(total_menit_sisa / 60)
            menit = int(total_menit_sisa % 60)

            if jam > 0:
                teks_waktu = f"{jam} Jam {menit} Menit"
            else:
                teks_waktu = f"{menit} Menit"
        elif nira_persen >= 100.0:
            teks_waktu = "PFull / Penuh!"
        elif nira_persen > 0 and selisih_nira == 0:
            # Jika nira ada isinya tapi nilainya stabil/belum naik lagi dari data menit lalu
            teks_waktu = data_lama["waktu_teks"] if data_lama["waktu_teks"] != "PFull / Penuh!" else "Sedang Terisi"

        # --------------------------------------------------------
        # Kalkulasi Kapasitas Baterai
        # --------------------------------------------------------
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

        status = (
            "Bersiap Panen!"
            if nira_persen >= 80.0
            else "Mulai Terisi" if nira_persen >= 50.0 else "Kondisi Aman"
        )

        # 3. Kirim Pembaruan ke Blynk Cloud
        update_blynk("V1", round(nira_persen, 1))
        update_blynk("V2", teks_waktu)
        update_blynk("V3", rssi)
        update_blynk("V4", round(sisa_baterai_persen, 1))

        # 4. Notifikasi Telegram Instan
        if 50.0 <= nira_persen < 53.0:
            kirim_telegram(
                f"💧 *Volume Nira mencapai 50%* \n⏱️ Estimasi Penuh: `{teks_waktu}`"
            )
        elif 80.0 <= nira_persen < 83.0:
            kirim_telegram(
                f"⚠️ *Volume Nira mencapai 80% (Siap Panen!)* \n⏱️ Estimasi Penuh: `{teks_waktu}`"
            )
        elif nira_persen >= 100.0:
            kirim_telegram(
                "🚨 *PERINGATAN: NIRA PENUH 100%!* 🚨\nSegera amankan wadah penampung!"
            )

        return jsonify({"status": "success", "estimasi": teks_waktu})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
