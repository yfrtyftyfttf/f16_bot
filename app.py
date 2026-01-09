import os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

@app.route('/')
def home():
    return "F16 Server is Live and Stable!", 200

# 1. استقبال الطلب من الموقع وإرساله للبوت
@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.get_json(force=True)
        u_name = data.get('user_name', 'عميل')
        details = data.get('details', {})
        
        msg = f"🚀 طلب جديد من F16\n👤 العميل: {u_name}\n"
        for k, v in details.items():
            msg += f"🔹 {k}: {v}\n"

        # أزرار الـ Callback ببيانات بسيطة
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ تنفيذ", "callback_data": "done"},
                {"text": "❌ رفض", "callback_data": "reject"}
            ]]
        }

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": CHAT_ID, 
            "text": msg,
            "reply_markup": reply_markup
        })
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# 2. معالجة ضغطات الأزرار (Webhook)
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    
    if "callback_query" in update:
        query = update["callback_query"]
        callback_id = query["id"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        action = query.get("data")

        # تحديد النتيجة
        if action == "done":
            res_text = "✅ تم التنفيذ"
            alert = "تم قبول الطلب بنجاح"
        else:
            res_text = "❌ تم الرفض"
            alert = "تم رفض الطلب"

        # إغلاق علامة التحميل في تليجرام
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": alert
        })

        # تحديث نص الرسالة لضمان التغيير
        original_text = query["message"]["text"].split("📍")[0].strip()
        new_msg_text = f"{original_text}\n\n📍 حالة الطلب: {res_text}"
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": new_msg_text
        })

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
