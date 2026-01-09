import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # لضمان قبول الاتصالات من أي مكان

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

@app.route('/')
def home():
    return "سيرفر الجيش يعمل!", 200

@app.route('/test', methods=['POST'])
def test():
    try:
        data = request.json
        msg = data.get('message', 'تجربة ناجحة!')
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": CHAT_ID,
            "text": f"🚀 رسالة فحص من الموقع:\n{msg}"
        })
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
