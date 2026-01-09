import os, requests, json, re
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# --- إعداد Firebase مع التحقق ---
try:
    fb_config = os.environ.get('FIREBASE_CONFIG_JSON')
    if fb_config:
        cred_dict = json.loads(fb_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ تم الاتصال بـ Firebase بنجاح")
except Exception as e:
    print(f"❌ خطأ في تشغيل Firebase: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

@app.route('/')
def home(): return "F16 Bot is Active 🚀", 200

# --- دالة استخراج الرقم فقط من النص ---
def extract_amount(text):
    # تبحث عن أي أرقام (سواء كانت صحيحة أو عشرية) في النص
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(text))
    return float(nums[0]) if nums else 0.0

@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.get_json(force=True)
        u_uid = data.get('user_uid')
        u_name = data.get('user_name')
        o_type = data.get('type')
        details = data.get('details', {})

        # استخراج القيمة المالية (رقم فقط)
        price_val = extract_amount(details.get('السعر الإجمالي', '0'))
        card_val = extract_amount(details.get('فئة الكارت', '0'))
        final_val = card_val if "شحن" in o_type else price_val

        msg = f"📦 {o_type}\n👤 العميل: {u_name}\n🆔 UID: {u_uid}\n"
        msg += "------------------------\n"
        for k, v in details.items(): msg += f"🔹 {k}: {v}\n"

        action = "charge" if "شحن" in o_type else "deduct"
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ تنفيذ", "callback_data": f"{action}:{u_uid}:{final_val}"},
                {"text": "❌ رفض", "callback_data": f"cancel:{u_uid}"}
            ]]
        }

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                      json={"chat_id": CHAT_ID, "text": msg, "reply_markup": reply_markup})
        return "success", 200
    except Exception as e:
        return str(e), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if "callback_query" in update:
        query = update["callback_query"]
        cb_data = query["data"].split(":")
        
        # 1. فحص نوع الإجراء
        action = cb_data[0]
        if action == "cancel":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                          json={"callback_query_id": query["id"], "text": "تم الإلغاء"})
            return "ok", 200

        u_uid = cb_data[1]
        amount = float(cb_data[2])

        try:
            # 2. فحص الاتصال بقاعدة البيانات
            user_ref = db.collection("users").doc(u_uid) # تأكد أن الاسم users بحروف صغيرة
            user_doc = user_ref.get()

            if not user_doc.exists:
                # إذا لم يجد الـ ID، يرسل لك تنبيه فوراً
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                              json={"chat_id": CHAT_ID, "text": f"⚠️ خطأ: لم أجد مستخدم في Firebase بهذا الـ ID:\n`{u_uid}`", "parse_mode": "Markdown"})
                return "ok", 200

            # 3. تنفيذ الإضافة أو الخصم
            change = amount if action == "charge" else -amount
            user_ref.update({"balance": firestore.Increment(change)})

            # 4. تحديث الرسالة لإثبات النجاح
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": query["message"]["chat"]["id"],
                "message_id": query["message"]["message_id"],
                "text": query["message"]["text"] + f"\n\n✅ تم التحديث بنجاح!\n💰 القيمة: {change}$\n🏦 الرصيد الجديد سيظهر عند العميل فوراً."
            })

        except Exception as e:
            # إرسال تقرير خطأ مفصل لك في التلجرام
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": CHAT_ID, "text": f"❌ فشل التنفيذ البرمجي:\n{str(e)}"})

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
