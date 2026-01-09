import os, requests, random
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# تهيئة Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"

@app.route('/')
def home(): return "السيرفر يعمل بنجاح!", 200

@app.route('/send_order', methods=['POST'])
def send_order():
    data = request.get_json(force=True)
    u_uid = data.get('user_uid', 'None')
    u_name = data.get('user_name', 'عميل')
    details = data.get('details', {})
    
    text = f"📦 طلب جديد\n👤 العميل: {u_name}\n🆔 UID: {u_uid}\n"
    text += "------------------------\n"
    for k, v in details.items(): text += f"🔹 {k}: {v}\n"

    # أزرار التنفيذ
    btns = [[
        {"text": "تم التنفيذ ✅", "callback_data": f"done_{u_uid}"},
        {"text": "رفض وإرجاع $0 ❌", "callback_data": f"rej_{u_uid}"}
    ]]

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": "6695916631", "text": text, "reply_markup": {"inline_keyboard": btns}
    })
    return jsonify({"status": "success"}), 200

# المسار الذي يستقبل ضغطات الأزرار من تليجرام
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if "callback_query" in update:
        query = update["callback_query"]
        callback_id = query["id"]
        chat_id = query["message"]["chat"]["id"]
        msg_id = query["message"]["message_id"]
        data = query["data"]

        # 1. إيقاف علامة التحميل في تليجرام فوراً
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": "جاري تنفيذ الأمر..." 
        })

        # 2. تحديث الرسالة لتبين أنه تم الضغط
        result_text = "✅ تم التأشير كمنفذ" if "done" in data else "❌ تم الرفض"
        new_text = f"{query['message']['text']}\n\n⚙️ النتيجة: {result_text}"
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": new_text
        })

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
