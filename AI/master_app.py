# # import threading
# # import sys
# # from pathlib import Path
# # from fastapi import FastAPI
# # from fastapi.responses import JSONResponse


# # from Learning.progress_service import save_session, update_mastery
# # from database import get_db
# # from fastapi import Depends
# # from sqlalchemy.orm import Session


# # from Learning.recommendation_service import get_recommendations

# # last_uploaded_video_url = None

# # from models.user_tutorial_progress import UserTutorialProgress

# # from models.session import Session as SessionModel

# # import subprocess
# # import time

# # # ----------------------------
# # # MERGE AUDIO + VIDEO
# # # ----------------------------

# # def merge_audio_video():

# #     video = "recordings/session_video.mp4"
# #     audio = "recordings/session_audio.wav"
# #     out = "recordings/final_session.mp4"

# #     cmd = [
# #         "ffmpeg",
# #         "-y",
# #         "-i", video,
# #         "-i", audio,
# #         "-c:v", "copy",
# #         "-c:a", "aac",
# #         out,
# #     ]

# #     subprocess.run(cmd)


# # # ----------------------------
# # # PATH SETUP
# # # ----------------------------

# # BASE = Path(__file__).parent

# # sys.path.append(str(BASE / "Guestures"))
# # sys.path.append(str(BASE / "Speech"))

# # # ----------------------------
# # # IMPORT SYSTEMS
# # # ----------------------------

# # from camera_server import (
# #     start_camera_system,
# #     stop_camera_system,
# #     compute_scores,
# # )

# # from main_server import (
# #     start_speech_system,
# #     stop_speech_system,
# #     state as speech_state,
# #     get_full_transcript,
# #     get_pitch_stats,
# # )

# # from content_compare import compare_to_reference
# # from content_eval import evaluate_content

# # # ----------------------------
# # # FASTAPI
# # # ----------------------------

# # app = FastAPI(title="Unified Presentation Coach")

# # running = False

# # reference_script = None

# # # ----------------------------
# # # SCORING HELPERS
# # # ----------------------------

# # def compute_overall(vision, filler_pct, pitch_stats):

# #     pitch_penalty = 0
# #     if pitch_stats["avg"] < 90 or pitch_stats["avg"] > 260:
# #         pitch_penalty = 10

# #     speech_score = max(
# #         100 - filler_pct * 3 - pitch_penalty,
# #         40,
# #     )

# #     overall = round(
# #         vision["overall"] * 0.65 + speech_score * 0.35,
# #         1,
# #     )

# #     return speech_score, overall


# # # ----------------------------
# # # START / STOP
# # # ----------------------------

# # @app.post("/api/start")
# # def start():

# #     global running

# #     if running:
# #         return JSONResponse({"status": "already running"})

# #     start_camera_system()
# #     start_speech_system()

# #     running = True

# #     return JSONResponse({"status": "started"})



# # @app.post("/api/stop")
# # def stop():

# #     global running

# #     stop_camera_system()
# #     stop_speech_system()

# #     global last_uploaded_video_url

# #     # small delay to flush files
# #     time.sleep(1)

# #     merge_audio_video()

# #     from services.cloudinary_service import upload_video
# #     import os

# #     try:
# #         cloud_url = upload_video(
# #             "recordings/final_session.mp4",
# #             folder="sessions"
# #         )

# #         print("Uploaded to Cloudinary:", cloud_url)

# #         last_uploaded_video_url = cloud_url
# #         # Delete local files after successful upload
# #         os.remove("recordings/session_video.mp4")
# #         os.remove("recordings/session_audio.wav")
# #         os.remove("recordings/final_session.mp4")

# #     except Exception as e:
# #         print("Upload failed:", e)
# #         cloud_url = None
# #         last_uploaded_video_url = None

# #     running = False

# #     return JSONResponse({
# #         "status": "stopped",
# #         "video_url": last_uploaded_video_url
# #     })

# # # ----------------------------
# # # LIVE STATUS
# # # ----------------------------

# # @app.get("/api/status")
# # def status():

# #     return JSONResponse({
# #         "running": running,
# #         "speech": speech_state,
# #     })


