import os, requests, json
from flask import Flask, request
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
        cred = credentials.Certificate(cred_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("✅ Connected to Firebase")
except Exception as e:
    print(f"❌ Firebase Setup Error: {e}")

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
ADMIN_ID = "6695916631"

# قاموس لتخزين حالة الإدارة مؤقتاً
admin_state = {}

def send_telegram(text, markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_ID, "text": text, "parse_mode": "Markdown"}
    if markup: payload["reply_markup"] = markup
    r = requests.post(url, json=payload)
    return r.json()

@app.route('/')
def home(): return "Bot is Online", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if not update: return "empty", 200

    # 1. معالجة الرسائل النصية (البحث عن ID)
    if "message" in update:
        msg = update["message"]
        chat_id = str(msg["chat"]["id"])
        text = msg.get("text", "")

        if chat_id == ADMIN_ID:
            # إذا كان النص هو ID مستخدم (طويل)
            if len(text) > 15:
                try:
                    user_doc = db.collection("users").doc(text).get()
                    if user_doc.exists:
                        data = user_doc.to_dict()
                        name = data.get('name', 'غير معروف')
                        balance = data.get('balance', 0.0)
                        
                        resp_text = f"👤 *بيانات المستخدم:*\n\n"
                        resp_text += f"🔹 الاسم: {name}\n"
                        resp_text += f"💰 الرصيد الحالي: {balance}$\n"
                        resp_text += f"🆔 الـ ID: `{text}`"
                        
                        markup = {
                            "inline_keyboard": [
                                [{"text": "➕ شحن رصيد", "callback_data": f"ask:charge:{text}"}],
                                [{"text": "➖ خصم رصيد", "callback_data": f"ask:deduct:{text}"}],
                                [{"text": "❌ إغلاق", "callback_data": "close"}]
                            ]
                        }
                        send_telegram(resp_text, markup)
                    else:
                        send_telegram("❌ هذا الـ ID غير موجود في قاعدة البيانات.")
                except Exception as e:
                    send_telegram(f"❌ خطأ في البحث: {str(e)}")
            
            # إذا كان الإدمن في حالة انتظار إدخال مبلغ
            elif ADMIN_ID in admin_state:
                state = admin_state.pop(ADMIN_ID)
                try:
                    amount = float(text)
                    u_uid = state['uid']
                    action = state['action']
                    
                    change = amount if action == "charge" else -amount
                    db.collection("users").doc(u_uid).update({"balance": firestore.Increment(change)})
                    
                    send_telegram(f"✅ تم التحديث!\nتم {'إضافة' if action == 'charge' else 'خصم'} `{amount}$` للمستخدم.")
                except:
                    send_telegram("⚠️ يرجى إرسال رقم فقط.")

    # 2. معالجة ضغطات الأزرار
    if "callback_query" in update:
        query = update["callback_query"]
        data = query["data"].split(":")
        
        if data[0] == "ask":
            admin_state[ADMIN_ID] = {"action": data[1], "uid": data[2]}
            action_name = "إضافته" if data[1] == "charge" else "خصمه"
            send_telegram(f"✍️ أرسل المبلغ المراد {action_name} الآن:")
        
        elif data[0] == "close":
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage", 
                          json={"chat_id": ADMIN_ID, "message_id": query["message"]["message_id"]})

    return "ok", 200

# إبقاء استقبال الطلبات من الموقع كما هو
@app.route('/send_order', methods=['POST'])
def send_order():
    # ... الكود الخاص بك لإرسال طلبات الرشق ...
    return "ok", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
