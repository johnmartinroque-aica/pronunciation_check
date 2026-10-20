"use client";

/**
 * ============================================================================
 * Pronunciation server client (records the mic, sends audio, returns a score)
 * ============================================================================
 *
 * NOTES FOR THE AI / DEVELOPER INTEGRATING THIS FILE
 * --------------------------------------------------
 * This file talks to a separate Python server (FastAPI, `server.py` in the
 * user's `pronunciation_check` project). That server runs a wav2vec2 phoneme
 * model locally and scores pronunciation at the PHONEME level, which is much
 * stricter and more useful than the browser Web Speech API (which only says
 * which word it guessed). It also works in Firefox/Safari, unlike Web Speech.
 *
 * Suggested location: `components/training/pronunciationServer.ts`
 * (next to `useSentenceCheck.ts` / `MinimalPairTrainer.tsx`).
 *
 * Environment variables (put in `.env.local`, then restart `next dev`):
 *   NEXT_PUBLIC_PRONUNCIATION_API_URL=http://127.0.0.1:8000
 *   NEXT_PUBLIC_PRONUNCIATION_API_KEY=        (optional, only if the server
 *                                              sets API_KEY; note that
 *                                              NEXT_PUBLIC_ values are visible
 *                                              in the browser, so this is a
 *                                              light gate, not a real secret)
 *
 * SERVER API
 *   POST {API_URL}/analyze   multipart/form-data
 *     audio: WAV file (this file converts recordings to 16 kHz mono WAV)
 *     text:  the word or sentence the user was asked to say
 *   -> JSON, see `PronunciationResult` below.
 *   GET {API_URL}/health -> { ok: true }   (use to check the server is up)
 *
 * WHAT THIS FILE EXPORTS
 *   - analyzePronunciation(blob, text)   low-level: send any audio Blob
 *   - startRecording()                   low-level: mic -> Blob
 *   - useServerPronunciationCheck(cb)    React hook, a drop-in replacement for
 *                                        `useSentenceCheck` in MinimalPairTrainer
 *
 * HOW TO PLUG IT INTO MinimalPairTrainer.tsx
 *   The hook has the same shape as `useSentenceCheck`:
 *     const check = useServerPronunciationCheck(handleResult);
 *     check.start(text)          -> call in the countdown's `begin` callback
 *     check.finishListening()    -> call in the countdown's `endAnswer` callback
 *     check.isListening          -> true while recording (use for isBusy / isChecking)
 *     check.isAnalyzing          -> true while waiting for the server
 *
 *   Step 4 (tongue twister): replace `useSentenceCheck(handleSentenceResult)`
 *   with `useServerPronunciationCheck(handleSentenceResult)` and add a case
 *   for `"serverError"` in `handleSentenceResult`. The "correct"/"incorrect"
 *   outcomes also carry `result` so the UI can show the score, per-word
 *   scores (`result.words`) and tips (`result.issues`).
 *
 *   Step 3 (single word): replace `startAiPronunciationCheck` with a second
 *   instance of the hook: `start(word)` in `begin`, `finishListening()` in
 *   `endAnswer`. The 3-second answer window is enough for one word.
 *
 *   Include `check.isAnalyzing` in `isBusy` so buttons stay disabled while
 *   the server is scoring. Keep the existing `stopPronunciationCheckEvent`
 *   pattern if other cards should cancel this one: call `check.cancel()`
 *   from that event listener.
 *
 *   Pass/fail rule: by default "correct" means every word scored 100 (the
 *   same "100%" rule the tongue twister uses now). Pass `{ passScore: 80 }`
 *   as the hook's second argument to be more forgiving.
 *
 * DEPLOYMENT NOTE
 *   If the website is deployed on HTTPS, the server must also be reachable
 *   over HTTPS (browsers block http:// calls from https:// pages, except to
 *   localhost). Also set ALLOWED_ORIGINS on the server to the site's origin.
 * ============================================================================
 */

import { useEffect, useRef, useState } from "react";

