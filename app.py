import os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

@app.route('/')
def home():
    return "F16 Server is Live!", 200

# 1. استقبال الطلبات من الموقع
@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.get_json(force=True)
        u_name = data.get('user_name', 'عميل')
        details = data.get('details', {})
        
        msg = f"🚀 طلب جديد من F16\n👤 {u_name}\n"
        for k, v in details.items():
            msg += f"🔹 {k}: {v}\n"

        # أزرار التحكم في تليجرام
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ تم التنفيذ", "callback_data": "done"},
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

# 2. استقبال ضغطات الأزرار من تليجرام (حل مشكلة التحميل)
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    
    if "callback_query" in data:
        callback_id = data["callback_query"]["id"]
        chat_id = data["callback_query"]["message"]["chat"]["id"]
        message_id = data["callback_query"]["message"]["message_id"]
        action = data["callback_query"]["data"] # "done" أو "reject"

        # أ- إخبار تليجرام بإيقاف علامة التحميل فوراً
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": "✅ تم تحديث الطلب" if action == "done" else "❌ تم رفض الطلب"
        })

        # ب- تحديث نص الرسالة لتبين أنك ضغطت الزر
        status_text = "✅ [حالة الطلب: تم التنفيذ]" if action == "done" else "❌ [حالة الطلب: مرفوض]"
        original_text = data["callback_query"]["message"]["text"]
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"{original_text}\n\n{status_text}"
        })

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