# # @app.get("/api/transcripts")
# # def transcripts():

# #     return JSONResponse({
# #         "transcripts": speech_state["transcripts"],
# #         "fillers": speech_state["fillers"],
# #     })


# # # ----------------------------
# # # UPLOAD REFERENCE SCRIPT
# # # ----------------------------

# # @app.post("/api/script")
# # def set_script(payload: dict):

# #     global reference_script

# #     reference_script = payload.get("script")

# #     return {"status": "stored"}


# # # ----------------------------
# # # FINAL SESSION REPORT
# # # ----------------------------

# # @app.get("/api/session/report")
# # def session_report(
# #     user_id: int,
# #     db: Session = Depends(get_db)
# # ):

# #     global reference_script

# #     transcript = get_full_transcript()

# #     filler_count = len(speech_state["fillers"])
# #     total_words = max(len(transcript.split()), 1)

# #     filler_pct = round((filler_count / total_words) * 100, 2)

# #     vision_scores = compute_scores()

# #     pitch_stats = get_pitch_stats()

# #     missed_points = []

# #     if reference_script:
# #         missed_points = compare_to_reference(
# #             transcript,
# #             reference_script,
# #         )

# #     gemini_feedback = evaluate_content(
# #         transcript,
# #         pitch_stats,
# #         vision_scores,
# #     )

# #     speech_score, overall = compute_overall(
# #         vision_scores,
# #         filler_pct,
# #         pitch_stats,
# #     )


# #     save_session(
# #         db=db,
# #         user_id=user_id,
# #         gesture=vision_scores["gesture"],
# #         posture=vision_scores["posture"],
# #         eye=vision_scores["eye"],
# #         speech=speech_score,
# #         overall=overall,
# #         video_url=last_uploaded_video_url
# #     )

# #     update_mastery(db, user_id)

# #     return {
# #         "transcript": transcript,
# #         "fillers": speech_state["fillers"],
# #         "filler_percent": filler_pct,
# #         "pitch": pitch_stats,
# #         "vision_scores": vision_scores,
# #         "missed_points": missed_points,
# #         "speech_score": speech_score,
# #         "overall_score": overall,
# #         "content_feedback": gemini_feedback,
# #     }




# # # ----------------------------
# # # RECOMMENDATIONS
# # # ----------------------------

# # @app.get("/api/learning/recommendations")
# # def recommendations(
# #     user_id: int,
# #     db: Session = Depends(get_db)
# # ):

# #     recs = get_recommendations(db, user_id)

# #     return {"recommendations": recs}



# # @app.post("/api/tutorial/progress")
# # def update_tutorial_progress(
# #     user_id: int,
# #     tutorial_id: int,
# #     watched_seconds: float,
# #     db: Session = Depends(get_db)
# # ):

# #     progress = db.query(UserTutorialProgress).filter(
# #         UserTutorialProgress.user_id == user_id,
# #         UserTutorialProgress.tutorial_id == tutorial_id
# #     ).first()

# #     if not progress:
# #         progress = UserTutorialProgress(
# #             user_id=user_id,
# #             tutorial_id=tutorial_id
# #         )
# #         db.add(progress)

# #     progress.watched_seconds = watched_seconds

# #     # Example: assume tutorial duration = 600 seconds
# #     percent = min((watched_seconds / 600) * 100, 100)
# #     progress.completion_percent = percent
# #     progress.completed = percent >= 95

# #     db.commit()

# #     return {"status": "updated"}



# # @app.get("/api/tutorial/progress")
# # def get_progress(user_id: int, db: Session = Depends(get_db)):

# #     records = db.query(UserTutorialProgress).filter(
# #         UserTutorialProgress.user_id == user_id
# #     ).all()

# #     return {
# #         "progress": [
# #             {
# #                 "tutorial_id": r.tutorial_id,
# #                 "completion_percent": r.completion_percent,
# #                 "completed": r.completed
# #             }
# #             for r in records
# #         ]
# #     }


# # @app.get("/api/learning/progress")
# # def learning_progress(user_id: int, db: Session = Depends(get_db)):

