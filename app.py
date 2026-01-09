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

def send_telegram(chat_id, text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    return requests.post(url, json=payload)

@app.route('/')
def home(): return "Server Active", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "ok", 200

    # 1. البحث عن الـ ID (الرسائل النصية)
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()

        if len(text) > 5:
            user_ref = db.collection("users").doc(text).get()
            if user_ref.exists:
                data = user_ref.to_dict()
                bal = data.get('balance', 0)
                
                # إرسال بيانات العميل مع الأزرار - تم تحسين الـ callback_data
                markup = {
                    "inline_keyboard": [
                        [{"text": "✅ قبول وشحن 10$", "callback_data": f"acc_10_{text}"}],
                        [{"text": "❌ رفض الطلب", "callback_data": f"rej_0_{text}"}]
                    ]
                }
                send_telegram(chat_id, f"👤 *تم العثور على الحساب:*\n💰 الرصيد الحالي: {bal}$\n🆔 ID: `{text}`", markup)
            else:
                send_telegram(chat_id, "❌ لم يتم العثور على هذا الـ ID.")

    # 2. معالجة الأزرار (إيقاف التحميل وتحديث الرصيد)
    if "callback_query" in update:
        query = update["callback_query"]
        q_id = query["id"]
        chat_id = query["message"]["chat"]["id"]
        
        # استلام البيانات وتفكيكها بحذر لمنع IndexError
        data_str = query["data"]
        parts = data_str.split("_")
        
        # فورا نوقف علامة التحميل
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                      json={"callback_query_id": q_id, "text": "جاري المعالجة..."})

        if len(parts) >= 3:
            action = parts[0] # acc أو rej
            amount = float(parts[1])
            u_uid = parts[2]

            try:
                if action == "acc":
                    # تحديث Firebase
                    db.collection("users").doc(u_uid).update({"balance": firestore.Increment(amount)})
                    
                    # إشعار المدير
                    send_telegram(chat_id, f"✅ تم شحن `{amount}$` للعميل `{u_uid}`.")
                    # إشعار العميل (بافتراض أن الـ UID هو نفس الـ Chat ID)
                    send_telegram(u_uid, f"✅ تم قبول طلبك وشحن رصيدك بمبلغ `{amount}$`.")

                elif action == "rej":
                    send_telegram(chat_id, f"❌ تم رفض طلب العميل `{u_uid}`.")
                    send_telegram(u_uid, "❌ نعتذر، تم رفض طلب الشحن الخاص بك.")

                # حذف الأزرار بعد التنفيذ
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageReplyMarkup", 
                              json={"chat_id": chat_id, "message_id": query["message"]["message_id"], "reply_markup": None})

            except Exception as e:
                send_telegram(chat_id, f"⚠️ خطأ أثناء التحديث: {str(e)}")
        else:
            send_telegram(chat_id, "⚠️ بيانات الزر غير صالحة.")

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
