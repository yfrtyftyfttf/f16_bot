import os, requests, json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request
from flask_cors import CORS

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
        print("✅ Firebase Connected Successfully")
except Exception as e:
    print(f"❌ Firebase Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"

def send_telegram(chat_id, text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if markup:
        payload["reply_markup"] = markup
    return requests.post(url, json=payload)

@app.route('/')
def home():
    return "Bot is running...", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update:
        return "ok", 200

    # 1. معالجة الرسائل النصية (البحث عن ID)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        if len(text) > 4:
            try:
                # تصحيح الخطأ: استخدام document() بدلاً من doc()
                user_ref = db.collection("users").document(text).get()
                
                if user_ref.exists:
                    data = user_ref.to_dict()
                    balance = data.get('balance', 0)
                    
                    msg_text = f"👤 *تم العثور على المستخدم:*\n🆔 ID: `{text}`\n💰 الرصيد الحالي: {balance}$"
                    
                    # الأزرار ترسل الـ ID مباشرة لتجنب أخطاء التقسيم
                    markup = {
                        "inline_keyboard": [
                            [{"text": "➕ شحن 10$", "callback_data": f"add_10_{text}"}],
                            [{"text": "❌ رفض الطلب", "callback_data": f"ref_0_{text}"}]
                        ]
                    }
                    send_telegram(chat_id, msg_text, markup)
                else:
                    send_telegram(chat_id, f"❌ لم يتم العثور على الـ ID: `{text}` في مجموعة users.")
            except Exception as e:
                send_telegram(chat_id, f"⚠️ خطأ في قاعدة البيانات: {str(e)}")

    # 2. معالجة ضغطات الأزرار (الشحن والرفض)
    if "callback_query" in update:
        query = update["callback_query"]
        q_id = query["id"]
        callback_data = query["data"]
        chat_id = query["message"]["chat"]["id"]

        # إيقاف علامة التحميل في تليجرام
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                      json={"callback_query_id": q_id, "text": "جاري التنفيذ..."})

        try:
            parts = callback_data.split("_")
            if len(parts) == 3:
                action = parts[0]
                amount = float(parts[1])
                u_id = parts[2]

                if action == "add":
                    # تحديث الرصيد بزيادة المبلغ
                    db.collection("users").document(u_id).update({"balance": firestore.Increment(amount)})
                    send_telegram(chat_id, f"✅ تم شحن {amount}$ للحساب `{u_id}` بنجاح.")
                    # إرسال إشعار للعميل
                    send_telegram(u_id, f"✅ تم قبول طلبك وشحن رصيدك بمبلغ {amount}$.")
                else:
                    send_telegram(chat_id, f"❌ تم رفض طلب الحساب `{u_id}`.")
                    send_telegram(u_id, "❌ نعتذر، تم رفض طلب الشحن الخاص بك.")

                # مسح الأزرار من الرسالة بعد التنفيذ
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup", 
                              json={"chat_id": chat_id, "message_id": query["message"]["message_id"], "reply_markup": None})

        except Exception as e:
            send_telegram(chat_id, f"⚠️ حدث خطأ أثناء التحديث: {str(e)}")

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