# #     total = db.query(TutorialVideo).count()

# #     completed = db.query(UserTutorialProgress).filter(
# #         UserTutorialProgress.user_id == user_id,
# #         UserTutorialProgress.completed == True
# #     ).count()

# #     percent = 0
# #     if total > 0:
# #         percent = (completed / total) * 100

# #     return {"learning_progress_percent": round(percent, 2)}


# # @app.get("/api/sessions/history")
# # def session_history(user_id: int, db: Session = Depends(get_db)):

# #     sessions = db.query(SessionModel).filter(
# #         SessionModel.user_id == user_id
# #     ).order_by(SessionModel.created_at.desc()).all()

# #     return {
# #         "sessions": [
# #             {
# #                 "date": s.created_at,
# #                 "overall_score": s.overall_score,
# #                 "video_url": s.video_url
# #             }
# #             for s in sessions
# #         ]
# #     }
# # # ----------------------------
# # # RUN
# # # ----------------------------

# # if __name__ == "__main__":

# #     import uvicorn

# #     uvicorn.run(app, host="0.0.0.0", port=9000)



# import sys
# from pathlib import Path
# from fastapi import FastAPI, UploadFile, File, Depends
# from fastapi.responses import JSONResponse
# from fastapi.middleware.cors import CORSMiddleware
# from sqlalchemy.orm import Session
# import tempfile
# import shutil

# from Learning.progress_service import save_session, update_mastery
# from Learning.recommendation_service import get_recommendations
# from database import get_db

# from models.user_tutorial_progress import UserTutorialProgress
# from models.session import Session as SessionModel
# from models.tutorial_video import TutorialVideo
# from models.feedback import Feedback
# import time

# # ----------------------------
# # PATH SETUP
# # ----------------------------

# BASE = Path(__file__).parent
# sys.path.append(str(BASE / "Guestures"))
# sys.path.append(str(BASE / "Speech"))

# # ----------------------------
# # IMPORT SYSTEMS
# # ----------------------------

# from camera_server import (
#     process_frame_from_webrtc,
#     compute_scores,
#     reset_scores,
# )

# from main_server import (
#     start_speech_system,
#     stop_speech_system,
#     state as speech_state,
#     get_full_transcript,
#     get_pitch_stats,
# )

# from content_compare import compare_to_reference
# from content_eval import evaluate_content
# import cloudinary_config  # Configure Cloudinary API keys
# from services.cloudinary_service import upload_video

# # ----------------------------
# # FASTAPI
# # ----------------------------

# app = FastAPI(title="Unified Presentation Coach")

# # Enable CORS for frontend running on various ports
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:8080", "http://127.0.0.1:8080", "http://localhost:5173", "http://localhost:8081", "http://127.0.0.1:8081"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# running = False
# reference_script = None
# last_uploaded_video_url = None  # Deprecated, use session_video_urls dict
# session_video_urls = {}  # Track video_url per session_id
# current_session_id = None
# current_user_id = None
# session_start_time = None

# # ----------------------------
# # SCORING HELPERS
# # ----------------------------

# def compute_overall(vision, filler_pct, pitch_stats):

#     pitch_penalty = 0
#     if pitch_stats["avg"] < 90 or pitch_stats["avg"] > 260:
#         pitch_penalty = 10

#     speech_score = max(
#         100 - filler_pct * 3 - pitch_penalty,
#         40,
#     )

#     overall = round(
#         vision["overall"] * 0.65 + speech_score * 0.35,
#         1,
#     )

#     return speech_score, overall

# # ----------------------------
# # START
# # ----------------------------

# @app.post("/api/start")
# def start(user_id: int = 1, db: Session = Depends(get_db)):

#     global running, current_session_id, current_user_id, session_start_time

#     if running:
#         return {"status": "already running", "session_id": current_session_id}

#     reset_scores()
#     start_speech_system()
    
#     # Create session record in database
#     try:
#         session = SessionModel(
#             user_id=user_id,
#             gesture_score=0,
#             posture_score=0,
#             eye_score=0,
#             speech_score=0,
#             overall_score=0,
#         )
#         db.add(session)
#         db.commit()
#         db.refresh(session)
        
