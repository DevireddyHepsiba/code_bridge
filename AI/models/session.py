from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime,String,Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    gesture_score = Column(Float, nullable=False)
    posture_score = Column(Float, nullable=False)
    eye_score = Column(Float, nullable=False)
    speech_score = Column(Float, nullable=False)
    overall_score = Column(Float, nullable=False)
    transcript = Column(Text, nullable=True)
    reference_script_id = Column(Integer, ForeignKey("scripts.id"), nullable=True)
    analysis_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    video_url = Column(String, nullable=True)
    user = relationship("User", backref="sessions")
