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

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    return requests.post(url, json=payload)

@app.route('/')
def home(): return "Server is running", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "ok", 200

    # 1. معالجة البحث عن ID (رسالة نصية)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        if len(text) > 5:
            user_ref = db.collection("users").doc(text).get()
            if user_ref.exists:
                bal = user_ref.to_dict().get('balance', 0)
                # إرسال بيانات العميل مع الأزرار
                markup = {
                    "inline_keyboard": [
                        [{"text": "✅ قبول وشحن 10$", "callback_data": f"pay:accept:10:{text}"}],
                        [{"text": "❌ رفض الطلب", "callback_data": f"pay:reject:0:{text}"}]
                    ]
                }
                send_telegram(chat_id, f"👤 *بيانات العميل وجدت:*\n💰 الرصيد الحالي: {bal}$\n🆔 ID: `{text}`")
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                              json={"chat_id": chat_id, "text": "اختر الإجراء المطلوب:", "reply_markup": markup})
            else:
                send_telegram(chat_id, "❌ لم يتم العثور على هذا الـ ID في قاعدة البيانات.")

    # 2. معالجة الأزرار (إيقاف التحميل وتحديث الرصيد)
    if "callback_query" in update:
        query = update["callback_query"]
        q_id = query["id"] # معرف الطلب لإيقاف التحميل
        chat_id = query["message"]["chat"]["id"]
        
        # تقسيم البيانات: [العملية, الحالة, المبلغ, الـ ID]
        data = query["data"].split(":")
        status = data[1]
        amount = float(data[2])
        u_uid = data[3]

        # فورا نوقف علامة التحميل في تليجرام
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                      json={"callback_query_id": q_id, "text": "جاري المعالجة..."})

        try:
            if status == "accept":
                # تحديث Firebase
                user_ref = db.collection("users").doc(u_uid)
                user_ref.update({"balance": firestore.Increment(amount)})
                
                # إرسال إشعار للمدير (أنت)
                send_telegram(chat_id, f"✅ تم شحن `{amount}$` للعميل `{u_uid}` بنجاح.")
                # إرسال إشعار للعميل (إذا كان الـ ID هو نفسه Chat ID)
                send_telegram(u_uid, f"✅ تم قبول طلبك وشحن رصيدك بمبلغ `{amount}$`.")

            elif status == "reject":
                send_telegram(chat_id, f"❌ تم رفض طلب العميل `{u_uid}`.")
                send_telegram(u_uid, "❌ نعتذر، تم رفض طلب الشحن الخاص بك.")

            # تحديث الرسالة الأصلية لإخفاء الأزرار
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": query["message"]["message_id"],
                "text": query["message"]["text"] + f"\n\n🏁 الحالة: {'تم القبول' if status == 'accept' else 'تم الرفض'}"
            })

        except Exception as e:
            send_telegram(chat_id, f"⚠️ حدث خطأ أثناء التحديث: {str(e)}")

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
