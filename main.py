import os
from pathlib import Path
import urllib.request
import urllib.error
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Hossam AI — OneState Rules")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
RULES_PATH = Path(__file__).with_name("rules_ar.txt")

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)

class ChatResponse(BaseModel):
    answer: str

@app.get("/")
def root():
    return {"service": "Hossam AI", "status": "online"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "rules_loaded": RULES_PATH.exists(),
        "rules_size": RULES_PATH.stat().st_size if RULES_PATH.exists() else 0,
    }

def build_prompt(message: str, rules: str) -> str:
    return f"""أنت Hossam AI، مساعد متخصص حصراً في تحليل قوانين OneState RP.

مهمتك ليست مطابقة كلمات بشكل آلي. افهم وصف اللاعب للموقف كاملًا، ثم اربط الوقائع بالقوانين الموجودة في المصدر فقط.

قواعد إلزامية:
1) اعتمد فقط على نص القوانين المرفق. لا تستخدم قانونًا أو عقوبة أو مدة من معرفتك العامة.
2) لا تخترع مادة أو رمزًا أو عقوبة.
3) لا تعتبر مجرد كلمة مثل "زون" أو "سلاح" أو "دعس" كافية للحكم.
4) استخرج من وصف اللاعب ما يلزم: المكان، الفعل، سبب RP، السلاح/المركبة، عدد المتضررين، الفصيل، هل الشخص مسعف، هل يوجد إنعاش، هل الحدث بدأ، وأي شرط آخر مؤثر.
5) إذا كانت معلومة أساسية ناقصة ويمكن أن تغير المادة أو العقوبة، اسأل عنها أولاً ولا تعطِ عقوبة نهائية.
6) إذا كانت هناك عدة مواد محتملة، لا تختر عشوائيًا. اذكر باختصار ما الذي يعتمد عليه الاختيار واسأل سؤالًا حاسمًا.
7) إذا انطبقت حالة تطبيقية محددة مذكورة في قسم "الحالات التطبيقية الشائعة"، استخدمها على الحالة التي تنطبق عليها، مع ذكر المادة/المواد والعقوبة كما وردت.
8) إذا لم توجد حالة تطبيقية محددة، استخدم القانون الأساسي المناسب.
9) إذا وُجد اختلاف بين قانون أساسي وحالة تطبيقية محددة، اعتبر الحالة التطبيقية المحددة أكثر تخصيصًا للحالة التي تنطبق عليها، ولا تخفِ وجود الاختلاف إذا كان مهمًا للفهم.
10) إذا لم تحسم القوانين الحالة بوضوح، قل حرفيًا: "القوانين المتوفرة لا تحسم هذه الحالة بشكل واضح."
11) لا تضف قوانين جديدة من عندك، ولا تحول تفسيرك إلى مادة قانونية جديدة.
12) حافظ على رموز المواد كما هي، بما فيها الرموز المركبة.
13) عندما تكون المعلومات كافية، أجب بهذا الترتيب:
   - الحالة
   - هل توجد مخالفة؟
   - المادة/المواد
   - العقوبة
   - السبب
   - ملاحظات إن وجدت
14) كن واضحًا ومختصرًا وبالعربية.
15) لا تقدم نصائح خارج قوانين OneState.

أمثلة لطريقة التفكير المطلوبة:
- "قتلت واحد بالزون" لا تكفي وحدها. اسأل أي زون/موقع؟ وهل يوجد سبب RP؟ وما طبيعة الشخص؟
- "دعست 4 لاعبين بالزون" تتطلب التأكد من أن المقصود داخل الحالة التطبيقية الخاصة بالزون وعدد اللاعبين 3+، ثم تطبيق المادة والعقوبة المحددتين في المصدر.
- "ضربت مسعف" يتطلب معرفة هل كان يقوم بإنعاش اللاعب، لأن الحالات التطبيقية تميز بين الحالتين.

نص القوانين ومصدر المعرفة:
----------------
{rules}
----------------

وصف اللاعب:
----------------
{message}
----------------
"""

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    if not RULES_PATH.exists():
        raise HTTPException(status_code=503, detail="OneState rules file is missing")

    rules = RULES_PATH.read_text(encoding="utf-8")
    prompt = build_prompt(req.message.strip(), rules)

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1200
        }
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            result = json.loads(response.read().decode("utf-8"))

        candidates = result.get("candidates", [])
        if not candidates:
            raise ValueError("AI returned no candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        answer = "".join(
            part.get("text", "") for part in parts if isinstance(part, dict)
        ).strip()

        if not answer:
            raise ValueError("AI returned an empty answer")

        return ChatResponse(answer=answer)

    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:1500]
        raise HTTPException(status_code=502, detail=f"AI provider error: {detail}")
    except (urllib.error.URLError, TimeoutError):
        raise HTTPException(status_code=502, detail="AI provider connection failed")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not obtain a valid AI response")
