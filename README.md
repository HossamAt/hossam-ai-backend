# Hossam AI Backend

Deploy as a Python web service on Render.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add `GEMINI_API_KEY` in Render Environment (never put the key in the Android app).
- Optional: set `GEMINI_MODEL` to a model available to your API key.
- The supplied `rules_ar.txt` contains the uploaded OneState Arabic rules.
- Endpoints: `/health` and `/chat` (POST JSON: `{"message":"..."}`).
