"""Web UI for the pronunciation checker.

Run:  python app.py   then open http://127.0.0.1:7860 in your browser.
"""
import html

import gradio as gr
import numpy as np

from phonemes import explain, lookup, respell
from pronounce import PRACTICE_SENTENCES, SAMPLE_RATE, analyze, load_model
from scoring import GRADES, ScoreBook, grade

PROC, MODEL = load_model()
BOOK = ScoreBook()
_last_take = None  # (sentence, audio hash) so Check after auto-check isn't counted twice


def to_mono_16k(audio):
    """Gradio gives (sample_rate, int16/float array); convert to float32 mono 16 kHz."""
    sr, data = audio
    data = np.asarray(data)
    if data.dtype.kind == "i":
        data = data.astype(np.float32) / np.iinfo(data.dtype).max
    else:
        data = data.astype(np.float32)
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != SAMPLE_RATE:
        n = int(len(data) * SAMPLE_RATE / sr)
        data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data)
    return data.astype(np.float32)


def color(score):
    return grade(score).color


def render(r, new_best=False):
    score = r["score"]
    g = grade(score)
    c = g.color
    words = "".join(
        f'<span class="pc-word" style="border-color:{color(ws)};color:{color(ws)}">{html.escape(w)}'
        f'<em>{html.escape(respell(ph))}</em><small>{ws:.0f}%</small></span>'
        for w, ph, ws in r["words"]
    )

    rows = []
    for op, word, exp, got in r["issues"]:
        for msg, tip in explain(exp, got):
            tip_html = f'<div class="pc-tip">💡 {html.escape(tip)}</div>' if tip else ""
            rows.append(f"<li>In <b>{html.escape(word)}</b>: you {html.escape(msg)}{tip_html}</li>")
    details = (f"<h4>What to fix</h4><ul>{''.join(rows)}</ul>" if rows
               else "<p>No mistakes detected - great job!</p>")

    seen = list(dict.fromkeys(r["expected"] + r["spoken"]))
    guide = "".join(
        f"<tr><td>{html.escape(p)}</td><td>{html.escape(lookup(p)[0])}</td>"
        f"<td>{html.escape(lookup(p)[1])}</td></tr>"
        for p in seen
    )

    return f"""
<div class="pc-result">
  <div class="pc-score" style="color:{c}">{score:.0f}<span>/100</span></div>
  <div class="pc-verdict" style="color:{c}">Grade {g.letter} - {g.verdict}</div>
  {'<div class="pc-best">🏆 New personal best!</div>' if new_best else ''}
  <div class="pc-words">{words}</div>
  <table class="pc-phones">
    <tr><th>Should sound like</th><td>{html.escape(respell(r["expected"]))}</td></tr>
    <tr><th>You said</th><td>{html.escape(respell(r["spoken"]))}</td></tr>
  </table>
  {details}
  <details class="pc-guide"><summary>Sound guide (phonetic symbols)</summary>
    <table><tr><th>Symbol</th><th>Sounds like</th><th>Example</th></tr>{guide}</table>
  </details>
</div>"""


def render_scores():
    scale = "".join(
        f'<tr><td style="color:{g.color}"><b>{g.letter}</b></td><td>{g.min}+</td>'
        f"<td>{html.escape(g.verdict)}</td><td>{html.escape(g.meaning)}</td></tr>"
        for g in GRADES
    )
    scale = (f'<h4>Grading scale</h4><table class="pc-table"><tr><th>Grade</th><th>Score</th>'
             f"<th>Verdict</th><th>Meaning</th></tr>{scale}</table>")
    rows = BOOK.table()
    if not rows:
        return "<p class='pc-msg'>No scores yet - your attempts will be listed here.</p>" + scale

    body = "".join(
        f"<tr><td class='pc-sent'>{html.escape(row['sentence'])}</td><td>{row['tries']}</td>"
        f"<td style='color:{color(row['best'])}'><b>{row['best']:.0f}</b> {grade(row['best']).letter}</td>"
        f"<td>{row['average']:.0f}</td><td>{row['last']:.0f}</td>"
        f"<td>{format(row['trend'], '+.0f') if row['tries'] > 1 else '-'}</td></tr>"
        for row in rows
    )
    t = BOOK.totals()
    weak = BOOK.weak_words()
    weak_html = ("<p><b>Words to practise:</b> " + ", ".join(
        f"<span style='color:{color(s)}'>{html.escape(w)} ({s:.0f}%)</span>" for w, s in weak) + "</p>"
        if weak else "")
    return f"""
<table class="pc-table">
  <tr><th>Sentence</th><th>Tries</th><th>Best</th><th>Average</th><th>Last</th><th>Trend</th></tr>
  {body}
</table>
<p><b>Overall:</b> {t['tries']} attempts, average {t['average']:.0f}, best {t['best']:.0f}</p>
{weak_html}{scale}"""


