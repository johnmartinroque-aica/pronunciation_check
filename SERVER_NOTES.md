# Pronunciation server – notes

Saved from a Claude Code chat on 2026-10-20.

## What was built

| File | Purpose |
|---|---|
| `server.py` | HTTP API so another website can send audio and get a pronunciation score |
| `client/pronunciationServer.ts` | Code for the Next.js website. Copy the whole file into the other project or another Claude chat; the comment block at the top explains how to integrate it |

The model (`facebook/wav2vec2-lv-60-espeak-cv-ft`) runs **locally** on the CPU.
It is downloaded once (~1.2 GB) into `~/.cache/huggingface`; after that no
audio leaves the machine.

## Run the server

```powershell
.\.venv\Scripts\Activate.ps1
python server.py
```

- Listens on `http://127.0.0.1:8000`
- Interactive test page: `http://127.0.0.1:8000/docs`
- Health check: `GET /health` returns `{"ok": true}`

Optional environment variables:

| Variable | Meaning | Default |
|---|---|---|
| `ALLOWED_ORIGINS` | Comma-separated sites allowed to call the API, e.g. `http://localhost:3000,https://mysite.com` | `*` (any site) |
| `API_KEY` | If set, requests must send the header `X-API-Key: <value>` | not set |
| `HOST`, `PORT` | Where to listen | `127.0.0.1`, `8000` |

## API

`POST /analyze` as `multipart/form-data`:

- `audio`: the recording. WAV is best; webm/ogg/mp4/mp3 need ffmpeg on PATH
  (installed on this PC via Chocolatey). Max 10 MB.
- `text`: the word or sentence the user was asked to say.

Test from the command line:

```bash
curl -F "audio=@recording.wav" -F "text=Rock the lock, then lock the rock." http://127.0.0.1:8000/analyze
```

Response (shortened):

```json
{
  "ok": true,
  "score": 87,
  "grade": {"letter": "B", "verdict": "Good", "color": "#65a30d"},
  "allWordsCorrect": false,
  "expected": {"phonemes": ["ɹ","ɑ","k", "..."], "soundsLike": "r-ah-k-..."},
  "heard":    {"phonemes": ["r","ɔ","k", "..."], "soundsLike": "r-aw-k-..."},
  "words":  [{"word": "Rock", "score": 67, "phonemes": ["ɹ","ɑ","k"], "soundsLike": "r-ah-k"}],
  "issues": [{"word": "Rock", "message": "you said \"aw\" ... instead of \"ah\" ...", "tip": null}]
}
```

If the recording is too short or too quiet:
`{"ok": false, "error": "too_short_or_quiet", "message": "..."}`

## Using it from the website

1. Copy `client/pronunciationServer.ts` into the Next.js project, e.g.
   `components/training/pronunciationServer.ts`.
2. Add to `.env.local`: `NEXT_PUBLIC_PRONUNCIATION_API_URL=http://127.0.0.1:8000`
3. Use the hook `useServerPronunciationCheck(onResult)`. It works the same way
   as the existing `useSentenceCheck` (`start(text)`, `finishListening()`,
   `isListening`, plus `isAnalyzing` and `cancel()`), so it plugs into the
   countdown in `MinimalPairTrainer.tsx` for step 3 (single word) and
   step 4 (tongue twister).
4. By default "correct" means every word scored 100. Pass `{ passScore: 80 }`
   as the second argument to be more forgiving.

The client records the mic with the browser's noise suppression turned on,
and converts the recording to 16 kHz mono WAV before sending it.

**Hosting:** a website can reach `127.0.0.1` only on the computer running the
server. Once the website is live on HTTPS, the server must also be hosted
with HTTPS, and `ALLOWED_ORIGINS` should be set to the site's address.

## Known issues / to-do

1. **"r" counted as wrong.** The model outputs `r` but espeak expects `ɹ`
   (same sound in English), so users lose points and see
   *"said 'r' instead of 'r'"*. Fix: map `r` → `ɹ` in `normalize()` in
   `pronounce.py`. Other symbol pairs may need the same treatment.
2. **"A" must be said as "ay".** `expected_phones_per_word()` sends the words
   to espeak one at a time, so a lone "a" becomes the letter name `eɪ`
   instead of the natural `ə` ("uh"). The same probably affects "the", "to",
   "of" and "for". Options:
   - Phonemize the whole sentence at once so espeak uses context
     (recommended), with a fallback if the word counts don't match.
   - Add an override table for weak words, e.g. `{"a": ["ə"], "the": ["ðə"]}`.
   - Accept several pronunciations per word (bigger change to the matching).
3. **Background noise.** Fan noise can stop silence trimming
   (fixed level `0.01` in `trim_silence`) and can sound like s/f/sh/th.
   Other voices or a TV are worse. Ideas, easiest first:
   - Set the trimming level from the measured background noise.
   - Use voice activity detection (Silero VAD or `webrtcvad`).
   - Add `noisereduce`:
     `nr.reduce_noise(y=audio, sr=SAMPLE_RATE, stationary=True, prop_decrease=0.8)`
     at the top of `analyze()`. Don't use full strength, because it blurs s/f sounds.
   - Drop low-confidence phonemes using the model's probabilities.
4. **`app.py` uses `share=True`**, which creates a public `*.gradio.live`
   link to the Gradio app. Set it to `False` if only you use it.