#         current_session_id = session.id
#         current_user_id = user_id
#         session_start_time = time.time()
#     except Exception as e:
#         print(f"Error creating session: {e}")
#         db.rollback()
#         return {"status": "error", "message": str(e)}

#     running = True
    
#     # Initialize video_url for this session
#     session_video_urls[session.id] = None

#     return {"status": "started", "session_id": session.id}

# # ----------------------------
# # RECEIVE FRAME FROM WEBRTC
# # ----------------------------

# @app.post("/api/frame")
# def receive_frame(payload: dict, db: Session = Depends(get_db)):

#     frame = payload.get("frame")
#     session_id = payload.get("session_id")  # Get session_id from payload

#     if not frame:
#         print("❌ No frame provided")
#         return {"error": "No frame provided"}

#     print(f"📸 Processing frame: {len(frame)} bytes (session: {session_id})")
#     result = process_frame_from_webrtc(frame)
#     print(f"✅ Frame processed: posture={result.get('posture_score')}, eye={result.get('eye_score')}, gesture={result.get('gesture_score')}")
    
#     # Save feedback to database for this frame analysis
#     if session_id:
#         try:
#             # Get session start time from database
#             session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
#             session_start_time = session.created_at.timestamp() if session and session.created_at else time.time()
#             timestamp = time.time() - session_start_time
            
#             # Ensure scores are valid numbers
#             posture_score = float(result.get("posture_score") or 0)
#             eye_score = float(result.get("eye_score") or 0)
#             gesture_score = float(result.get("gesture_score") or 0)
            
#             # Save posture feedback
#             fb_posture = Feedback(
#                 session_id=session_id,
#                 category="posture",
#                 status=result.get("posture_status", "analyzed"),
#                 score=posture_score,
#                 timestamp=timestamp
#             )
#             db.add(fb_posture)
            
#             # Save eye contact feedback
#             fb_eye = Feedback(
#                 session_id=session_id,
#                 category="eye_contact",
#                 status=result.get("eye_status", "analyzed"),
#                 score=eye_score,
#                 timestamp=timestamp
#             )
#             db.add(fb_eye)
            
#             # Save gesture feedback
#             fb_gesture = Feedback(
#                 session_id=session_id,
#                 category="gesture",
#                 status=result.get("gesture_status", "analyzed"),
#                 score=gesture_score,
#                 timestamp=timestamp
#             )
#             db.add(fb_gesture)
            
#             db.commit()
#         except Exception as e:
#             print(f"Error saving feedback: {e}")
#             db.rollback()

#     return result

# # ----------------------------
# # STOP
# # ----------------------------

# @app.post("/api/stop")
# def stop():

#     global running, current_session_id, session_video_urls

#     try:
#         stop_speech_system()
#     except Exception as e:
#         print(f"⚠️ Error stopping speech system: {e}")
#         # Continue anyway, we still want to stop recording
    
#     running = False
    
#     # Get video_url for CURRENT session
#     video_url = None
#     if current_session_id and current_session_id in session_video_urls:
#         video_url = session_video_urls[current_session_id]
#         print(f"✅ Returning video for session {current_session_id}: {video_url}")
#     else:
#         print(f"⚠️ No video found for session {current_session_id}")

#     return {
#         "status": "stopped",
#         "video_url": video_url
#     }

# # ----------------------------
# # VIDEO UPLOAD FROM WEBRTC
# # ----------------------------

# @app.post("/api/upload")
# async def upload_video_file(file: UploadFile = File(...)):

#     global last_uploaded_video_url, session_video_urls, current_session_id

#     try:
#         with tempfile.NamedTemporaryFile(delete=False) as tmp:
#             content = await file.read()
#             tmp.write(content)
#             temp_path = tmp.name

#         print(f"📤 Uploading file from {temp_path}, size: {len(content)} bytes")
        
#         cloud_url = upload_video(temp_path, folder="sessions")

#         last_uploaded_video_url = cloud_url
        
