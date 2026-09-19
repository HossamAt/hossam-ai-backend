# خادم Hossam AI

## الملفات
- `main.py`: API يتوافق مع تطبيق Android (POST `/chat` ويستقبل `message` ويرجع `answer`).
- `rules_ar.txt`: نص القوانين المستخرج من ملف DOCX المرفق.
- `requirements.txt`: الاعتماديات.
- `render.yaml`: إعداد نشر مبدئي على Render.

## النشر من الموبايل
1. أنشئ مستودع GitHub جديد للخادم وارفع محتويات هذا المجلد إليه.
2. افتح Render وسجّل الدخول عبر GitHub، ثم أنشئ Web Service من مستودع الخادم.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. أضف Environment Variable باسم `GEMINI_API_KEY` وضع مفتاحك فيه من لوحة الاستضافة فقط، وليس داخل Android أو GitHub.
6. بعد النشر افتح `/health` وتأكد من ظهور `status: ok` و`rules_loaded: true`.
7. خذ رابط الخدمة HTTPS وأرسل لي الرابط لنضبطه في Android ثم نبني APK جديد.

ملاحظة: تأكد من شروط وحدود الاستخدام المجاني لدى مزود النموذج والاستضافة؛ قد تتغير. لا ترفع أي مفتاح سري إلى GitHub.
