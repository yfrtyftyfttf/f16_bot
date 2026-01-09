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
        print("✅ Firebase Connected")
except Exception as e:
    print(f"❌ Firebase Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
ADMIN_ID = "6695916631"

def send_telegram(chat_id, text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update or "message" not in update: return "ok", 200

    chat_id = str(update["message"]["chat"]["id"])
    text = update["message"].get("text", "").strip()

    if chat_id == ADMIN_ID:
        # إذا أرسلت ID طويل (البحث عن مستخدم)
        if len(text) > 10:
            try:
                # محاولة البحث في مجموعة "users"
                user_ref = db.collection("users").doc(text).get()
                
                if user_ref.exists:
                    data = user_ref.to_dict()
                    name = data.get('name', 'بدون اسم')
                    balance = data.get('balance', 0)
                    
                    msg = f"👤 *تم العثور على العميل:*\n\n"
                    msg += f"🔹 الاسم: {name}\n"
                    msg += f"💰 الرصيد: {balance}$\n"
                    msg += f"🆔 الـ ID: `{text}`"
                    
                    markup = {
                        "inline_keyboard": [
                            [{"text": "➕ شحن", "callback_data": f"op:charge:{text}"}],
                            [{"text": "➖ خصم", "callback_data": f"op:deduct:{text}"}]
                        ]
                    }
                    send_telegram(chat_id, msg, markup)
                else:
                    # إذا لم يجد الـ ID، سنحاول البحث في مجموعة "Users" (حرف كبير) احتياطاً
                    send_telegram(chat_id, f"❌ الـ ID `{text}` غير موجود في مجموعة (users).\nتأكد من اسم المجموعة في Firebase.")
            
            except Exception as e:
                send_telegram(chat_id, f"⚠️ خطأ تقني في Firebase:\n`{str(e)}`")
    
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
