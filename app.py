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

# ذاكرة مؤقتة لتخزين العمليات (لمنع مشاكل الأزرار)
pending_operations = {}

def send_telegram(chat_id, text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    return requests.post(url, json=payload)

@app.route('/')
def home(): return "Bot Active", 200

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
                
                # تخزين البيانات في الذاكرة لتجنب أخطاء الزر
                op_id = f"op_{text[:5]}" 
                pending_operations[op_id] = {"uid": text, "amount": 10.0}
                
                markup = {
                    "inline_keyboard": [
                        [{"text": "✅ قبول وشحن 10$", "callback_data": f"accept_{op_id}"}],
                        [{"text": "❌ رفض الطلب", "callback_data": f"reject_{op_id}"}]
                    ]
                }
                send_telegram(chat_id, f"👤 *بيانات الحساب:*\n💰 الرصيد: {bal}$\n🆔 ID: `{text}`", markup)
            else:
                send_telegram(chat_id, "❌ الـ ID غير موجود في السجلات.")

    # 2. معالجة الأزرار
    if "callback_query" in update:
        query = update["callback_query"]
        callback_data = query["data"]
        chat_id = query["message"]["chat"]["id"]
        
        # إيقاف التحميل
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                      json={"callback_query_id": query["id"], "text": "يتم التنفيذ..."})

        # فك التشفير البسيط
        try:
            action, op_id = callback_data.split("_")
            if op_id in pending_operations:
                u_uid = pending_operations[op_id]["uid"]
                amount = pending_operations[op_id]["amount"]

                if action == "accept":
                    db.collection("users").doc(u_uid).update({"balance": firestore.Increment(amount)})
                    send_telegram(chat_id, f"✅ تم شحن `{amount}$` بنجاح للـ ID: `{u_uid}`")
                    send_telegram(u_uid, f"✅ تم قبول طلبك وشحن رصيدك بمبلغ `{amount}$`.")
                else:
                    send_telegram(chat_id, f"❌ تم رفض الطلب للـ ID: `{u_uid}`")
                    send_telegram(u_uid, "❌ نعتذر، تم رفض طلب الشحن الخاص بك.")
                
                # مسح الأزرار والعملية من الذاكرة
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup", 
                              json={"chat_id": chat_id, "message_id": query["message"]["message_id"], "reply_markup": None})
                del pending_operations[op_id]
            else:
                send_telegram(chat_id, "⚠️ انتهت صلاحية هذا الزر، يرجى البحث عن الـ ID مرة أخرى.")
        except Exception as e:
            send_telegram(chat_id, f"⚠️ حدث خطأ غير متوقع: `{str(e)}`")

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
