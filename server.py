"""HTTP API for the pronunciation checker, for use from another website.

Run:  python server.py        (listens on http://127.0.0.1:8000)
Docs: http://127.0.0.1:8000/docs  (interactive test page)

POST /analyze   multipart/form-data
    audio  - the recording (WAV is best; webm/ogg/mp4/mp3 need ffmpeg on PATH)
    text   - the sentence or word the user was asked to say
Returns JSON with an overall score, per-word scores and what to fix.

Environment variables (all optional):
    ALLOWED_ORIGINS  comma-separated sites allowed to call this API,
                     e.g. "http://localhost:3000,https://mysite.com" (default: *)
    API_KEY          if set, requests must send header  X-API-Key: <value>
    HOST, PORT       where to listen (default 127.0.0.1:8000)
"""
import io
import os
import shutil
import subprocess
import threading

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from phonemes import explain, respell
from pronounce import SAMPLE_RATE, analyze, load_model
from scoring import grade

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
API_KEY = os.environ.get("API_KEY")

PROC, MODEL = load_model()
_model_lock = threading.Lock()  # one inference at a time keeps memory use predictable

app = FastAPI(title="Pronunciation Check API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


def decode_audio(data):
    """Decode uploaded bytes to float32 mono 16 kHz."""
    try:
        audio, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
        audio = audio.mean(axis=1)
    except Exception:
        # Browser formats (webm/opus, mp4/aac) aren't readable by soundfile.
        if not shutil.which("ffmpeg"):
            raise HTTPException(415, "Unsupported audio format. Send WAV, or install ffmpeg.")
        proc = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-i", "pipe:0",
             "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "pipe:1"],
            input=data, capture_output=True)
        if proc.returncode != 0:
            raise HTTPException(415, "Could not decode audio file.")
        return np.frombuffer(proc.stdout, dtype=np.float32)
    if sr != SAMPLE_RATE:
        n = int(len(audio) * SAMPLE_RATE / sr)
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio)
    return audio.astype(np.float32)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/analyze")
def analyze_endpoint(audio: UploadFile = File(...), text: str = Form(...),
                     x_api_key: str | None = Header(default=None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "Invalid API key.")
    text = text.strip()
    if not text:
        raise HTTPException(400, "text is empty.")
    data = audio.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Audio file too large (max 10 MB).")

    samples = decode_audio(data)
    with _model_lock:
        r = analyze(PROC, MODEL, samples, text)
    if r is None:
        return {"ok": False, "error": "too_short_or_quiet",
                "message": "Didn't catch that - the recording was too short or too quiet."}

    g = grade(r["score"])
    words = [{"word": w, "score": round(ws), "phonemes": ph, "soundsLike": respell(ph)}
             for w, ph, ws in r["words"]]
    issues = [{"word": word, "message": f"you {msg}", "tip": tip or None}
              for _, word, exp, got in r["issues"] for msg, tip in explain(exp, got)]
    return {
        "ok": True,
        "score": round(r["score"]),
        "grade": {"letter": g.letter, "verdict": g.verdict, "color": g.color},
        "allWordsCorrect": all(w["score"] == 100 for w in words),
        "expected": {"phonemes": r["expected"], "soundsLike": respell(r["expected"])},
        "heard": {"phonemes": r["spoken"], "soundsLike": respell(r["spoken"])},
        "words": words,
        "issues": issues,
    }


if __name__ == "__main__":
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")))
