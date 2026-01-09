import os, requests, json
from flask import Flask, request, jsonify
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
        # التحقق من وجود مفاتيح معينة لضمان سلامة الملف
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Firebase Connected Successfully")
except Exception as e:
    print(f"❌ Firebase Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"

@app.route('/')
def index(): return "F16 Bot is Running...", 200

# استقبال الطلبات من الموقع
@app.route('/send_order', methods=['POST'])
def send_order():
    data = request.get_json(force=True)
    u_uid = data.get('user_uid')
    u_name = data.get('user_name')
    o_type = data.get('type')
    details = data.get('details', {})
    
    # تحديد القيمة المالية (سواء كانت شحن أو خصم)
    price_str = details.get('السعر الإجمالي', '0').replace('$', '').strip()
    card_str = details.get('فئة الكارت', '0').split('$')[0].strip()
    final_val = card_str if "شحن" in o_type else price_str

    msg = f"🔔 {o_type}\n👤 العميل: {u_name}\n🆔 ID: {u_uid}\n"
    msg += "------------------\n"
    for k, v in details.items(): msg += f"🔹 {k}: {v}\n"

    action = "charge" if "شحن" in o_type else "deduct"
    reply_markup = {
        "inline_keyboard": [[
            {"text": "✅ تنفيذ", "callback_data": f"{action}:{u_uid}:{final_val}"},
            {"text": "❌ رفض", "callback_data": f"cancel:{u_uid}"}
        ]]
    }

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  json={"chat_id": "6695916631", "text": msg, "reply_markup": reply_markup})
    return "ok", 200

# استقبال التحديثات من تلجرام (Webhook)
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if "callback_query" in update:
        query = update["callback_query"]
        cb_data = query["data"].split(":")
        
        if cb_data[0] == "cancel":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", 
                          json={"callback_query_id": query["id"], "text": "تم إلغاء الطلب"})
            return "ok", 200

        action = cb_data[0] # charge أو deduct
        u_uid = cb_data[1]
        try:
            val = float(cb_data[2])
            user_ref = db.collection("users").doc(u_uid)
            
            # تنفيذ العملية في Firebase
            change = val if action == "charge" else -val
            user_ref.update({"balance": firestore.Increment(change)})
            
            # تحديث رسالة التلجرام لتأكيد النجاح
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": query["message"]["chat"]["id"],
                "message_id": query["message"]["message_id"],
                "text": query["message"]["text"] + f"\n\n✅ النتيجة: تم تحديث الرصيد بـ ({change}$)"
            })
        except Exception as e:
            # إرسال تنبيه في حال وجود خطأ في الـ UID أو قاعدة البيانات
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                          json={"chat_id": "6695916631", "text": f"❌ خطأ تقني: {str(e)}"})

    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
