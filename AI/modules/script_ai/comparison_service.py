import json
import re
from .llm_service import call_gemini

def compare_script(reference_script, transcript):
    """Compare a reference script against the actual transcript."""

    # Guard: if transcript is too short, skip Gemini call
    if not transcript or len(transcript.strip().split()) < 5:
        return {
            "coverage_percent": 0,
            "missing_points": ["Transcript too short to analyze"],
            "partially_covered_points": [],
            "flow_issues": [],
            "insights": "The speaker did not say enough to compare against the script."
        }

    prompt = f"""You are an expert speech evaluator. Compare the reference script against what the speaker actually said in the transcript.

Reference Script:
---
{reference_script}
---

Actual Transcript:
---
{transcript}
---

Analyze how well the speaker covered the script. Return ONLY a JSON object with NO markdown, NO code fences, NO extra text:

{{
  "coverage_percent": <number 0-100>,
  "missing_points": ["<key idea from script that was completely skipped>"],
  "partially_covered_points": ["<idea that was mentioned but not fully explained>"],
  "flow_issues": ["<any ordering or transition problems>"],
  "insights": "<one paragraph summary of how well the speaker followed the script>"
}}

Rules:
- coverage_percent: what percentage of the script's key ideas were conveyed
- missing_points: list specific topics/sentences from the script that the speaker skipped entirely
- partially_covered_points: ideas mentioned briefly but not fully covered
- flow_issues: if the speaker changed the order or had awkward transitions
- insights: a brief constructive summary
- If the speaker covered everything well, set coverage_percent high and leave missing_points empty
- Return ONLY valid JSON
"""

    try:
        result = call_gemini(prompt, max_tokens=1024, temperature=0)
        parsed = _extract_json(result)
        if parsed:
            # Validate expected keys exist
            parsed.setdefault("coverage_percent", 0)
            parsed.setdefault("missing_points", [])
            parsed.setdefault("partially_covered_points", [])
            parsed.setdefault("flow_issues", [])
            parsed.setdefault("insights", "")
            return parsed
        else:
            print(f"⚠️ compare_script: Could not parse JSON from: {result[:300]}")
            return {
                "coverage_percent": 0,
                "missing_points": ["Analysis could not be completed"],
                "partially_covered_points": [],
                "flow_issues": [],
                "insights": "The AI model returned an invalid response. Please try again."
            }
    except Exception as e:
        print(f"⚠️ compare_script exception: {e}")
        return {
            "coverage_percent": 0,
            "missing_points": ["Analysis failed due to an error"],
            "partially_covered_points": [],
            "flow_issues": [],
            "insights": str(e)
        }


def _extract_json(text: str):
    """Robustly extract a JSON object from text that may contain markdown fences."""
    # Strip markdown code fences if present
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find JSON object by matching braces
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