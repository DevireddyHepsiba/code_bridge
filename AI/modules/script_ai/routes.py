from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from database import get_db
from modules.script_ai.models import Script
from modules.script_ai.script_service import generate_script, edit_script, structure_script

import pdfplumber
from docx import Document
from io import BytesIO

router = APIRouter()

@router.post("/api/script/upload")
async def upload_script(
    user_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        filename = file.filename.lower()
        content_bytes = await file.read()

        text = ""

        # TXT
        if filename.endswith(".txt"):
            text = content_bytes.decode("utf-8")

        # PDF
        elif filename.endswith(".pdf"):
            with pdfplumber.open(BytesIO(content_bytes)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""

        # DOCX
        elif filename.endswith(".docx"):
            doc = Document(BytesIO(content_bytes))
            for para in doc.paragraphs:
                text += para.text + "\n"

        else:
            return {"error": "Unsupported file type"}

        # Structure raw text via Gemini
        try:
            structured = structure_script(text)
        except Exception:
            structured = text  # fallback to raw if LLM fails

        script = Script(
            user_id=user_id,
            content=structured,
            original_content=text,
            source="uploaded",
            is_final=False
        )

        db.add(script)
        db.commit()
        db.refresh(script)

        return {
            "script_id": script.id,
            "content": structured
        }

    except Exception as e:
        return {"error": str(e)}


# Generate via prompt
@router.post("/api/script/generate")
def generate(data: dict, db: Session = Depends(get_db)):

    prompt = data.get("prompt") or data.get("topic")
    if not prompt:
        return {"error": "prompt is required"}

    user_id = data.get("user_id")
    if not user_id:
        return {"error": "user_id is required"}

    # Ensure user exists (avoid FK crash)
    from models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=f"user{user_id}@auto.local",
            name=f"User {user_id}",
            password_hash=""
        )
        db.add(user)
        db.commit()

    try:
        script_text = generate_script(prompt)
    except Exception as e:
        return {"error": "LLM failed", "details": str(e)}

    script = Script(
        user_id=user_id,
        content=script_text,
        source="generated",
        is_final=False
    )

    db.add(script)
    db.commit()
    db.refresh(script)

    return {"script_id": script.id, "content": script_text}


# Save manually typed script
@router.post("/api/script/save")
def save_manual(data: dict, db: Session = Depends(get_db)):

    content = data.get("content")
    user_id = data.get("user_id")

    if not content or not user_id:
        return {"error": "content and user_id are required"}

    # Ensure user exists
    from models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(
            id=user_id,
            email=f"user{user_id}@auto.local",
            name=f"User {user_id}",
            password_hash=""
        )
        db.add(user)
        db.commit()

    script = Script(
        user_id=user_id,
        content=content,
        source="manual",
        is_final=False
    )

    db.add(script)
    db.commit()
    db.refresh(script)

    return {"script_id": script.id, "content": script.content}


# Edit conversationally
@router.post("/api/script/edit")
def edit(data: dict, db: Session = Depends(get_db)):

    script_id = data.get("script_id")
    user_id = data.get("user_id")
    instruction = data.get("instruction")

    if not script_id or not instruction:
        return {"error": "script_id and instruction are required"}

    query = db.query(Script).filter(Script.id == script_id)
    if user_id:
        query = query.filter(Script.user_id == user_id)
    script = query.first()

    if not script:
        return {"error": "Script not found"}

    try:
        updated = edit_script(script.content, instruction)
    except Exception as e:
        return {"error": "LLM failed", "details": str(e)}

    script.content = updated
    db.commit()

    return {"script_id": script.id, "content": updated}


# Finalize
@router.post("/api/script/finalize")
def finalize(data: dict, db: Session = Depends(get_db)):

    script_id = data.get("script_id")
    user_id = data.get("user_id")

    if not script_id:
        return {"error": "script_id is required"}

    query = db.query(Script).filter(Script.id == script_id)
    if user_id:
        query = query.filter(Script.user_id == user_id)
    script = query.first()

    if not script:
        return {"error": "Script not found"}

    script.is_final = True
    db.commit()

    return {"status": "finalized"}