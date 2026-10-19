"""Plain-English descriptions of the IPA phoneme symbols used by the model."""

# symbol -> (sounds like, example word)
SOUNDS = {
    # vowels
    "i": ("ee", "see"), "ɪ": ("i", "sit"), "eɪ": ("ay", "day"), "e": ("ay", "day"),
    "ɛ": ("e", "bed"), "æ": ("a", "cat"), "a": ("a", "cat"), "ɑ": ("ah", "father"),
    "ɒ": ("o", "hot"), "ɔ": ("aw", "law"), "oʊ": ("oh", "go"), "o": ("oh", "go"),
    "ʊ": ("u", "book"), "u": ("oo", "food"), "ʌ": ("uh", "cup"),
    "ə": ("uh", "about (weak)"), "ɐ": ("uh", "sofa (weak)"), "ᵻ": ("i", "roses (weak)"),
    "ɚ": ("er", "butter (weak)"), "ɝ": ("ur", "bird"), "ɜ": ("ur", "bird"),
    "aɪ": ("eye", "my"), "aʊ": ("ow", "now"), "ɔɪ": ("oy", "boy"),
    "iə": ("eer", "near"), "ɪɹ": ("eer", "near"), "ɛɹ": ("air", "hair"),
    "ɑɹ": ("ar", "car"), "ɔɹ": ("or", "for"), "oːɹ": ("or", "for"), "ʊɹ": ("oor", "tour"),
    "aɪɚ": ("ire", "fire"), "aɪə": ("ire", "fire"), "aʊɚ": ("our", "hour"),
    # consonants
    "p": ("p", "pen"), "b": ("b", "bad"), "t": ("t", "tea"), "d": ("d", "dog"),
    "k": ("k", "cat"), "g": ("g", "go"), "ɡ": ("g", "go"),
    "f": ("f", "fish"), "v": ("v", "van"),
    "θ": ("th", "think (no voice)"), "ð": ("th", "this (buzzing)"),
    "s": ("s", "sun"), "z": ("z", "zoo"), "ʃ": ("sh", "she"), "ʒ": ("zh", "measure"),
    "h": ("h", "hat"), "tʃ": ("ch", "chair"), "dʒ": ("j", "jam"),
    "m": ("m", "man"), "n": ("n", "no"), "ŋ": ("ng", "sing"),
    "l": ("l", "leg"), "ɹ": ("r", "red"), "r": ("r", "red"),
    "w": ("w", "wet"), "j": ("y", "yes"),
    "ɾ": ("t", "butter (quick tap)"), "ʔ": ("(stop)", "uh-oh"),
    "n̩": ("n", "button"), "l̩": ("l", "bottle"), "m̩": ("m", "rhythm"),
    # non-English sounds a learner's accent may produce
    "ɫ": ("dark l", "full"), "ʁ": ("throat r", "French 'rouge'"), "ʀ": ("throat r", "French 'rouge'"),
    "χ": ("kh", "German 'Bach'"), "x": ("kh", "Scottish 'loch'"), "ɣ": ("soft g", "Spanish 'lago'"),
    "β": ("soft b", "Spanish 'saber'"), "ɸ": ("soft f", "Japanese 'fuji'"), "ç": ("hy", "German 'ich'"),
    "ʋ": ("v/w", "Hindi 'vah'"), "ɲ": ("ny", "Spanish 'niño'"), "ʎ": ("ly", "Italian 'figlio'"),
    "y": ("ü", "French 'tu'"), "ø": ("eu", "French 'peu'"), "œ": ("eu", "French 'peur'"),
    "ɨ": ("i (middle)", "Polish 'ryba'"), "ʉ": ("ew", "Swedish 'hus'"), "ɯ": ("u (unrounded)", "Korean 'eu'"),
    "ɟ": ("gy", "Hungarian 'gyár'"), "c": ("ky", "Hungarian 'tyúk'"), "ts": ("ts", "cats"),
}

# Accent marks that only modify a base letter (nasal, palatal, aspirated, ...)
_MODIFIERS = set("ʰʲˤᵝ̪̞̝̩̃̊0123456789")