def check(audio, sentence):
    global _last_take
    sentence = (sentence or "").strip()
    if not sentence:
        return "<p class='pc-msg'>Type or pick a sentence first.</p>", render_scores()
    if audio is None:
        return "<p class='pc-msg'>Record yourself first (click the microphone).</p>", render_scores()
    data = to_mono_16k(audio)
    r = analyze(PROC, MODEL, data, sentence)
    if r is None:
        return ("<p class='pc-msg'>Didn't catch that - the recording was too short or too quiet.</p>",
                render_scores())
    take = (sentence, hash(data.tobytes()))
    new_best = False
    if take != _last_take:
        _last_take = take
        new_best = BOOK.add(sentence, r)
    return render(r, new_best), render_scores()


def reset_scores():
    BOOK.reset()
    return render_scores()


CSS = """
.pc-result { text-align:center; padding:8px; }
.pc-score { font-size:64px; font-weight:700; line-height:1; }
.pc-score span { font-size:24px; opacity:.6; }
.pc-verdict { font-size:20px; font-weight:600; margin:4px 0 16px; }
.pc-words { display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-bottom:16px; }
.pc-word { border:2px solid; border-radius:10px; padding:6px 12px; font-size:20px; font-weight:600;
           display:inline-flex; flex-direction:column; align-items:center; cursor:help; }
.pc-word em { font-size:13px; font-style:normal; font-weight:400; opacity:.85; }
.pc-word small { font-size:12px; font-weight:400; }
.pc-phones { margin:0 auto 12px; font-size:16px; border:none !important; }
.pc-phones th, .pc-phones td { border:none !important; padding:4px 8px; }
.pc-phones th { text-align:right; opacity:.7; font-weight:400; }
.pc-phones td { text-align:left; font-weight:600; }
.pc-result ul { text-align:left; display:inline-block; max-width:520px; }
.pc-result li { margin-bottom:10px; }
.pc-tip { font-size:14px; opacity:.85; margin-top:2px; }
.pc-guide { margin-top:16px; text-align:left; display:inline-block; }
.pc-guide summary { cursor:pointer; opacity:.8; }
.pc-guide table { margin-top:8px; }
.pc-guide td:first-child { font-size:18px; text-align:center; }
.pc-msg { text-align:center; padding:24px; opacity:.8; }
.pc-best { font-size:18px; font-weight:600; margin:-8px 0 16px; }
.pc-table { width:100%; border-collapse:collapse; margin-bottom:12px; }
.pc-table th, .pc-table td { padding:6px 10px; text-align:center; }
.pc-table th { opacity:.7; font-weight:600; }
.pc-table td.pc-sent { text-align:left; }
"""

with gr.Blocks(title="Pronunciation Check") as demo:
    gr.Markdown("# 🎤 Pronunciation Check\nPick or type a sentence, record yourself, then press **Check**.")
    with gr.Row():
        with gr.Column():
            sentence = gr.Dropdown(PRACTICE_SENTENCES, value=PRACTICE_SENTENCES[0],
                                   allow_custom_value=True, label="Sentence (pick or type your own)")
            audio = gr.Audio(sources=["microphone", "upload"], type="numpy",
                             label="Your recording")
            btn = gr.Button("Check pronunciation", variant="primary")
        with gr.Column():
            result = gr.HTML("<p class='pc-msg'>Your results will appear here.</p>")
    with gr.Accordion("📊 Score table", open=True):
        scores = gr.HTML(render_scores())
        reset = gr.Button("Reset score history", size="sm", variant="stop")

    btn.click(check, [audio, sentence], [result, scores])
    audio.stop_recording(check, [audio, sentence], [result, scores])  # auto-check when recording stops
    reset.click(reset_scores, None, scores)
    demo.load(render_scores, None, scores)  # fresh table on page reload

if __name__ == "__main__":
    demo.launch(inbrowser=True, css=CSS)
