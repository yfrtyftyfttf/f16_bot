import os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

@app.route('/')
def home():
    return "F16 Server is Active", 200

# إرسال الطلب للبوت
@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.get_json(force=True)
        u_name = data.get('user_name', 'عميل')
        details = data.get('details', {})
        
        msg = f"🚀 طلب جديد من F16\n👤 {u_name}\n"
        for k, v in details.items():
            msg += f"🔹 {k}: {v}\n"

        # أزرار ببيانات واضحة وبسيطة
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ تنفيذ", "callback_data": "done"},
                {"text": "❌ رفض", "callback_data": "reject"}
            ]]
        }

        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": CHAT_ID, 
            "text": msg,
            "reply_markup": reply_markup
        })
        return jsonify({"status": "success", "tel_res": r.json()}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

# استقبال ضغطات الأزرار
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json()
    
    if "callback_query" in update:
        query = update["callback_query"]
        callback_id = query["id"]
        chat_id = query["message"]["chat"]["id"]
        message_id = query["message"]["message_id"]
        data = query.get("data", "") # البيانات المخزنة في الزر

        # معالجة دقيقة بناءً على النص
        if data == "done":
            res_text = "✅ تم التنفيذ بنجاح"
            alert = "تم التأكيد"
        elif data == "reject":
            res_text = "❌ تم رفض الطلب"
            alert = "تم الرفض"
        else:
            res_text = f"⚠️ بيانات غير متوقعة: {data}"
            alert = "خطأ في البيانات"

        # إغلاق التحميل في تليجرام
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": callback_id,
            "text": alert
        })

        # تحديث الرسالة
        original = query["message"]["text"]
        if "حالة" not in original:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": chat_id,
                "message_id": message_id,
                "text": f"{original}\n\n📍 حالة الطلب: {res_text}"
            })

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
