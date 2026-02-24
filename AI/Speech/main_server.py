import time
import threading
from fastapi import FastAPI
from fastapi.responses import JSONResponse

import os
import soundfile as sf
import numpy as np

import assemblyai as aai
from filler_nlp import detect_fillers_from_text

from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingEvents,
    StreamingParameters,
)

from api_secrets import API_KEY_ASSEMBLYAI

from pause_detector import PauseDetector
from wpm_tracker import WPMTracker
from pitch_analyzer import PitchAnalyzer
from audio_stream import AudioStream


# ---------------- CONFIG ----------------

SAMPLE_RATE = 16000

app = FastAPI(title="Speech Analysis System")

pause_detector = PauseDetector()
wpm_tracker = WPMTracker()
pitch_analyzer = PitchAnalyzer(SAMPLE_RATE)

# ---------------- AUDIO RECORDING ----------------

audio_writer = None
audio_file_path = "recordings/session_audio.wav"

# ---------------- SESSION STATE ----------------

state = {
    "running": False,
    "session_start": None,
    "wpm": 0,
    "last_pause": False,

    # live values
    "pitch": 0,
    "loudness": 0,

    # histories for final report
    "pitch_history": [],
    "loudness_history": [],

    "transcripts": [],
    "fillers": [],
    "pause_events": [],  # Track long pause timestamps for beep sound
    "speaking_active": False,  # Track if user is currently speaking (for beep control)
}

analysis_thread = None
client = None
audio_stream = None


# ---------------- AUDIO CALLBACK ----------------

def audio_callback(indata, frames, time_info, status):

    global audio_writer

    audio = indata.copy()
    flat = audio.flatten()

    # ✅ RECORD MIC
    if audio_writer:
        audio_writer.write(audio)

    # ---- pause detection ----
    pause_detected = pause_detector.process_audio(flat)
    
    # Track if user is currently speaking (for beep control)
    rms = np.sqrt(np.mean(flat ** 2))
    state["speaking_active"] = bool(rms >= pause_detector.silence_threshold)
    
    if pause_detected:
        state["last_pause"] = True
        # Track pause event with timestamp for beep sound
        pause_time = round(time.time() - state["session_start"], 2) if state["session_start"] else 0
        state["pause_events"].append({"timestamp": pause_time, "id": f"pause-{pause_time}"})
        print(f"🔔 Long pause detected at {pause_time}s")

    # ---- pitch + loudness ----
    loud = pitch_analyzer.loudness(flat)
    pitch = pitch_analyzer.pitch(flat)

    if 60 <= pitch <= 400:
        state["pitch"] = round(pitch, 2)
        state["pitch_history"].append(pitch)

    state["loudness"] = round(loud, 5)
    state["loudness_history"].append(loud)


# ---------------- ASSEMBLY EVENTS ----------------

def on_turn(self, event):

    if hasattr(event, "end_of_turn") and not event.end_of_turn:
        return

    text = event.transcript.strip()

    if not text:
        return

    now = time.time()
    timestamp = round(now - state["session_start"], 2)

    # ---- WPM ----
    word_count = len(text.split())
    state["wpm"] = wpm_tracker.add_words(word_count)

    entry = {
        "text": text,
        "time": timestamp,
    }

    # ---- filler detection ----
    nlp_fillers = detect_fillers_from_text(text, timestamp)

    entry["fillers"] = nlp_fillers  # keep full {word, time} objects for frontend

    for f in nlp_fillers:
        state["fillers"].append(f)

    state["transcripts"].append(entry)


def on_begin(self, event):

    global audio_stream, audio_writer

    wpm_tracker.start()

    state["session_start"] = time.time()

    state["transcripts"].clear()
    state["fillers"].clear()
    state["pause_events"].clear()
    state["pitch_history"].clear()
    state["loudness_history"].clear()

    os.makedirs("recordings", exist_ok=True)

    # ✅ OPEN AUDIO FILE
    audio_writer = sf.SoundFile(
        audio_file_path,
        mode="w",
        samplerate=SAMPLE_RATE,
        channels=1,
    )

    # ✅ START MIC STREAM
    audio_stream = AudioStream(
        SAMPLE_RATE,
        audio_callback,
    )

    audio_stream.start()


def on_terminated(self, event):

    global audio_stream

    if audio_stream:
        audio_stream.stop()


# ---------------- START / STOP ----------------

def analysis_worker():

    global client

    client = StreamingClient(
        StreamingClientOptions(
            api_key=API_KEY_ASSEMBLYAI,
            api_host="streaming.assemblyai.com",
        )
    )

    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_terminated)

    client.connect(
        StreamingParameters(
            sample_rate=SAMPLE_RATE,
            format_turns=True,
        )
    )

    client.stream(
        aai.extras.MicrophoneStream(sample_rate=SAMPLE_RATE)
    )


@app.post("/api/start")
def start():

    global analysis_thread

    if state["running"]:
        return JSONResponse({"status": "already running"})

    state["running"] = True
    state["last_pause"] = False

    analysis_thread = threading.Thread(
        target=analysis_worker,
        daemon=True,
    )

    analysis_thread.start()

    return JSONResponse({"status": "started"})


@app.post("/api/stop")
def stop():

    global client, audio_stream, audio_writer

    if client:
        client.disconnect(terminate=True)

    if audio_stream:
        audio_stream.stop()
        audio_stream = None

    # ✅ CLOSE WAV FILE
    if audio_writer:
        try:
            audio_writer.close()
        except Exception as e:
            print(f"⚠️ Warning closing audio file: {e}")
        audio_writer = None

    state["running"] = False

    return JSONResponse({"status": "stopped"})


@app.get("/api/status")
def status():

    return JSONResponse(state)


@app.get("/api/transcripts")
def transcripts():

    return JSONResponse({
        "transcripts": state["transcripts"],
        "fillers": state["fillers"],
    })


# ---------------- FINAL REPORT HELPERS ----------------

def get_full_transcript():

    return " ".join(t["text"] for t in state["transcripts"])


def get_pitch_stats():

    if not state["pitch_history"]:
        return {"avg": 0, "min": 0, "max": 0}

    vals = state["pitch_history"]

    return {
        "avg": round(sum(vals) / len(vals), 2),
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
    }


# ---------------- MASTER CONTROL ----------------

def start_speech_system():

    global analysis_thread

    analysis_thread = threading.Thread(
        target=analysis_worker,
        daemon=True,
    )

    analysis_thread.start()


def stop_speech_system():
    stop()
