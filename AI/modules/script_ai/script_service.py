from .llm_service import call_gemini

def structure_script(raw_text: str):

    prompt = f"""
You are a professional presentation editor.

Structure the following text into a clean speech script with these sections:
1. Introduction
2. Key Points
3. Conclusion

IMPORTANT: Return ONLY plain text. Do NOT use any markdown formatting such as ##, **, ---, bullet symbols, or headers. Write it as a natural, spoken speech script that a presenter would read aloud.

Text:
{raw_text}
"""

    return call_gemini(prompt)


def generate_script(topic: str):

    prompt = f"""
You are a professional presentation writer. Write a complete speech script for a 5-minute presentation.

The script must have:
1. Introduction - greet the audience and introduce the topic
2. Key Points - cover 3 to 4 main points with clear explanations
3. Conclusion - summarize and end with a strong closing statement

IMPORTANT: Return ONLY plain text. Do NOT use any markdown formatting such as ##, **, ---, bullet symbols, asterisks, or headers. Write it as a natural, spoken speech script that a presenter would read aloud word by word. Use paragraph breaks to separate sections.

Topic: {topic}
"""

    return call_gemini(prompt, max_tokens=4096)


def edit_script(current_script: str, instruction: str):

    prompt = f"""
You are a professional presentation editor.

Current Script:
{current_script}

Instruction:
{instruction}

Return the full updated script as plain text. Do NOT use any markdown formatting such as ##, **, ---, bullet symbols, asterisks, or headers. Write it as a natural, spoken speech script.
"""

    return call_gemini(prompt)