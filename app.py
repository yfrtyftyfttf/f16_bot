import os, requests, json
from flask import Flask, request
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# --- إعداد Firebase ---
try:
    fb_config = os.environ.get('FIREBASE_CONFIG_JSON')
    if fb_config:
        cred_dict = json.loads(fb_config)
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Connected to Firebase")
except Exception as e:
    print(f"❌ Firebase Setup Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
# ملاحظة: تأكد أن هذا هو معرفك الصحيح في تلجرام
ADMIN_ID = "6695916631"

admin_state = {}

def send_telegram(chat_id, text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    return requests.post(url, json=payload)

@app.route('/')
def home(): return "Bot is Online", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "empty", 200

    if "message" in update:
        msg = update["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "")

        # مؤقتاً: سنرد على أي شخص للتأكد من عمل البوت
        if text == "/start":
            send_telegram(chat_id, f"👋 أهلاً بك! معرفك (Chat ID) هو: `{chat_id}`\nأرسل لي ID المستخدم للبحث عنه.")
            return "ok", 200

        # معالجة البحث عن مستخدم
        if len(text) > 15:
            try:
                user_doc = db.collection("users").doc(text).get()
                if user_doc.exists:
                    data = user_doc.to_dict()
                    name = data.get('name', 'غير معروف')
                    balance = data.get('balance', 0.0)
                    
                    resp_text = f"👤 *بيانات المستخدم:*\n\n"
                    resp_text += f"🔹 الاسم: {name}\n"
                    resp_text += f"💰 الرصيد: {balance}$\n"
                    resp_text += f"🆔 الـ ID: `{text}`"
                    
                    markup = {
                        "inline_keyboard": [
                            [{"text": "➕ شحن", "callback_data": f"ask:charge:{text}"}],
                            [{"text": "➖ خصم", "callback_data": f"ask:deduct:{text}"}]
                        ]
                    }
                    send_telegram(chat_id, resp_text, markup)
                else:
                    send_telegram(chat_id, "❌ هذا الـ ID غير موجود في Firestore.")
            except Exception as e:
                send_telegram(chat_id, f"❌ خطأ في Firebase: {str(e)}")

    # معالجة الأزرار
    if "callback_query" in update:
        query = update["callback_query"]
        cb_data = query["data"].split(":")
        chat_id = str(query["message"]["chat"]["id"])
        
        if cb_data[0] == "ask":
            admin_state[chat_id] = {"action": cb_data[1], "uid": cb_data[2]}
            send_telegram(chat_id, f"✍️ أرسل المبلغ الآن لتنفيذ عملية الـ {cb_data[1]}:")
            
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