#         # Store video_url for current session
#         if current_session_id:
#             session_video_urls[current_session_id] = cloud_url
#             print(f"✅ Session {current_session_id} video: {cloud_url}")
        
#         print(f"✅ Upload successful: {cloud_url}")

#         return {"video_url": cloud_url}
#     except Exception as e:
#         print(f"❌ Upload failed: {e}")
#         import traceback
#         traceback.print_exc()
#         return {"video_url": None, "error": str(e)}

# # ----------------------------
# # STATUS
# # ----------------------------

# @app.get("/api/status")
# def status():

#     return {
#         "running": running,
#         "speech": speech_state,
#     }

# @app.get("/api/transcripts")
# def transcripts():

#     return {
#         "transcripts": speech_state["transcripts"],
#         "fillers": speech_state["fillers"],
#     }

# @app.get("/api/fillers")
# def get_fillers():
#     """Get current filler words detected in real-time during recording"""
#     fillers = speech_state.get("fillers", [])
#     total_words = len(speech_state.get("transcripts", []))
#     filler_count = len(fillers)
#     filler_percent = round((filler_count / total_words * 100) if total_words > 0 else 0, 2)
    
#     return {
#         "fillers": fillers,
#         "filler_percent": filler_percent,
#         "count": filler_count,
#     }

# @app.get("/api/pause-events")
# def get_pause_events():
#     """Get long pause events detected during recording for beep alerts"""
#     pause_events = speech_state.get("pause_events", [])
#     speaking_active = speech_state.get("speaking_active", False)
    
#     return {
#         "pause_events": pause_events,
#         "count": len(pause_events),
#         "speaking_active": speaking_active,  # If true, user is speaking - don't play beep
#     }

# # ----------------------------
# # SCRIPT
# # ----------------------------

# @app.post("/api/script")
# def set_script(payload: dict):

#     global reference_script
#     reference_script = payload.get("script")

#     return {"status": "stored"}

# # ----------------------------
# # FINAL SESSION REPORT
# # ----------------------------

# @app.get("/api/session/report")
# def session_report(
#     user_id: int,
#     db: Session = Depends(get_db)
# ):

#     global reference_script

#     transcript = get_full_transcript()

#     filler_count = len(speech_state["fillers"])
#     total_words = max(len(transcript.split()), 1)

#     filler_pct = round((filler_count / total_words) * 100, 2)

#     vision_scores = compute_scores()
#     pitch_stats = get_pitch_stats()

#     missed_points = []

#     if reference_script:
#         missed_points = compare_to_reference(
#             transcript,
#             reference_script,
#         )

#     # Wrap Gemini call with fallback
#     try:
#         gemini_feedback = evaluate_content(
#             transcript,
#             pitch_stats,
#             vision_scores,
#         )
#         # Check if Gemini returned an error dict
#         if isinstance(gemini_feedback, dict) and "error" in gemini_feedback:
#             print(f"⚠️ Gemini returned error: {gemini_feedback}")
#             gemini_feedback = "Content analysis unavailable. Please try again later."
#     except Exception as e:
#         print(f"⚠️ Gemini exception: {e}")
#         gemini_feedback = "Content analysis unavailable. Please try again later."

#     speech_score, overall = compute_overall(
#         vision_scores,
#         filler_pct,
#         pitch_stats,
#     )

#     save_session(
#         db=db,
#         user_id=user_id,
#         gesture=vision_scores["gesture"],
#         posture=vision_scores["posture"],
#         eye=vision_scores["eye"],
#         speech=speech_score,
#         overall=overall,
#         video_url=last_uploaded_video_url
#     )

#     update_mastery(db, user_id)
    
#     # Fetch all feedback records for this session
#     global current_session_id
#     feedback_records = []
#     if current_session_id:
#         feedback_records = db.query(Feedback).filter(
#             Feedback.session_id == current_session_id
#         ).order_by(Feedback.timestamp).all()

#     # Get video URL for this session
#     video_url = session_video_urls.get(current_session_id) if current_session_id else last_uploaded_video_url

