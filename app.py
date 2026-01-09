import os, requests, random
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# تهيئة Firebase (تأكد من وجود الملف في GitHub)
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"

@app.route('/')
def home(): return "OK", 200

# استقبال الطلبات من الموقع
@app.route('/send_order', methods=['POST'])
def send_order():
    data = request.get_json(force=True)
    u_uid = data.get('user_uid', 'N/A')
    u_name = data.get('user_name', 'عميل')
    o_type = data.get('type')
    details = data.get('details', {})
    
    text = f"📦 طلب جديد\n👤 العميل: {u_name}\n🆔 UID: {u_uid}\n"
    text += "------------------------\n"
    for k, v in details.items(): text += f"🔹 {k}: {v}\n"

    # أزرار تفاعلية
    if o_type == 'شحن رصيد':
        amt = str(details.get('المبلغ', '0'))
        btns = [[{"text": "✅ قبول وشحن", "callback_data": f"add_{u_uid}_{amt}"}, 
                 {"text": "❌ رفض", "callback_data": "rej"}]]
    else:
        btns = [[{"text": "✅ تم التنفيذ", "callback_data": "done"}]]

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": "6695916631", "text": text, "reply_markup": {"inline_keyboard": btns}
    })
    return jsonify({"status": "success"}), 200

# --- الجزء المسؤول عن "التحميل" وعدم الاستجابة في تليجرام ---
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"]
        msg_id = query["message"]["message_id"]
        chat_id = query["message"]["chat"]["id"]
        
        # معالجة البيانات
        parts = data.split('_')
        action = parts[0]
        
        response_text = "⚙️ جاري المعالجة..."
        
        if action == "add":
            uid, amt = parts[1], float(parts[2])
            # تحديث الرصيد في Firebase
            db.collection('users').document(uid).update({'balance': firestore.Increment(amt)})
            response_text = f"✅ تم شحن {amt}$ للمستخدم"
        elif action == "done":
            response_text = "🎉 تم تأكيد التنفيذ"
        elif action == "rej":
            response_text = "❌ تم رفض الطلب"

        # 1. إخفاء علامة التحميل من تليجرام (ضروري جداً)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": query["id"], "text": response_text
        })

        # 2. تحديث نص الرسالة لكي تعرف أنك ضغطت الزر
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id, "message_id": msg_id, 
            "text": query["message"]["text"] + f"\n\n⚙️ النتيجة: {response_text}"
        })

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
