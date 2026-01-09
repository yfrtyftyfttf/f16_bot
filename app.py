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

def send_telegram(chat_id, text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    return requests.post(url, json=payload)

@app.route('/')
def home(): return "Bot is Active", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "ok", 200

    # 1. البحث عن الـ ID
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        if len(text) > 5:
            user_ref = db.collection("users").doc(text).get()
            if user_ref.exists:
                bal = user_ref.to_dict().get('balance', 0)
                # استخدام فاصل فريد (::) لضمان عدم التداخل مع الـ ID
                markup = {
                    "inline_keyboard": [
                        [{"text": "✅ قبول وشحن 10$", "callback_data": f"acc::10::{text}"}],
                        [{"text": "❌ رفض الطلب", "callback_data": f"rej::0::{text}"}]
                    ]
                }
                send_telegram(chat_id, f"👤 *بيانات الحساب:*\n💰 الرصيد: {bal}$\n🆔 ID: `{text}`", markup)
            else:
                send_telegram(chat_id, "❌ الـ ID غير موجود.")

    # 2. معالجة الأزرار
    if "callback_query" in update:
        query = update["callback_query"]
        q_id = query["id"]
        chat_id = query["message"]["chat"]["id"]
        
        # إيقاف التحميل فوراً
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                      json={"callback_query_id": q_id, "text": "يتم الآن التحديث..."})

        # تقسيم البيانات باستخدام الفاصل الجديد (::)
        data_parts = query["data"].split("::")
        
        if len(data_parts) >= 3:
            action = data_parts[0]
            amount = float(data_parts[1])
            u_uid = data_parts[2]

            try:
                if action == "acc":
                    db.collection("users").doc(u_uid).update({"balance": firestore.Increment(amount)})
                    send_telegram(chat_id, f"✅ تم إضافة `{amount}$` للحساب `{u_uid}`")
                    send_telegram(u_uid, f"✅ تم قبول طلبك وشحن `{amount}$` في رصيدك.")
                
                elif action == "rej":
                    send_telegram(chat_id, f"❌ تم رفض طلب الحساب `{u_uid}`")
                    send_telegram(u_uid, "❌ نعتذر، تم رفض طلب الشحن الخاص بك.")

                # مسح الأزرار لمنع التكرار
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup", 
                              json={"chat_id": chat_id, "message_id": query["message"]["message_id"], "reply_markup": None})
            except Exception as e:
                send_telegram(chat_id, f"⚠️ خطأ في Firebase: {str(e)}")
        else:
            # إذا استمر الخطأ، سنعرض البيانات الخام لتشخيصها
            send_telegram(chat_id, f"⚠️ خطأ في قراءة الزر. البيانات المستلمة: `{query['data']}`")

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