#     return {
#         "transcript": transcript,
#         "fillers": speech_state["fillers"],
#         "filler_percent": filler_pct,
#         "pitch": pitch_stats,
#         "vision_scores": vision_scores,
#         "missed_points": missed_points,
#         "speech_score": speech_score,
#         "overall_score": overall,
#         "content_feedback": gemini_feedback,
#         "video_url": video_url,
#         "live_feedback": [
#             {
#                 "id": f.id,
#                 "category": f.category,
#                 "status": f.status,
#                 "score": f.score,
#                 "timestamp": f.timestamp,
#             }
#             for f in feedback_records
#         ]
#     }

# # ----------------------------
# # RECOMMENDATIONS
# # ----------------------------

# @app.get("/api/learning/recommendations")
# def recommendations(
#     user_id: int,
#     db: Session = Depends(get_db)
# ):

#     recs = get_recommendations(db, user_id)
#     return {"recommendations": recs}

# # ----------------------------
# # TUTORIAL PROGRESS
# # ----------------------------

# @app.post("/api/tutorial/progress")
# def update_tutorial_progress(
#     user_id: int,
#     tutorial_id: int,
#     watched_seconds: float,
#     db: Session = Depends(get_db)
# ):

#     progress = db.query(UserTutorialProgress).filter(
#         UserTutorialProgress.user_id == user_id,
#         UserTutorialProgress.tutorial_id == tutorial_id
#     ).first()

#     if not progress:
#         progress = UserTutorialProgress(
#             user_id=user_id,
#             tutorial_id=tutorial_id
#         )
#         db.add(progress)

#     progress.watched_seconds = watched_seconds

#     percent = min((watched_seconds / 600) * 100, 100)
#     progress.watch_percent = percent
#     progress.completed = percent >= 95

#     db.commit()

#     return {"status": "updated"}

# @app.get("/api/tutorial/progress")
# def get_progress(user_id: int, db: Session = Depends(get_db)):

#     records = db.query(UserTutorialProgress).filter(
#         UserTutorialProgress.user_id == user_id
#     ).all()

#     return {
#         "progress": [
#             {
#                 "tutorial_id": r.tutorial_id,
#                 "completion_percent": r.watch_percent,
#                 "completed": r.completed
#             }
#             for r in records
#         ]
#     }

# # ----------------------------
# # LEARNING PROGRESS
# # ----------------------------

# @app.get("/api/learning/progress")
# def learning_progress(user_id: int, db: Session = Depends(get_db)):

#     total = db.query(TutorialVideo).count()

#     completed = db.query(UserTutorialProgress).filter(
#         UserTutorialProgress.user_id == user_id,
#         UserTutorialProgress.completed == True
#     ).count()

#     percent = 0
#     if total > 0:
#         percent = (completed / total) * 100

#     return {"learning_progress_percent": round(percent, 2)}

# # ----------------------------
# # SESSION HISTORY
# # ----------------------------

# @app.get("/api/sessions/history")
# def session_history(user_id: int, db: Session = Depends(get_db)):

#     sessions = db.query(SessionModel).filter(
#         SessionModel.user_id == user_id
#     ).order_by(SessionModel.created_at.desc()).all()

#     return {
#         "sessions": [
#             {
#                 "date": s.created_at,
#                 "overall_score": s.overall_score,
#                 "video_url": s.video_url
#             }
#             for s in sessions
#         ]
#     }

# # ----------------------------
# # RUN
# # ----------------------------

# if __name__ == "__main__":

#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=9000)



import sys
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import tempfile
import time

from database import get_db
from models.session import Session as SessionModel
from models.feedback import Feedback
from models.tutorial_video import TutorialVideo
from models.user_tutorial_progress import UserTutorialProgress

from Learning.progress_service import update_mastery
from Learning.recommendation_service import get_recommendations

# 🔥 NEW SCRIPT AI IMPORTS
from modules.script_ai.comparison_service import compare_script
from modules.script_ai.models import Script
from modules.script_ai.routes import router as script_router
from content_eval import evaluate_content

# ----------------------------
# PATH SETUP
# ----------------------------

BASE = Path(__file__).parent
sys.path.append(str(BASE / "Guestures"))
sys.path.append(str(BASE / "Speech"))

