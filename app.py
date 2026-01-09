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
except Exception as e:
    print(f"Firebase Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update or "message" not in update: return "ok", 200

    chat_id = update["message"]["chat"]["id"]
    text = update["message"].get("text", "").strip()

    if len(text) > 5:  # إذا أرسلت الـ ID
        try:
            # تنبيه لبدء البحث
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": "🔍 جاري الفحص في قاعدة البيانات..."})

            # البحث في مجموعة users (تأكد من الاسم هنا)
            user_ref = db.collection("users").doc(text).get()

            if user_ref.exists:
                data = user_ref.to_dict()
                bal = data.get('balance', 0)
                
                msg = f"✅ تم العثور على الحساب!\n\n💰 الرصيد الحالي: {bal}$\n🆔 ID: `{text}`"
                markup = {
                    "inline_keyboard": [
                        [{"text": "➕ شحن رصيد", "callback_data": f"op:charge:{text}"}],
                        [{"text": "➖ خصم رصيد", "callback_data": f"op:deduct:{text}"}]
                    ]
                }
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                              json={"chat_id": chat_id, "text": msg, "reply_markup": markup})
            else:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                              json={"chat_id": chat_id, "text": f"❌ لم أجد مستخدم بهذا الـ ID في مجموعة 'users'.\nتأكد أنك أنشأت الـ Document بالاسم الصحيح."})
        
        except Exception as e:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": chat_id, "text": f"⚠️ خطأ تقني: {str(e)}"})

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
