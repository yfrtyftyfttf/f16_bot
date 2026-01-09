import os, requests, json
from flask import Flask, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# إعداد Firebase
try:
    fb_config = os.environ.get('FIREBASE_CONFIG_JSON')
    if fb_config:
        cred_dict = json.loads(fb_config)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase Connected")
except Exception as e:
    print(f"❌ Firebase Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"

@app.route('/')
def home(): return "Bot is Alive", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "ok", 200

    # بمجرد وصول أي رسالة، سيحاول البوت الرد فوراً
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "")
        
        # رسالة اختبار بسيطة
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": chat_id,
            "text": f"✅ استلمت رسالتك: {text}\nسأقوم الآن بالبحث عن الـ ID إذا أرسلته."
        })

        # البحث في Firebase إذا كان النص عبارة عن ID
        if len(text) > 15:
            try:
                user_doc = db.collection("users").doc(text).get()
                if user_doc.exists:
                    u_data = user_doc.to_dict()
                    msg = f"👤 مستخدم: {u_data.get('name')}\n💰 رصيد: {u_data.get('balance')}$\nأرسل المبلغ لشحنه."
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id, "text": msg
                    })
                else:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": chat_id, "text": "❌ الـ ID غير موجود في القاعدة."
                    })
            except Exception as e:
                print(f"Error: {e}")

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
