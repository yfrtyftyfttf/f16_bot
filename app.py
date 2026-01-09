import os, requests, json
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
CORS(app)

# 1. إعداد Firebase Admin
fb_config = os.environ.get('FIREBASE_CONFIG_JSON')
if fb_config:
    cred_dict = json.loads(fb_config)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

BOT_TOKEN = "6785445743:AAFquuyfY2IIjgs2x6PnL61uA-3apHIpz2k"
CHAT_ID = "6695916631"

pending_edits = {}

@app.route('/')
def home(): return "F16 System Live! 🚀", 200

@app.route('/send_order', methods=['POST'])
def send_order():
    try:
        data = request.get_json(force=True)
        u_uid = data.get('user_uid')
        u_name = data.get('user_name')
        o_type = data.get('type')
        details = data.get('details', {})
        
        price = details.get('السعر الإجمالي', '0').replace('$', '')
        card_val = details.get('فئة الكارت', '0').replace('$ آسيا', '')
        final_val = card_val if "شحن" in o_type else price

        msg = f"🔔 {o_type}\n👤 العميل: {u_name}\n🆔 ID: {u_uid}\n"
        msg += "------------------\n"
        for k, v in details.items(): msg += f"🔹 {k}: {v}\n"

        action_prefix = "charge" if "شحن" in o_type else "deduct"
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ تنفيذ", "callback_data": f"{action_prefix}:{u_uid}:{final_val}"},
                {"text": "📝 تعديل وتم", "callback_data": f"edit:{u_uid}:{action_prefix}"},
                {"text": "❌ رفض", "callback_data": f"reject:{u_uid}"}
            ]]
        }

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
            "chat_id": CHAT_ID, "text": msg, "reply_markup": reply_markup
        })
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    
    if "callback_query" in update:
        query = update["callback_query"]
        cb_data = query["data"].split(":")
        action = cb_data[0]
        
        if action == "reject":
             requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": query["message"]["chat"]["id"],
                "message_id": query["message"]["message_id"],
                "text": query["message"]["text"] + "\n\n❌ النتيجة: تم رفض الطلب"
            })
        
        elif action == "edit":
            pending_edits[CHAT_ID] = {"u_uid": cb_data[1], "type": cb_data[2]}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": CHAT_ID, "text": "✍️ أرسل القيمة الجديدة الآن:"
            })
        
        elif action in ["charge", "deduct"]:
            u_uid = cb_data[1]
            val = float(cb_data[2])
            user_ref = db.collection("users").doc(u_uid)
            user_doc = user_ref.get()

            if action == "deduct":
                current_bal = user_doc.to_dict().get('balance', 0)
                if current_bal < val:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={
                        "callback_query_id": query["id"], "text": "❌ الرصيد غير كافي للخصم!", "show_alert": True
                    })
                    return "ok", 200
            
            change = val if action == "charge" else -val
            user_ref.update({"balance": firestore.Increment(change)})
            
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", json={
                "chat_id": query["message"]["chat"]["id"],
                "message_id": query["message"]["message_id"],
                "text": query["message"]["text"] + f"\n\n⚙️ النتيجة: تم تحديث الرصيد ({change}$)"
            })

        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": query["id"]})

    # معالجة رسالة التعديل النصية
    if "message" in update and str(update["message"]["chat"]["id"]) == CHAT_ID:
        if CHAT_ID in pending_edits:
            edit_data = pending_edits.pop(CHAT_ID)
            try:
                new_val = float(update["message"]["text"])
                change = new_val if edit_data["type"] == "charge" else -new_val
                db.collection("users").doc(edit_data["u_uid"]).update({"balance": firestore.Increment(change)})
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": f"✅ تم التعديل والتنفيذ: {new_val}$"})
            except:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": "❌ أرسل رقماً فقط!"})

    return "ok", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
