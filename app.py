import os, requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# إعداد Firebase في السيرفر (تأكد من رفع ملف الخدمة الخاص بك)
# ملاحظة: ستحتاج لملف JSON الخاص بـ Firebase Admin SDK ليعمل الخصم حقيقياً
# سنستخدم هنا هيكلية منطق الأزرار

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

@app.route('/send_order', methods=['POST'])
def send_order():
    data = request.get_json(force=True)
    u_name = data.get('user_name')
    u_uid = data.get('user_uid')
    details = data.get('details', {})
    o_type = data.get('type')

    msg = f"🔔 {o_type} جديد\n👤 العميل: {u_name}\n🆔 ID: {u_uid}\n"
    msg += "------------------\n"
    for k, v in details.items(): msg += f"🔹 {k}: {v}\n"

    # أزرار تليجرام الثلاثية
    reply_markup = {
        "inline_keyboard": [[
            {"text": "✅ تم", "callback_data": f"accept_{u_uid}_{details.get('النوع', '0')}"},
            {"text": "❌ رفض", "callback_data": f"reject_{u_uid}"},
            {"text": "📝 تعديل وتم", "callback_data": f"edit_{u_uid}"}
        ]]
    }

    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
        "chat_id": CHAT_ID, "text": msg, "reply_markup": reply_markup
    })
    return jsonify({"status": "ok"})

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"]
        # هنا يتم وضع منطق التعامل مع Firebase Admin 
        # لتنفيذ "accept" (إضافة رصيد) أو "edit"
        
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
            "callback_query_id": query["id"],
            "text": "جاري معالجة العملية..."
        })
        
        # تحديث الرسالة
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
            "chat_id": query["message"]["chat"]["id"],
            "message_id": query["message"]["message_id"],
            "text": query["message"]["text"] + "\n\n⚙️ تم الإجراء بنجاح!"
        })
    return "ok"
