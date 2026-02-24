import json
import re
import sys
from pathlib import Path

# Add modules dir so we can import call_gemini
sys.path.append(str(Path(__file__).resolve().parent.parent / "modules" / "script_ai"))
from llm_service import call_gemini


def _extract_json(text: str):
    """Robustly extract a JSON object from text."""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    if start == -1:
        return None

    brace_count = 0
    end = start
    for i in range(start, len(text)):
        if text[i] == '{':
            brace_count += 1
        elif text[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end = i + 1
                break

    if brace_count != 0:
        return None

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return None


def evaluate_content(text, pitch, vision):
    """Analyze a presentation transcript and return structured feedback."""

    if not text or len(text.strip().split()) < 5:
        return {
            "clarity_score": 0,
            "engagement_score": 0,
            "structure_score": 0,
            "strengths": [],
            "improvements": ["Transcript too short to provide meaningful feedback"],
            "overall_feedback": "Not enough speech content was captured to analyze.",
            "content_suggestions": ["Try speaking more during your presentation"]
        }

    prompt = f"""You are an expert public speaking coach. Analyze this presentation transcript and performance data, then return STRICT JSON only.

Transcript:
{text}

Pitch stats: avg={pitch.get('avg',0):.0f}Hz, min={pitch.get('min',0):.0f}Hz, max={pitch.get('max',0):.0f}Hz
Vision scores: eye_contact={vision.get('eye',0)}%, posture={vision.get('posture',0)}%, gestures={vision.get('gesture',0)}%

Return ONLY this JSON structure with NO markdown, NO code fences, NO extra text:
{{
  "clarity_score": <number 0-100>,
  "engagement_score": <number 0-100>,
  "structure_score": <number 0-100>,
  "strengths": ["<specific strength from their speech>", "<another strength>"],
  "improvements": ["<specific actionable improvement>", "<another improvement>"],
  "overall_feedback": "<2-3 sentence constructive summary>",
  "content_suggestions": ["<suggestion to improve content>", "<another suggestion>"]
}}

Rules:
- Be specific and actionable — reference actual things from the transcript
- Strengths: what the speaker did well based on content and delivery data
- Improvements: concrete areas they should work on
- content_suggestions: ideas to make the content itself stronger
- Return ONLY valid JSON
"""

    try:
        result = call_gemini(prompt, max_tokens=1024, temperature=0.3)
        parsed = _extract_json(result)
        if parsed:
            parsed.setdefault("clarity_score", 0)
            parsed.setdefault("engagement_score", 0)
            parsed.setdefault("structure_score", 0)
            parsed.setdefault("strengths", [])
            parsed.setdefault("improvements", [])
            parsed.setdefault("overall_feedback", "")
            parsed.setdefault("content_suggestions", [])
            return parsed
        else:
            print(f"⚠️ evaluate_content: Could not parse JSON from: {result[:300]}")
            return {"error": "Invalid JSON from Gemini"}
    except Exception as e:
        print(f"⚠️ evaluate_content exception: {e}")
        return {"error": str(e)}