# ----------------------------
# IMPORT SYSTEMS
# ----------------------------

from camera_server import (
    process_frame_from_webrtc,
    compute_scores,
    reset_scores,
)

from main_server import (
    start_speech_system,
    stop_speech_system,
    state as speech_state,
    get_full_transcript,
    get_pitch_stats,
)

from services.cloudinary_service import upload_video
import cloudinary_config

# ----------------------------
# FASTAPI
# ----------------------------

app = FastAPI(title="Unified Presentation Coach")

app.include_router(script_router)  # ✅ Register Script AI module

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# AUTO-CREATE TABLES ON STARTUP
# ----------------------------
from database import engine, Base

@app.on_event("startup")
def startup():
    # Import all models so Base.metadata knows about them
    import models.session  # noqa
    import models.feedback  # noqa
    import models.user  # noqa
    import models.skill_mastery  # noqa
    import models.tutorial_video  # noqa
    import models.user_tutorial_progress  # noqa
    import modules.script_ai.models  # noqa
    Base.metadata.create_all(bind=engine)
    print("✅ All tables created")

# ----------------------------
# GLOBAL STATE
# ----------------------------

running = False
current_session_id = None
current_user_id = None
session_video_urls = {}

# ----------------------------
# HELPER
# ----------------------------

def compute_overall(vision, filler_pct, pitch_stats):

    pitch_penalty = 0
    if pitch_stats["avg"] < 90 or pitch_stats["avg"] > 260:
        pitch_penalty = 10

    speech_score = max(
        100 - filler_pct * 3 - pitch_penalty,
        40,
    )

    overall = round(
        vision["overall"] * 0.65 + speech_score * 0.35,
        1,
    )

    return speech_score, overall

# ----------------------------
# START SESSION
# ----------------------------