# How to make the expected sound
TIPS = {
    "ð": "Put your tongue tip lightly between your teeth and let it buzz (voice on).",
    "θ": "Put your tongue tip between your teeth and blow air out, no voice.",
    "ɹ": "Pull your tongue back without touching the roof of your mouth; round your lips a little.",
    "l": "Touch your tongue tip to the ridge just behind your top teeth.",
    "v": "Rest your top teeth on your bottom lip and buzz.",
    "f": "Rest your top teeth on your bottom lip and blow air.",
    "w": "Round your lips tightly, then open them.",
    "z": "Same as 's' but with your voice on (a buzz).",
    "ʃ": "Round your lips and pull your tongue back: 'shh'.",
    "ʒ": "Like 'sh' but with your voice on, as in 'measure'.",
    "tʃ": "Start with 't' and release into 'sh': 'ch'.",
    "dʒ": "Start with 'd' and release into 'zh': 'j'.",
    "ŋ": "Raise the back of your tongue to the roof of your mouth; don't add a 'g' at the end.",
    "h": "Just breathe out softly before the vowel.",
    "i": "Long sound: smile and stretch it, 'ee'.",
    "ɪ": "Short, relaxed sound; don't stretch it into 'ee'.",
    "æ": "Drop your jaw and open your mouth wide, as in 'cat'.",
    "ɛ": "Mouth half open, short sound, as in 'bed'.",
    "ʌ": "Short, relaxed 'uh' from the middle of your mouth.",
    "ə": "A very short, weak, relaxed 'uh'; don't open your mouth wide.",
    "ɚ": "A short, weak 'er' with your tongue pulled back.",
    "ɝ": "Hold a strong 'er' with your tongue pulled back.",
    "u": "Long sound: round your lips tightly, 'oo'.",
    "ʊ": "Short sound with relaxed, slightly rounded lips, as in 'book'.",
    "eɪ": "Glide from 'e' to 'ee': 'ay'.",
    "oʊ": "Start with 'o' and round your lips into 'oo': 'oh'.",
    "aɪ": "Glide from 'ah' to 'ee': 'eye'.",
    "aʊ": "Glide from 'ah' to 'oo': 'ow'.",
    "ɔɪ": "Glide from 'aw' to 'ee': 'oy'.",
}

# Specific advice for common (expected, said) mix-ups
PAIR_TIPS = {
    ("ð", "d"): "You tapped a hard 'd'. Put your tongue between your teeth and let air buzz out; don't tap.",
    ("ð", "z"): "Move your tongue forward, between your teeth, instead of behind them.",
    ("θ", "t"): "You tapped a 't'. Put your tongue between your teeth and blow; don't tap.",
    ("θ", "s"): "Move your tongue forward, between your teeth, instead of behind them.",
    ("θ", "f"): "Use your tongue between your teeth, not your lip.",
    ("v", "b"): "Don't close your lips; rest your top teeth on your bottom lip.",
    ("b", "v"): "Close both lips together, then release.",
    ("v", "w"): "Use your top teeth on your bottom lip, not rounded lips.",
    ("w", "v"): "Round your lips; don't touch your teeth to your lip.",
    ("ɹ", "l"): "Don't touch the roof of your mouth; pull your tongue back instead.",
    ("l", "ɹ"): "Touch your tongue tip to the ridge behind your top teeth.",
    ("i", "ɪ"): "Make it longer and smile more: 'ee'.",
    ("ɪ", "i"): "Make it shorter and more relaxed; don't stretch it.",
    ("æ", "ɛ"): "Open your mouth wider and drop your jaw.",
    ("ɛ", "æ"): "Don't open your mouth so wide.",
    ("ʃ", "s"): "Round your lips and pull your tongue back a little.",
    ("s", "ʃ"): "Spread your lips and keep your tongue forward.",
    ("z", "s"): "Turn your voice on: it should buzz.",
    ("u", "ʊ"): "Make it longer and round your lips tighter.",
    ("ʊ", "u"): "Make it shorter and more relaxed.",
    ("ə", "ɑ"): "Too open. This is a short, weak 'uh'; keep your mouth relaxed.",
    ("ə", "æ"): "Too open. This is a short, weak 'uh'; keep your mouth relaxed.",
}


def lookup(phone):
    """Return (sounds like, example) for a phone, splitting unknown combos into parts."""
    if phone in SOUNDS:
        return SOUNDS[phone]
    base = "".join(ch for ch in phone if ch not in _MODIFIERS)
    if base != phone and base:
        return lookup(base)
    parts, i = [], 0
    while i < len(phone):
        for n in (3, 2, 1):
            if phone[i:i + n] in SOUNDS:
                parts.append(SOUNDS[phone[i:i + n]][0])
                i += n
                break
        else:
            parts.append(phone[i])
            i += 1
    return "".join(parts), ""


def respell(phones):
    """['ð', 'ə'] -> 'th-uh'"""
    return "-".join(lookup(p)[0] for p in phones)


def describe(phone):
    """'ð' -> '"th" (as in this (buzzing))'"""
    label, example = lookup(phone)
    return f'"{label}" (as in {example})' if example else f'"{label}"'


def explain(expected, said):
    """Turn one mismatch into [(message, tip), ...] in plain English."""
    if not said:
        return [(f"missed the {describe(e)} sound", TIPS.get(e, "")) for e in expected]
    if not expected:
        return [(f"added an extra {describe(s)} sound", "") for s in said]
    if len(expected) == len(said):
        return [
            (f"said {describe(s)} instead of {describe(e)}",
             PAIR_TIPS.get((e, s)) or TIPS.get(e, ""))
            for e, s in zip(expected, said) if e != s
        ]
    tip = next((TIPS[e] for e in expected if e not in said and e in TIPS), "")
    return [(f'said "{respell(said)}" instead of "{respell(expected)}"', tip)]
