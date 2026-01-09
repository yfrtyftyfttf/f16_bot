import os, requests, json, re
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# إعداد Firebase
try:
    fb_config = os.environ.get('FIREBASE_CONFIG_JSON')
    if fb_config:
        cred_dict = json.loads(fb_config)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
except Exception as e: print(f"Firebase Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

# متغير مؤقت لتخزين الـ ID الذي تتعامل معه الآن
admin_state = {}

def send_msg(text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    return requests.post(url, json=payload)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    # 1. إذا أرسلت ID المستخدم كرسالة نصية
    if "message" in update and str(update["message"]["chat"]["id"]) == CHAT_ID:
        text = update["message"].get("text", "")
        
        # إذا كانت الرسالة عبارة عن ID (طويل عادة)
        if len(text) > 15:
            user_ref = db.collection("users").doc(text)
            user_doc = user_ref.get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                name = user_data.get('name', 'بدون اسم')
                bal = user_data.get('balance', 0.0)
                
                msg = f"👤 *بيانات العميل:*\n\n"
                msg += f"🔹 الاسم: {name}\n"
                msg += f"💰 الرصID: {bal}$\n"
                msg += f"🆔 ID: `{text}`"
                
                markup = {
                    "inline_keyboard": [
                        [{"text": "➕ شحن رصيد", "callback_data": f"ask_charge:{text}"}],
                        [{"text": "➖ خصم رصيد", "callback_data": f"ask_deduct:{text}"}],
                        [{"text": "❌ إغلاق", "callback_data": "close"}]
                    ]
                }
                send_msg(msg, markup)
            else:
                send_msg("❌ هذا الـ ID غير موجود في قاعدة البيانات.")
        
        # إذا كنت في حالة انتظار إدخال مبلغ (بعد الضغط على شحن)
        elif CHAT_ID in admin_state:
            state_data = admin_state.pop(CHAT_ID)
            try:
                amount = float(text)
                u_uid = state_data['uid']
                action = state_data['action']
                
                change = amount if action == "charge" else -amount
                db.collection("users").doc(u_uid).update({"balance": firestore.Increment(change)})
                
                send_msg(f"✅ تم بنجاح!\nتم {'إضافة' if action == 'charge' else 'خصم'} مبلغ `{amount}$` للمستخدم.")
            except:
                send_msg("⚠️ يرجى إرسال رقم فقط (مثلاً: 5 أو 10.5)")

    # 2. معالجة ضغطات الأزرار
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"].split(":")
        
        if data[0] == "ask_charge":
            admin_state[CHAT_ID] = {"uid": data[1], "action": "charge"}
            send_msg("✍️ أرسل المبلغ الذي تريد *إضافته* الآن:")
            
        elif data[0] == "ask_deduct":
            admin_state[CHAT_ID] = {"uid": data[1], "action": "deduct"}
            send_msg("✍️ أرسل المبلغ الذي تريد *خصمه* الآن:")
            
        elif data[0] == "close":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", 
                          json={"chat_id": CHAT_ID, "message_id": query["message"]["message_id"]})

    return "ok", 200

@app.route('/send_order', methods=['POST'])
def send_order():
    # ابقِ كود إرسال الطلبات من الموقع كما هو لإشعارك بالطلبات الجديدة
    data = request.get_json(force=True)
    # ... نفس كود إرسال الرسالة السابق ...
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