@app.post("/api/start")
def start(user_id: int = 1, db: Session = Depends(get_db)):

    global running, current_session_id, current_user_id

    if running:
        return {"status": "already running", "session_id": current_session_id}

    reset_scores()
    start_speech_system()

    session = SessionModel(
        user_id=user_id,
        gesture_score=0,
        posture_score=0,
        eye_score=0,
        speech_score=0,
        overall_score=0,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    current_session_id = session.id
    current_user_id = user_id
    running = True

    session_video_urls[session.id] = None

    return {"status": "started", "session_id": session.id}

# ----------------------------
# FRAME ANALYSIS
# ----------------------------

@app.post("/api/frame")
def receive_frame(payload: dict, db: Session = Depends(get_db)):

    frame = payload.get("frame")
    session_id = payload.get("session_id")

    if not frame:
        return {"error": "No frame provided"}

    result = process_frame_from_webrtc(frame)

    if session_id:
        timestamp = time.time()

        fb = Feedback(
            session_id=session_id,
            category="vision",
            status="analyzed",
            score=result.get("posture_score", 0),
            timestamp=timestamp,
        )
        db.add(fb)
        db.commit()

    return result

# ----------------------------
# STOP SESSION
# ----------------------------

@app.post("/api/stop")
def stop():

    global running
    stop_speech_system()
    running = False

    return {"status": "stopped"}

# ----------------------------
# LIVE TRANSCRIPTS
# ----------------------------

@app.get("/api/transcripts")
def get_transcripts():
    return {
        "transcripts": speech_state.get("transcripts", []),
        "fillers": speech_state.get("fillers", []),
    }

# ----------------------------
# FILLER WORDS
# ----------------------------

@app.get("/api/fillers")
def get_fillers():
    fillers = speech_state.get("fillers", [])
    total_words = sum(len(t.get("text", "").split()) for t in speech_state.get("transcripts", []))
    filler_count = len(fillers)
    filler_percent = round((filler_count / max(total_words, 1)) * 100, 2)
    return {
        "fillers": fillers,
        "filler_percent": filler_percent,
        "count": filler_count,
    }

# ----------------------------
# PAUSE EVENTS (for beep alerts)
# ----------------------------

@app.get("/api/pause-events")
def get_pause_events():
    pause_events = speech_state.get("pause_events", [])
    speaking_active = speech_state.get("speaking_active", False)
    return {
        "pause_events": pause_events,
        "count": len(pause_events),
        "speaking_active": bool(speaking_active),
    }

# ----------------------------
# VIDEO UPLOAD
# ----------------------------

@app.post("/api/upload")
async def upload_video_file(file: UploadFile = File(...)):
    global current_session_id, session_video_urls
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name

        print(f"\U0001f4e4 Uploading file from {temp_path}, size: {len(content)} bytes")

        cloud_url = upload_video(temp_path, folder="sessions")

        if current_session_id:
            session_video_urls[current_session_id] = cloud_url
            print(f"\u2705 Session {current_session_id} video: {cloud_url}")

        # Clean up temp file
        import os
        try:
            os.unlink(temp_path)
        except:
            pass

        return {"video_url": cloud_url}
    except Exception as e:
        print(f"\u274c Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"video_url": None, "error": str(e)})

# ----------------------------
# FINAL SESSION REPORT
# ----------------------------

@app.get("/api/session/report")
def session_report(
    user_id: int,
    db: Session = Depends(get_db)
):
    global current_session_id

    transcript = get_full_transcript()

    filler_count = len(speech_state["fillers"])
    total_words = max(len(transcript.split()), 1)
    filler_pct = round((filler_count / total_words) * 100, 2)

    vision_scores = compute_scores()
    pitch_stats = get_pitch_stats()

    # 🔥 GET FINALIZED SCRIPT
    reference_script = db.query(Script).filter(
        Script.user_id == user_id,
        Script.is_final == True
    ).order_by(Script.created_at.desc()).first()

    semantic_analysis = None
    content_feedback = None

    # Run both Gemini calls in parallel using threads
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _compare():
        if reference_script:
            return compare_script(reference_script.content, transcript)
        return None

    def _evaluate():
        try:
            fb = evaluate_content(transcript, pitch_stats, vision_scores)
            if isinstance(fb, dict) and "error" in fb:
                print(f"⚠️ Gemini feedback error: {fb}")
                return None
            return fb
        except Exception as e:
            print(f"⚠️ Gemini feedback exception: {e}")
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_compare = pool.submit(_compare)
        future_evaluate = pool.submit(_evaluate)
        semantic_analysis = future_compare.result(timeout=90)
        content_feedback = future_evaluate.result(timeout=90)

    speech_score, overall = compute_overall(
        vision_scores,
        filler_pct,
        pitch_stats,
    )

    # 🔥 UPDATE SESSION
    if current_session_id:
        session = db.query(SessionModel).filter(
            SessionModel.id == current_session_id
        ).first()

        if session:
            session.gesture_score = vision_scores["gesture"]
            session.posture_score = vision_scores["posture"]
            session.eye_score = vision_scores["eye"]
            session.speech_score = speech_score
            session.overall_score = overall
            session.transcript = transcript

            if reference_script:
                session.reference_script_id = reference_script.id

            session.analysis_json = semantic_analysis

            db.commit()

    update_mastery(db, user_id)

    return {
        "transcript": transcript,
        "vision_scores": vision_scores,
        "speech_score": speech_score,
        "overall_score": overall,
        "semantic_analysis": semantic_analysis,
        "content_feedback": content_feedback,
        "filler_percent": filler_pct,
        "pitch": pitch_stats,
        "fillers": speech_state["fillers"],
    }

# ----------------------------
# RECOMMENDATIONS
# ----------------------------

@app.get("/api/learning/recommendations")
def recommendations(
    user_id: int,
    db: Session = Depends(get_db)
):
    recs = get_recommendations(db, user_id)
    return {"recommendations": recs}

# ----------------------------
# SESSION HISTORY
# ----------------------------

@app.get("/api/sessions/history")
def session_history(user_id: int, db: Session = Depends(get_db)):

    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id
    ).order_by(SessionModel.created_at.desc()).all()

    return {
        "sessions": [
            {
                "date": s.created_at,
                "overall_score": s.overall_score,
                "video_url": s.video_url
            }
            for s in sessions
        ]
    }

# ----------------------------
# RUN
# ----------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)