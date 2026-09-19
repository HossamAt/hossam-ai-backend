import os
import re
import uuid
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI
from pydantic import BaseModel

BASE = Path(__file__).parent
RULES_FILE = BASE / "rules_ar.txt"

app = FastAPI(title="Hossam AI")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

SYSTEM_PROMPT = """أنت Hossam AI، مساعد قوانين OneState RP.

مهمتك تحليل الواقعة كما وصفها المستخدم، وليس مطابقة كلمات فقط.

قواعد صارمة:
1) تحدث بالعربية فقط. لا تستخدم الإنجليزية إلا إذا كان كود المادة نفسه مثل RP4/6.
2) افهم السياق كاملًا: من الفاعل، ماذا فعل، أين، متى، هل توجد فعالية، هل يوجد سبب RP، نوع السلاح/المركبة، عدد الأشخاص، هل الشخص شرطي/جيش/MD، وهل توجد حالة خاصة.
3) استخدم الحالات التطبيقية الشائعة المحددة في القوانين عندما تنطبق؛ فهي أولوية على القاعدة العامة لأنها أكثر تحديدًا.
4) بعض الحالات تحتاج تحليلًا سياقيًا حتى لو لم تذكر القاعدة الفعل حرفيًا. اربط الوقائع بشروط المادة، لكن لا تخترع قانونًا أو عقوبة جديدة.
5) إذا كانت المعلومات كافية للحكم: لا تسأل أي سؤال، أعطِ النتيجة مباشرة.
6) لا تسأل إلا إذا كانت معلومة ناقصة يمكن أن تغيّر المادة أو العقوبة. اسأل سؤالًا واحدًا فقط في كل رسالة، وبأقل عدد ممكن من الأسئلة.
7) لا تسأل عن معلومات لا تغيّر النتيجة.
8) إذا كانت هناك عدة مخالفات واضحة في نفس الواقعة، اعرضها كلها. لا تجمع العقوبات أو تفترض التراكم إلا إذا كان المصدر ينص عليه.
9) لا تخترع كودًا أو عقوبة أو مدة.
10) إذا لم يوجد نص واضح يحسم الحالة، أخرج حرفيًا:
«القوانين المتوفرة لا تحسم هذه الحالة بشكل واضح.»
11) لا تذكر للمستخدم كلمات تقنية مثل backend أو API أو Gemini أو prompt أو server أو database أو system أو error.
12) إذا حدث خلل داخلي، أخرج فقط:
«حدث خطأ مؤقتًا، حاول مرة أخرى.»
13) إذا طلب المستخدم مادة مباشرة مثل «شو قانون RP4؟»، أجب مباشرة من الفهرس دون أسئلة.
14) إذا طلب قسم MD أو الشرطة أو الجيش، استخدم القسم المطلوب فقط وقدم القاعدة المختصرة.
15) حافظ على أكواد المواد كما هي، بما فيها الأكواد المركبة مثل RP1/4/6 وRP13-ABUSE1.
16) تعامل مع Red Zone حسب قاعدة Hossam AI الخاصة: القتل داخل Red Zone بلا عقوبة، باستثناء حالات الميديك التي ينطبق عليها RP16/الحالة الخاصة.
17) لا تعتبر كل كلمة مثل «مداهمة» مخالفة تلقائيًا. حلل المكان والسبب والفعالية والفصيل والظروف.
18) لا تذكر أن قاعدة ما «تفسير منك». أعط النتيجة القانونية فقط عندما يدعمها المصدر.

صيغة الجواب عند وجود نتيجة:
🚫 المخالفة: ...
📋 المادة: ...
⏱️ العقوبة: ...
ℹ️ السبب: ...

إذا كانت هناك أكثر من مخالفة، كرر البطاقات لكل مخالفة.

إذا كانت معلومة واحدة ضرورية فقط:
❓ سؤال واحد واضح ومباشر؟

اجعل الجواب قصيرًا جدًا وواضحًا، ولا تكرر وصف المستخدم كاملًا.
"""

RULES = RULES_FILE.read_text(encoding="utf-8") if RULES_FILE.exists() else ""

# Fast direct lookup index.
CODE_RE = re.compile(r"\b(?:NAME\d+|AC\d+|RP\d+(?:\.\d+)?|CHAT\d+|TCHAT\d+|ABUSE\d+(?:\.\d+)?|ALERT\d+|MEDIA\d+|CLAN\d+(?:\.\d+)?|MD\d+(?:\.\d+)?|11\.\d+|12\.\d+)\b", re.I)

