# Pronunciation Check (microphone)

Speak a sentence into your microphone and get a phoneme-level pronunciation
score, a per-word breakdown, and a list of the sounds you got wrong.

It uses `facebook/wav2vec2-lv-60-espeak-cv-ft` to recognise the phonemes you
actually said, and eSpeak NG to work out the phonemes you *should* have said,
then compares them.

## 1. One-time setup (Windows)

### a) Install eSpeak NG (required)
1. Download the latest `espeak-ng.msi` from
   https://github.com/espeak-ng/espeak-ng/releases (Assets section, x64).
2. Install it to the default location `C:\Program Files\eSpeak NG\`.

   Or from an admin terminal: `winget install --id eSpeak-NG.eSpeak-NG`

The script finds `C:\Program Files\eSpeak NG\libespeak-ng.dll` automatically.
If you installed somewhere else, set the path yourself:

```powershell
$env:PHONEMIZER_ESPEAK_LIBRARY = "D:\path\to\libespeak-ng.dll"
```

### b) Python environment
Python 3.10 - 3.12 is recommended.

```powershell
cd D:\python\pronunciation_check
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

(Have an NVIDIA GPU? You can install the CUDA build of torch instead; CPU is
fast enough for short sentences.)

## 2. Usage

### Web UI (recommended)

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Your browser opens at http://127.0.0.1:7860. Pick a sentence or type your own,
click the microphone, speak, and click stop. The result appears automatically
(or press **Check pronunciation**). Each word is coloured by score; hover over
a word to see its expected phonemes. You can also upload a WAV file.
The first time, allow the browser to use your microphone.

### Command line

Activate the venv first (`.\.venv\Scripts\Activate.ps1`), then:

```powershell
python pronounce.py                                   # practise built-in sentences
python pronounce.py "The weather is nice today"       # practise your own sentence
python pronounce.py --file recording.wav "The weather is nice today"
python pronounce.py --list-devices                    # show microphones
python pronounce.py --device 1                        # use a specific microphone
python pronounce.py --save                            # keep each take as take_N.wav
```

Flow: press **Enter**, speak, press **Enter** again. You'll then see the
result and can choose **r**etry, **n**ext, **c**ustom sentence or **q**uit.

### Scoring

Every attempt gets a grade:

| Grade | Score | Verdict | Meaning |
|---|---|---|---|
| A | 90+ | Excellent! | Clear, native-like; almost every sound recognised. |
| B | 75+ | Good | Easy to understand; a few sounds slightly off. |
| C | 55+ | Needs some work | Understandable, but several sounds wrong or missing. |
| D | 0+ | Try again | Hard to understand; many sounds wrong or missing. |

The bands are defined in `GRADES` in `scoring.py`; edit them there.

The first run downloads the model (~1.2 GB) into your Hugging Face cache.

## 3. Example output

```
  Expected: /ð ə w ɛ ð ɚ ɪ z n aɪ s t ə d eɪ/
  Heard:    /d ə w ɛ d ɚ ɪ z n aɪ s t ə d eɪ/

  Overall score: 87/100  Good

  Per word:
    The             [#####.....]  50%  /ð ə/
    weather         [########..]  80%  /w ɛ ð ɚ/
    is              [##########] 100%  /ɪ z/
    nice            [##########] 100%  /n aɪ s/
    today           [##########] 100%  /t ə d eɪ/

  Details:
    in 'The': said /d/ instead of /ð/
    in 'weather': said /d/ instead of /ð/
```

## 4. Troubleshooting

| Problem | Fix |
|---|---|
| `espeak not installed on your system` | Install eSpeak NG (step 1a) or set `PHONEMIZER_ESPEAK_LIBRARY`. |
| "recording was too short or too quiet" | Speak closer to the mic, check Windows Sound settings > Input level, or pick another `--device`. |
| Wrong microphone used | `python pronounce.py --list-devices`, then `--device <index>`. |
| Microphone access denied | Windows Settings > Privacy & security > Microphone > allow desktop apps. |
| `--file` with a non-16 kHz WAV fails | `pip install librosa` (used only for resampling). |

## Notes / limitations
- Expected pronunciation is US English (`en-us`) from eSpeak; change
  `language=` in `expected_phones_per_word` for other accents (e.g. `en-gb`).
- Stress and vowel-length marks are ignored when comparing.
- The score is a similarity ratio between phoneme sequences, a good practice
  signal, not a certified assessment.
