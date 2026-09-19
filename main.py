import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="Hossam AI Backend")
RULES_PATH = Path(__file__).with_name("rules_ar.txt")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.getenv("GEMINI_API_KEY", "")

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def root():
    return {"status": "ok", "service": "Hossam AI Backend"}

@app.get("/health")
def health():
    return {"status": "ok", "rules_loaded": RULES_PATH.exists() and RULES_PATH.stat().st_size > 0}

@app.post("/chat")
async def chat(req: ChatRequest):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY is not configured")
    if not RULES_PATH.exists():
        raise HTTPException(status_code=500, detail="Rules file is missing")
    rules = RULES_PATH.read_text(encoding="utf-8")
    prompt = (
        "أنت Hossam AI، مساعد يجيب عن أسئلة لعبة OneState اعتمادًا على ملف القوانين التالي فقط. "
        "لا تخترع قوانين أو عقوبات غير موجودة. إذا لم تغطِ القوانين السؤال، وضّح أن الملف لا يحتوي على إجابة مؤكدة. "
        "أجب بالعربية وباختصار، واذكر رقم القاعدة عند توفره.\n\n"
        f"القوانين:\n{rules}\n\nسؤال اللاعب: {req.message}"
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Gemini API error ({response.status_code})")
    data = response.json()
    try:
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Unexpected response from Gemini")
    return {"answer": answer}
