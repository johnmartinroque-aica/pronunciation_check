"""Live pronunciation checker: speak into the microphone, get a phoneme-level score.

Usage:
    python pronounce.py                       # practice the built-in sentences
    python pronounce.py "The weather is nice today"
    python pronounce.py --file recording.wav "The weather is nice today"
    python pronounce.py --list-devices
"""
import argparse
import os
import queue
import sys
from difflib import SequenceMatcher

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000
MODEL_ID = "facebook/wav2vec2-lv-60-espeak-cv-ft"

PRACTICE_SENTENCES = [
    "Rock the lock, then lock the rock.",
    "The clown wore a crown in the crowd.",
    "I bet the vet will be back by seven.",
    "Curb the curve before the next curb.",
    "She will sip her soup on the ship.",
    "Sue lost one shoe, so Sue bought a new shoe.",
    "A bug bit the boy, the boy beat the bug.",
    "I think the ship will sink, I think.",
    "Though the dough won't thaw, to the oven it goes.",
    "Show the proof to prove that you have proof.",
    "Rory rented what Larry lent.",
    "Frame the flame before the flame flickers.",
    "Vote for the boat, then boat to the vote.",
    "The rebels revel by the river.",
    "See the water seep near the sleeping sheep.",
    "The shy girl let out a big sad sigh.",
    "The sheep will slip, then the sheep will sleep.",
    "The hen then ran out of the den.",
    "Watch the sun rise as you eat rice.",
    "The dog dashed down the dock.",
]

# On Windows, phonemizer needs to be told where the eSpeak NG library lives.
if sys.platform == "win32" and "PHONEMIZER_ESPEAK_LIBRARY" not in os.environ:
    _dll = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"
    if os.path.exists(_dll):
        os.environ["PHONEMIZER_ESPEAK_LIBRARY"] = _dll

import torch  # noqa: E402
from phonemizer import phonemize  # noqa: E402
from phonemizer.separator import Separator  # noqa: E402
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor  # noqa: E402

from phonemes import explain, respell  # noqa: E402
from scoring import grade  # noqa: E402

# Marks that differ between the model output and espeak but don't change
# whether a sound was pronounced correctly.
_STRIP = str.maketrans("", "", "ˈˌːˑ‿")


def normalize(phone):
    return phone.translate(_STRIP)


def load_model():
    print("Loading model (first run downloads ~1.2 GB)...")
    proc = Wav2Vec2Processor.from_pretrained(MODEL_ID)
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID)
    model.eval()
    return proc, model


def record_from_mic(device=None):
    """Record until the user presses Enter. Returns float32 mono audio at 16 kHz."""
    q = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        q.put(indata.copy())

    input("Press Enter and start speaking...")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        device=device, callback=callback):
        input("  Recording... press Enter when done.")
    chunks = []
    while not q.empty():
        chunks.append(q.get())
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks)[:, 0]


def trim_silence(audio, threshold=0.01, pad=0.2):
    """Cut leading/trailing silence so the model doesn't hallucinate on noise."""
    loud = np.where(np.abs(audio) > threshold)[0]
    if len(loud) == 0:
        return audio
    p = int(pad * SAMPLE_RATE)
    return audio[max(0, loud[0] - p): loud[-1] + p]


