from flask import Flask, request, jsonify
import joblib
import pandas as pd
from datetime import datetime

app = Flask(__name__)

# Load model ANFIS yang sudah kamu buat
model = joblib.load('model_anfis.pkl')

# Simulasi Database sederhana di memori (biar bisa dilihat datanya)
data_log = []

@app.route('/api/nira', methods=['POST'])
def handle_nira():
    payload = request.json
    nira = payload['nira_persen']
    
    # LOGIKA DETEKSI PANEN
    status = "Mengisi"
    if len(data_log) > 0:
        last_nira = data_log[-1]['nira']
        # Kalau sebelumnya >= 90% terus tiba-tiba jadi < 15%, artinya habis dipanen!
        if last_nira >= 90 and nira <= 15:
            status = "Baru Saja Dipanen"
    
    # SIMPAN DATA KE LOG
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nira": nira,
        "status": status
    }
    data_log.append(entry)
    
    # Simpan hanya 50 data terakhir biar server gak berat
    if len(data_log) > 50: data_log.pop(0)
    
    return jsonify({"status": "Data Diterima", "kondisi": status}), 200

@app.route('/api/data', methods=['GET'])
def get_data():
    # Ini endpoint buat kamu lihat isi data di web/browser
    return jsonify(data_log)

if __name__ == '__main__':
    app.run()
