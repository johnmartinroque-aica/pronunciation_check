"""Grading scale for pronunciation scores."""
from collections import namedtuple

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

