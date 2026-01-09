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

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    return requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "ok", 200

    # 1. البحث اليدوي عن العميل (عبر الرسائل)
    if "message" in update:
        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip()
        if len(text) > 5:
            user_ref = db.collection("users").doc(text).get()
            if user_ref.exists:
                bal = user_ref.to_dict().get('balance', 0)
                markup = {
                    "inline_keyboard": [
                        [{"text": "✅ قبول وشحن 10$", "callback_data": f"act:accept:10:{text}"}],
                        [{"text": "❌ رفض الطلب", "callback_data": f"act:reject:0:{text}"}]
                    ]
                }
                send_telegram(chat_id, f"👤 عميل موجود\n💰 رصيده الحالي: {bal}$\n🆔 ID: `{text}`")
                # إرسال الأزرار
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                              json={"chat_id": chat_id, "text": "اختر الإجراء:", "reply_markup": markup})

    # 2. معالجة أزرار التنفيذ والرفض (إرسال إشعار للعميل)
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"].split(":") # [act, status, amount, uid]
        
        status = data[1]
        amount = float(data[2])
        u_uid = data[3]
        
        try:
            if status == "accept":
                # تحديث الرصيد في Firebase
                db.collection("users").doc(u_uid).update({"balance": firestore.Increment(amount)})
                
                # رسالة للمدير
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                              json={"callback_query_id": query["id"], "text": "✅ تم الشحن وإبلاغ العميل"})
                
                # إشعار للعميل (الزبون)
                send_telegram(u_uid, f"✅ *تم تنفيذ طلب الشحن الخاص بك!*\n💰 تم إضافة: `{amount}$` إلى رصيدك بنجاح.\nنتمنى لك تجربة ممتعة.")

            elif status == "reject":
                # رسالة للمدير
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                              json={"callback_query_id": query["id"], "text": "❌ تم الرفض وإبلاغ العميل"})
                
                # إشعار للعميل (الزبون)
                send_telegram(u_uid, "❌ *نعتذر منك!*\nلقد تم رفض طلب الشحن الخاص بك. يرجى التأكد من البيانات أو التواصل مع الدعم الفني.")

            # تحديث رسالة المدير لتوضيح أن العملية تمت
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": query["message"]["chat"]["id"],
                "message_id": query["message"]["message_id"],
                "text": query["message"]["text"] + f"\n\n🏁 *الحالة النهائية:* {'تم القبول' if status == 'accept' else 'تم الرفض'}"
            })

        except Exception as e:
            send_telegram(query["message"]["chat"]["id"], f"❌ خطأ: {str(e)}")

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
