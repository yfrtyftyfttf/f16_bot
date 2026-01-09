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

@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.get_json(force=True)
        u_name = data.get('user_name', 'عميل')
        details = data.get('details', {})
        
        msg = f"🚀 طلب جديد من F16\n👤 {u_name}\n"
        for k, v in details.items():
            msg += f"🔹 {k}: {v}\n"

        # تأكد من أن callback_data مختلفة تماماً لكل زر
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ تم التنفيذ", "callback_data": "btn_done"},
                {"text": "❌ رفض", "callback_data": "btn_reject"}
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

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    
    if "callback_query" in data:
        query = data["callback_query"]
        callback_id = query["id"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        action = query["data"] # هنا نستلم btn_done أو btn_reject

        # 1. تحديد النص بناءً على الزر المضغوط بدقة
        if action == "btn_done":
            status_text = "✅ [حالة الطلب: تم التنفيذ]"
            alert_text = "تم تأكيد التنفيذ بنجاح"
        elif action == "btn_reject":
            status_text = "❌ [حالة الطلب: مرفوض]"
            alert_text = "تم رفض الطلب"
        else:
            status_text = "⚠️ حالة غير معروفة"
            alert_text = "خطأ في المعالجة"

        # 2. إغلاق التحميل في تليجرام
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": alert_text
        })

        # 3. تحديث الرسالة بالنص المناسب
        original_text = query["message"]["text"]
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": message_id,
            "text": f"{original_text}\n\n{status_text}"
        })

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