def load_wav(path):
    audio, sr = sf.read(path, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        import librosa  # only needed for resampling files
        audio = librosa.resample(audio, orig_sr=sr, target_sr=SAMPLE_RATE)
    return audio


def recognize_phones(proc, model, audio):
    inputs = proc(audio, sampling_rate=SAMPLE_RATE, return_tensors="pt")
    with torch.no_grad():
        ids = model(**inputs).logits.argmax(-1)
    return [normalize(p) for p in proc.batch_decode(ids)[0].split() if normalize(p)]


def expected_phones_per_word(text):
    """Return [(word, [phones...]), ...] using espeak."""
    words = text.split()
    phonemized = phonemize(words, language="en-us", backend="espeak",
                           separator=Separator(phone=" ", word="", syllable=""),
                           strip=True, with_stress=False, njobs=1)
    result = []
    for word, ph in zip(words, phonemized):
        phones = [normalize(p) for p in ph.split() if normalize(p)]
        result.append((word.strip(".,!?;:\"'"), phones))
    return result


def analyze(proc, model, audio, text):
    """Score audio against text. Returns a dict, or None if the audio is unusable."""
    audio = trim_silence(audio)
    if len(audio) < SAMPLE_RATE * 0.3:
        return None

    spoken = recognize_phones(proc, model, audio)
    words = expected_phones_per_word(text)

    expected, owner = [], []  # owner[i] = index of the word that phone i belongs to
    for wi, (_, phones) in enumerate(words):
        expected.extend(phones)
        owner.extend([wi] * len(phones))

    sm = SequenceMatcher(None, expected, spoken, autojunk=False)
    correct = [False] * len(expected)
    issues = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for i in range(i1, i2):
                correct[i] = True
        else:
            word = words[owner[min(i1, len(owner) - 1)]][0] if owner else "?"
            issues.append((op, word, expected[i1:i2], spoken[j1:j2]))

    word_scores = []
    for wi, (word, phones) in enumerate(words):
        idx = [i for i, o in enumerate(owner) if o == wi]
        ws = 100 * sum(correct[i] for i in idx) / len(idx) if idx else 100
        word_scores.append((word, phones, ws))

    return {
        "score": sm.ratio() * 100,
        "expected": expected,
        "spoken": spoken,
        "words": word_scores,
        "issues": issues,
    }


def assess(proc, model, audio, text):
    r = analyze(proc, model, audio, text)
    if r is None:
        print("  Didn't catch that - recording was too short or too quiet.\n")
        return None

    score = r["score"]
    g = grade(score)
    print(f"\n  Expected: {respell(r['expected'])}")
    print(f"  Heard:    {respell(r['spoken'])}")
    print(f"\n  Overall score: {score:.0f}/100  Grade {g.letter} - {g.verdict}\n")

    print("  Per word:")
    for word, phones, ws in r["words"]:
        bar = "#" * round(ws / 10) + "." * (10 - round(ws / 10))
        print(f"    {word:<15} [{bar}] {ws:3.0f}%  sounds like: {respell(phones)}")

    if r["issues"]:
        print("\n  What to fix:")
        for op, word, exp, got in r["issues"]:
            for msg, tip in explain(exp, got):
                print(f"    In '{word}': you {msg}")
                if tip:
                    print(f"      Tip: {tip}")
    print()
    return r


def verdict(score):
    return grade(score).verdict


def main():
    ap = argparse.ArgumentParser(description="Microphone pronunciation checker")
    ap.add_argument("text", nargs="?", help="sentence to practise (default: built-in list)")
    ap.add_argument("--file", help="assess a WAV file instead of the microphone")
    ap.add_argument("--device", type=int, help="input device index (see --list-devices)")
    ap.add_argument("--save", action="store_true", help="save each take as take_N.wav")
    ap.add_argument("--list-devices", action="store_true")
    args = ap.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    proc, model = load_model()

    if args.file:
        text = args.text or PRACTICE_SENTENCES[0]
        assess(proc, model, load_wav(args.file), text)
        return

    sentences = [args.text] if args.text else PRACTICE_SENTENCES
    take = 0
    for sentence in sentences:
        while True:
            print("=" * 60)
            print(f'  Say: "{sentence}"')
            print("=" * 60)
            audio = record_from_mic(args.device)
            take += 1
            if args.save:
                sf.write(f"take_{take}.wav", audio, SAMPLE_RATE)
            assess(proc, model, audio, sentence)
            choice = input("[r]etry, [n]ext, [c]ustom sentence, [q]uit? ").strip().lower()
            if choice == "r":
                continue
            if choice == "c":
                sentence = input("Type your sentence: ").strip() or sentence
                continue
            if choice == "q":
                return
            break
    print("Done - nice practice!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")