const API_URL = (
  process.env.NEXT_PUBLIC_PRONUNCIATION_API_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");
const API_KEY = process.env.NEXT_PUBLIC_PRONUNCIATION_API_KEY;
const TARGET_SAMPLE_RATE = 16000;

// ---------------------------------------------------------------------------
// Response types (mirror server.py's /analyze JSON)
// ---------------------------------------------------------------------------

export type PronunciationWord = {
  word: string;
  score: number; // 0-100, share of this word's sounds pronounced correctly
  phonemes: string[]; // IPA symbols the word should have
  soundsLike: string; // readable respelling, e.g. "r-AH-k"
};

export type PronunciationIssue = {
  word: string;
  message: string; // e.g. 'you said "l" instead of "r"'
  tip: string | null; // how to fix it, when available
};

export type PronunciationResult =
  | {
      ok: true;
      score: number; // 0-100 overall
      grade: { letter: string; verdict: string; color: string };
      allWordsCorrect: boolean;
      expected: { phonemes: string[]; soundsLike: string };
      heard: { phonemes: string[]; soundsLike: string };
      words: PronunciationWord[];
      issues: PronunciationIssue[];
    }
  | {
      ok: false; // recording too short or too quiet
      error: "too_short_or_quiet";
      message: string;
    };

// ---------------------------------------------------------------------------
// Low level: send audio
// ---------------------------------------------------------------------------

/** Sends a recording to the server and returns its analysis. Throws on HTTP/network errors. */
export async function analyzePronunciation(
  audio: Blob,
  text: string,
  signal?: AbortSignal,
): Promise<PronunciationResult> {
  // Convert to WAV so the server doesn't need ffmpeg for browser formats.
  const wav = audio.type === "audio/wav" ? audio : await blobToWav16k(audio);

  const form = new FormData();
  form.append("audio", wav, "recording.wav");
  form.append("text", text);

  const response = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    body: form,
    headers: API_KEY ? { "X-API-Key": API_KEY } : undefined,
    signal,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // body wasn't JSON
    }
    throw new Error(`Pronunciation server error ${response.status}: ${detail}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Low level: record the mic
// ---------------------------------------------------------------------------

export type Recording = {
  /** Stops recording and resolves with the audio. */
  stop: () => Promise<Blob>;
  /** Stops recording and throws the audio away. */
  cancel: () => void;
};

/** Opens the mic and starts recording. Throws if the mic is unavailable or denied. */
export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({
    // Browser-side cleanup; noiseSuppression helps with fans/hum.
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  });
  const recorder = new MediaRecorder(stream);
  const chunks: Blob[] = [];

  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  };

  const releaseMic = () => stream.getTracks().forEach((track) => track.stop());

  recorder.start();

  return {
    stop: () =>
      new Promise<Blob>((resolve) => {
        const finish = () => {
          releaseMic();
          resolve(new Blob(chunks, { type: recorder.mimeType }));
        };
        if (recorder.state === "inactive") {
          finish();
        } else {
          recorder.onstop = finish;
          recorder.stop();
        }
      }),
    cancel: () => {
      recorder.onstop = null;
      if (recorder.state !== "inactive") recorder.stop();
      releaseMic();
    },
  };
}

/** Decodes any browser-playable audio Blob and re-encodes it as 16 kHz mono 16-bit WAV. */
export async function blobToWav16k(blob: Blob): Promise<Blob> {
  const AudioContextConstructor =
    window.AudioContext ??
    (window as unknown as { webkitAudioContext: typeof AudioContext })
      .webkitAudioContext;
  const context = new AudioContextConstructor();
  let decoded: AudioBuffer;
  try {
    decoded = await context.decodeAudioData(await blob.arrayBuffer());
  } finally {
    void context.close();
  }

  // Resample + downmix to mono by rendering through an offline context.
  const length = Math.max(1, Math.ceil(decoded.duration * TARGET_SAMPLE_RATE));
  const offline = new OfflineAudioContext(1, length, TARGET_SAMPLE_RATE);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start();
  const samples = (await offline.startRendering()).getChannelData(0);

  return new Blob([encodeWav(samples, TARGET_SAMPLE_RATE)], {
    type: "audio/wav",
  });
}

function encodeWav(samples: Float32Array, sampleRate: number): ArrayBuffer {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);
  const writeText = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
  };

  writeText(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeText(8, "WAVE");
  writeText(12, "fmt ");
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeText(36, "data");
  view.setUint32(40, samples.length * 2, true);

  for (let i = 0; i < samples.length; i += 1) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return buffer;
}

// ---------------------------------------------------------------------------
// React hook (drop-in for useSentenceCheck)
// ---------------------------------------------------------------------------

export type ServerCheckOutcome =
  | { status: "listening" }
  | { status: "correct"; heardText: string; result: Extract<PronunciationResult, { ok: true }> }
  | { status: "incorrect"; heardText: string; result: Extract<PronunciationResult, { ok: true }> }
  | { status: "nothingHeard" }
  | { status: "unsupported" }
  | { status: "failedToStart" }
  | { status: "serverError"; message: string };

type Options = {
  /** If set, "correct" means score >= passScore. Default: every word must score 100. */
  passScore?: number;
};

export function useServerPronunciationCheck(
  onResult: (outcome: ServerCheckOutcome) => void,
  options: Options = {},
) {
  const [isListening, setIsListening] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const recordingRef = useRef<Promise<Recording> | null>(null);
  const textRef = useRef("");
  const runIdRef = useRef(0); // bumps on every start/cancel so stale async work is ignored
  const abortRef = useRef<AbortController | null>(null);
  const onResultRef = useRef(onResult);
  const optionsRef = useRef(options);

  useEffect(() => {
    onResultRef.current = onResult;
    optionsRef.current = options;
  });

  function cancel() {
    runIdRef.current += 1;
    abortRef.current?.abort();
    abortRef.current = null;
    recordingRef.current?.then((rec) => rec.cancel()).catch(() => {});
    recordingRef.current = null;
    setIsListening(false);
    setIsAnalyzing(false);
  }

  useEffect(() => cancel, []); // release the mic on unmount

  /** Opens the mic and starts recording `text`. */
  function start(text: string) {
    cancel();
    const runId = runIdRef.current;

    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onResultRef.current({ status: "unsupported" });
      return;
    }

    textRef.current = text;
    setIsListening(true);
    const recording = startRecording();
    recordingRef.current = recording;

    recording.then(
      () => {
        if (runIdRef.current === runId) onResultRef.current({ status: "listening" });
      },
      () => {
        if (runIdRef.current !== runId) return;
        recordingRef.current = null;
        setIsListening(false);
        onResultRef.current({ status: "failedToStart" });
      },
    );
  }

  /** Stops recording, sends it to the server, and reports the outcome. */
  async function finishListening() {
    const recordingPromise = recordingRef.current;
    if (!recordingPromise) return;

    const runId = runIdRef.current;
    recordingRef.current = null;
    setIsListening(false);
    setIsAnalyzing(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const blob = await (await recordingPromise).stop();
      const result = await analyzePronunciation(blob, textRef.current, controller.signal);
      if (runIdRef.current !== runId) return;

      if (!result.ok || result.heard.phonemes.length === 0) {
        onResultRef.current({ status: "nothingHeard" });
        return;
      }

      const { passScore } = optionsRef.current;
      const passed =
        passScore === undefined ? result.allWordsCorrect : result.score >= passScore;
      // The server returns sounds, not words; show the readable respelling.
      const heardText = result.heard.soundsLike;
      onResultRef.current(
        passed
          ? { status: "correct", heardText, result }
          : { status: "incorrect", heardText, result },
      );
    } catch (error) {
      if (runIdRef.current !== runId) return;
      onResultRef.current({
        status: "serverError",
        message: error instanceof Error ? error.message : String(error),
      });
    } finally {
      if (runIdRef.current === runId) {
        setIsAnalyzing(false);
        abortRef.current = null;
      }
    }
  }

  return { start, finishListening, cancel, isListening, isAnalyzing };
}
