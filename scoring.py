"""Grading scale and a persistent score history (saved to scores.json)."""
import json
import os
from collections import namedtuple
from datetime import datetime

SCORES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scores.json")

Grade = namedtuple("Grade", "min letter verdict color meaning")

# Highest band first; a score gets the first band whose minimum it reaches.
GRADES = [
    Grade(90, "A", "Excellent!", "#16a34a", "Clear, native-like; almost every sound recognised."),
    Grade(75, "B", "Good", "#65a30d", "Easy to understand; a few sounds slightly off."),
    Grade(55, "C", "Needs some work", "#d97706", "Understandable, but several sounds wrong or missing."),
    Grade(0, "D", "Try again", "#dc2626", "Hard to understand; many sounds wrong or missing."),
]


def grade(score):
    return next(g for g in GRADES if score >= g.min)


class ScoreBook:
    """Every attempt, kept between runs so you can track progress."""

    def __init__(self, path=SCORES_FILE):
        self.path = path
        self.attempts = []
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    self.attempts = json.load(f)
            except (OSError, ValueError):
                self.attempts = []

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.attempts, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def add(self, sentence, result):
        """Record an analyze() result. Returns True if it's a new best for the sentence."""
        previous = self.scores(sentence)
        score = round(result["score"], 1)
        self.attempts.append({
            "time": datetime.now().isoformat(timespec="seconds"),
            "sentence": sentence,
            "score": score,
            "words": [[w, round(ws)] for w, _, ws in result["words"]],
        })
        self.save()
        return bool(previous) and score > max(previous)

    def reset(self):
        self.attempts = []
        if os.path.exists(self.path):
            os.remove(self.path)

    def scores(self, sentence):
        return [a["score"] for a in self.attempts if a["sentence"] == sentence]

    def table(self):
        """One row per sentence, in the order first practised."""
        rows = {}
        for a in self.attempts:
            rows.setdefault(a["sentence"], []).append(a["score"])
        return [{
            "sentence": s,
            "tries": len(sc),
            "best": max(sc),
            "average": sum(sc) / len(sc),
            "last": sc[-1],
            "trend": sc[-1] - sc[0],
        } for s, sc in rows.items()]

    def totals(self):
        sc = [a["score"] for a in self.attempts]
        if not sc:
            return None
        return {"tries": len(sc), "average": sum(sc) / len(sc), "best": max(sc)}

    def weak_words(self, n=5, below=90):
        """Words with the lowest average score across all attempts."""
        seen = {}
        for a in self.attempts:
            for w, ws in a["words"]:
                seen.setdefault(w.lower(), []).append(ws)
        avg = [(w, sum(s) / len(s)) for w, s in seen.items()]
        return sorted([x for x in avg if x[1] < below], key=lambda x: x[1])[:n]