def relevant_rules(message: str) -> str:
    m = message.lower()
    # Direct article lookup: return only matching lines.
    codes = set(x.upper() for x in CODE_RE.findall(message))
    if codes:
        lines = [ln for ln in RULES.splitlines() if any(code in ln.upper() for code in codes)]
        if lines:
            return "\n".join(lines[:12])

    groups = []
    if any(x in m for x in ["جرين", "green", "زون", "منطقة خضراء", "منطقة حمراء", "red zone"]):
        groups += ["Green Zone:", "Neutral/green:", "Special Hossam AI application rule:"]
    if any(x in m for x in ["ميديك", "مسعف", "طبيب", "md", "تحالف طبي"]):
        groups += ["10 MD — Medical Alliance:", "Factions:"]
    if any(x in m for x in ["شرطة", "شرطي", "police", "اعتقال", "سجن", "كف", "تاسر"]):
        groups += ["11 Police:", "Factions:"]
    if any(x in m for x in ["جيش", "عسكري", "army", "قاعدة عسكرية", "مداهمة", "مداهم"]):
        groups += ["12 Army:", "Factions:", "Neutral/green:"]
    if any(x in m for x in ["شات", "سب", "إهان", "صوت", "رسايل", "فويس"]):
        groups += ["Voice:"]
    if any(x in m for x in ["قلتش", "غليتش", "جدار", "اخرج من rp", "افك", "afk"]):
        groups += ["Serious:"]
    if any(x in m for x in ["عصابة", "كلان", "gang", "تاسر"]):
        groups += ["9.1 CLAN1", "Neutral/green:", "Factions:"]
    if any(x in m for x in ["قتل", "ضرب", "طلق", "اطلاق", "دعس", "دهس", "مركبة", "سيارة"]):
        groups += ["5.1 RP1", "5.2 RP2", "5.4 RP4", "5.6 RP6", "5.9 RP9", "5.9.1 RP9.1", "5.16 RP16",
                   "Green Zone:", "Neutral/green:", "Factions:", "Special Hossam AI application rule:"]

    # Extract sections by headings. Keep compact context.
    if not groups:
        return RULES[:14000]

    selected = []
    lines = RULES.splitlines()
    for i, line in enumerate(lines):
        if any(g.lower() in line.lower() for g in groups):
            selected.extend(lines[max(0, i-1): min(len(lines), i+28)])
    # Always include application-case header and conflicts, but compactly.
    app_start = next((i for i,l in enumerate(lines) if "## HOSSAM AI APPLICATION CASES" in l), None)
    if app_start is not None:
        selected.extend(lines[app_start: min(len(lines), app_start+120)])
    # Deduplicate preserving order.
    out, seen = [], set()
    for ln in selected:
        if ln not in seen:
            seen.add(ln)
            out.append(ln)
    return "\n".join(out)[:18000]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

def call_model(message: str, context: str) -> str:
    if not GEMINI_API_KEY:
        return "حدث خطأ مؤقتًا، حاول مرة أخرى."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    prompt = f"""{SYSTEM_PROMPT}

القوانين ذات الصلة بهذه الرسالة:
---BEGIN RULES---
{context}
---END RULES---

رسالة المستخدم:
{message}

أجب للمستخدم فقط، بالعربية، وباختصار. لا تذكر أي معلومات تقنية."""
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.05,
            "maxOutputTokens": 500,
            "topP": 0.8
        }
    }
    try:
        r = requests.post(
            url,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if not text:
            return "حدث خطأ مؤقتًا، حاول مرة أخرى."
        # Remove accidental technical leakage.
        banned = ["backend", "api", "gemini", "prompt", "database", "server", "system", "exception", "traceback"]
        if any(x in text.lower() for x in banned):
            return "القوانين المتوفرة لا تحسم هذه الحالة بشكل واضح."
        return text
    except Exception:
        return "حدث خطأ مؤقتًا، حاول مرة أخرى."

@app.get("/")
def root():
    return {"status": "ok", "name": "Hossam AI"}

@app.post("/chat")
def chat(req: ChatRequest):
    message = (req.message or "").strip()
    if not message:
        return {"reply": "اكتب الحالة أو المادة التي تريد معرفة حكمها."}
    context = relevant_rules(message)
    return {"reply": call_model(message, context)}
