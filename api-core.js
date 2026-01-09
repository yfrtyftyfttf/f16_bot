// إعدادات Firebase
const firebaseConfig = {
    apiKey: "AIzaSyDrLSVoJJsEzlmcIBvNNb9OJzWtJixYhpw",
    authDomain: "army-smm.firebaseapp.com",
    projectId: "army-smm",
    storageBucket: "army-smm.firebasestorage.app",
    messagingSenderId: "27268417960",
    appId: "1:27268417960:web:990e040e77a0c38a11f59d"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();

// دالة الإرسال الموحدة للسيرفر
async function sendToF16Server(payload) {
    const user = auth.currentUser;
    if (!user) return alert("يرجى تسجيل الدخول");

    try {
        const snap = await db.collection("users").doc(user.uid).get();
        const userData = snap.data();

        const response = await fetch('https://f16-bot.onrender.com/send_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...payload,
                user_uid: user.uid,
                user_name: userData.name || "عميل"
            })
        });
        return response.ok;
    } catch (e) {
        console.error("Connection Error:", e);
        return false;
    }
}
