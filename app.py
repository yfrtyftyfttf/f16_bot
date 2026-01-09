import os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # السماح لجميع النطاقات بالوصول

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

@app.route('/')
def home(): return "Server is Running", 200

@app.route('/send_order', methods=['POST', 'OPTIONS'])
def send_order():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
    try:
        data = request.get_json(force=True) # قراءة البيانات حتى لو كانت مشفرة
        u_name = data.get('user_name', 'عميل')
        details = data.get('details', {})
        
        msg = f"🚀 طلب جديد\n👤 العميل: {u_name}\n"
        for k, v in details.items():
            msg += f"🔹 {k}: {v}\n"

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": CHAT_ID, "text": msg
        })
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
