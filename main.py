import os
from pathlib import Path
from typing import List
import urllib.request
import urllib.error
import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="Hossam AI — OneState Rules")

# Set these as environment variables in your hosting dashboard.
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
    return {"status": "ok", "rules_loaded": RULES_PATH.exists()}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    if not RULES_PATH.exists():
        raise HTTPException(status_code=503, detail="OneState rules file is missing")

    rules = RULES_PATH.read_text(encoding="utf-8")
    prompt = f"""أنت Hossam AI، مساعد مختص حصراً بقوانين لعبة OneState.
أجب بالعربية وبأسلوب واضح ومختصر، واعتمد فقط على نص القوانين المرفق أدناه.
إذا لم تجد القانون أو العقوبة في النص، قل بوضوح إن النص المتاح لا يحددها ولا تخمّن.
ميّز بين وصف اللاعب والاستنتاج، واطلب تفاصيل إضافية إذا كانت ضرورية.
لا تقدم نصائح خارج قوانين OneState.

نص القوانين:
{rules}

سؤال اللاعب:
{req.message}
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 900}
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        return ChatResponse(answer=answer)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:1000]
        raise HTTPException(status_code=502, detail=f"AI provider error: {detail}")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not obtain an AI response")
