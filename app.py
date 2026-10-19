"""Web UI for the pronunciation checker.

Run:  python app.py   then open http://127.0.0.1:7860 in your browser.
"""
import html

import gradio as gr
import numpy as np

from phonemes import explain, lookup, respell
from pronounce import PRACTICE_SENTENCES, SAMPLE_RATE, analyze, load_model, verdict

PROC, MODEL = load_model()


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
    if score >= 90:
        return "#16a34a"
    if score >= 75:
        return "#65a30d"
    if score >= 55:
        return "#d97706"
    return "#dc2626"


def render(r):
    score = r["score"]
    c = color(score)
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
  <div class="pc-verdict" style="color:{c}">{verdict(score)}</div>
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


def check(audio, sentence):
    sentence = (sentence or "").strip()
    if not sentence:
        return "<p class='pc-msg'>Type or pick a sentence first.</p>"
    if audio is None:
        return "<p class='pc-msg'>Record yourself first (click the microphone).</p>"
    r = analyze(PROC, MODEL, to_mono_16k(audio), sentence)
    if r is None:
        return "<p class='pc-msg'>Didn't catch that - the recording was too short or too quiet.</p>"
    return render(r)


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

    btn.click(check, [audio, sentence], result)
    audio.stop_recording(check, [audio, sentence], result)  # auto-check when recording stops

if __name__ == "__main__":
    demo.launch(inbrowser=True, css=CSS)
